from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Iterator

from .domain import MediaStatus


class DuplicateChecksumError(Exception):
    def __init__(self, media_id: str):
        self.media_id = media_id
        super().__init__(f"Duplicate media: {media_id}")


class SQLiteRepository:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = Lock()
        self._initialise()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS media (
                    media_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    checksum TEXT NOT NULL UNIQUE,
                    object_path TEXT,
                    thumbnail_path TEXT,
                    tags_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    model_version TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_media_status ON media(status);
                CREATE INDEX IF NOT EXISTS idx_media_owner_created ON media(owner, created_at);
                CREATE TABLE IF NOT EXISTS subscriptions (
                    owner TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    email TEXT NOT NULL,
                    PRIMARY KEY(owner, tag)
                );
                """
            )

    def reserve_media(self, record: dict) -> None:
        with self._lock, self.connect() as db:
            try:
                db.execute(
                    """INSERT INTO media(
                        media_id, owner, filename, content_type, size, checksum, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record["media_id"],
                        record["owner"],
                        record["filename"],
                        record["content_type"],
                        record["size"],
                        record["checksum"],
                        MediaStatus.RESERVED.value,
                        datetime.now(UTC).isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                row = db.execute(
                    "SELECT media_id FROM media WHERE checksum = ?", (record["checksum"],)
                ).fetchone()
                if row:
                    raise DuplicateChecksumError(row["media_id"]) from exc
                raise

    def get_media(self, media_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM media WHERE media_id = ?", (media_id,)).fetchone()
        return self._row(row) if row else None

    def list_media(self, ready_only: bool = False) -> list[dict]:
        query = "SELECT * FROM media"
        params: tuple = ()
        if ready_only:
            query += " WHERE status = ?"
            params = (MediaStatus.READY.value,)
        query += " ORDER BY created_at DESC"
        with self.connect() as db:
            rows = db.execute(query, params).fetchall()
        return [self._row(row) for row in rows]

    def update_media(self, media_id: str, **changes) -> None:
        if "tags" in changes:
            changes["tags_json"] = json.dumps(changes.pop("tags"), sort_keys=True)
        allowed = {"object_path", "thumbnail_path", "tags_json", "status", "model_version", "error"}
        invalid = set(changes) - allowed
        if invalid:
            raise ValueError(f"Unsupported media fields: {sorted(invalid)}")
        if not changes:
            return
        columns = ", ".join(f"{name} = ?" for name in changes)
        values = [
            value.value if isinstance(value, MediaStatus) else value for value in changes.values()
        ]
        with self.connect() as db:
            db.execute(f"UPDATE media SET {columns} WHERE media_id = ?", (*values, media_id))

    def find_by_tags(self, required: dict[str, int]) -> list[dict]:
        return [
            media
            for media in self.list_media(ready_only=True)
            if all(media["tags"].get(tag, 0) >= count for tag, count in required.items())
        ]

    def delete_media(self, media_id: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM media WHERE media_id = ?", (media_id,))

    def upsert_subscription(self, owner: str, tag: str, email: str) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO subscriptions(owner, tag, email) VALUES (?, ?, ?)
                ON CONFLICT(owner, tag) DO UPDATE SET email = excluded.email""",
                (owner, tag, email),
            )

    def delete_subscription(self, owner: str, tag: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM subscriptions WHERE owner = ? AND tag = ?", (owner, tag))

    def subscribers_for(self, tags: set[str]) -> list[dict]:
        if not tags:
            return []
        placeholders = ",".join("?" for _ in tags)
        with self.connect() as db:
            rows = db.execute(
                f"SELECT owner, tag, email FROM subscriptions WHERE tag IN ({placeholders})",
                tuple(tags),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        value = dict(row)
        value["tags"] = json.loads(value.pop("tags_json") or "{}")
        value["created_at"] = datetime.fromisoformat(value["created_at"])
        return value
