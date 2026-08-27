from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from threading import Lock
from uuid import uuid4

import httpx
from PIL import Image

from .config import Settings
from .domain import MediaStatus, QueryFileReservation, normalize_tag
from .repository import SQLiteRepository


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.originals = root / "originals"
        self.thumbnails = root / "thumbnails"
        self.queries = root / "queries"
        for folder in (self.originals, self.thumbnails, self.queries):
            folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_filename(filename: str) -> str:
        name = Path(filename).name
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "upload.bin"

    def media_path(self, media_id: str, filename: str) -> Path:
        folder = self.originals / media_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder / self.safe_filename(filename)

    def media_key(self, media_id: str, filename: str) -> str:
        return f"originals/{media_id}/{self.safe_filename(filename)}"

    def thumbnail_path(self, media_id: str) -> Path:
        return self.thumbnails / f"{media_id}.jpg"

    def query_path(self, query_id: str, filename: str) -> Path:
        folder = self.queries / query_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder / self.safe_filename(filename)

    def delete_media(self, record: dict) -> None:
        if record.get("object_path"):
            path = Path(record["object_path"])
            if path.exists():
                path.unlink()
            if path.parent.exists() and not any(path.parent.iterdir()):
                path.parent.rmdir()
        if record.get("thumbnail_path"):
            path = Path(record["thumbnail_path"])
            if path.exists():
                path.unlink()

    def delete_query(self, query_id: str) -> None:
        folder = self.queries / query_id
        if folder.exists():
            shutil.rmtree(folder)


class InferenceClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.gcp_wif_audience or not self.settings.gcp_wif_service_account:
            return {}
        from google.auth import aws, impersonated_credentials
        from google.auth.transport.requests import Request

        external = aws.Credentials(
            audience=self.settings.gcp_wif_audience,
            subject_token_type="urn:ietf:params:aws:token-type:aws4_request",
            credential_source={
                "environment_id": "aws1",
                "region_url": (
                    "http://169.254.169.254/latest/meta-data/placement/availability-zone"
                ),
                "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
                "regional_cred_verification_url": (
                    "https://sts.{region}.amazonaws.com"
                    "?Action=GetCallerIdentity&Version=2011-06-15"
                ),
            },
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        target = impersonated_credentials.Credentials(
            source_credentials=external,
            target_principal=self.settings.gcp_wif_service_account,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            lifetime=900,
        )
        identity = impersonated_credentials.IDTokenCredentials(
            target,
            target_audience=self.settings.inference_url.rstrip("/"),
            include_email=True,
        )
        identity.refresh(Request())
        if not identity.token:
            raise RuntimeError("GCP WIF did not return an ID token")
        return {"Authorization": f"Bearer {identity.token}"}

    def detect(self, path: Path, filename: str, content_type: str) -> tuple[dict[str, int], str]:
        if self.settings.inference_mode == "http":
            with path.open("rb") as file:
                response = httpx.post(
                    f"{self.settings.inference_url.rstrip('/')}/infer",
                    headers=self._headers(),
                    files={"file": (filename, file, content_type)},
                    timeout=600,
                )
            response.raise_for_status()
            payload = response.json()
            return payload["tags"], payload["modelVersion"]
        stem = Path(filename).stem
        tag = re.sub(r"[_-]?\d+$", "", stem)
        return {normalize_tag(tag): 1}, self.settings.model_version


class NotificationService:
    def __init__(self, root: Path, repository: SQLiteRepository):
        self.path = root / "notifications.jsonl"
        self.repository = repository

    def publish(self, media_id: str, tags: set[str]) -> None:
        subscribers = self.repository.subscribers_for(tags)
        if not subscribers:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as output:
            for subscriber in subscribers:
                output.write(json.dumps({"mediaId": media_id, **subscriber}) + "\n")


class QueryFileStore:
    def __init__(self):
        self._items: dict[str, QueryFileReservation] = {}
        self._lock = Lock()

    def create(
        self, owner: str, filename: str, content_type: str, size: int
    ) -> QueryFileReservation:
        item = QueryFileReservation(
            query_id=str(uuid4()),
            owner=owner,
            filename=filename,
            content_type=content_type,
            size=size,
        )
        with self._lock:
            self._items[item.query_id] = item
        return item

    def get(self, query_id: str) -> QueryFileReservation | None:
        return self._items.get(query_id)

    def set_path(self, query_id: str, path: Path) -> None:
        with self._lock:
            self._items[query_id].path = str(path)

    def remove(self, query_id: str) -> None:
        with self._lock:
            self._items.pop(query_id, None)


class MediaProcessor:
    def __init__(
        self,
        repository: SQLiteRepository,
        storage: LocalStorage,
        inference: InferenceClient,
        notifications: NotificationService,
    ):
        self.repository = repository
        self.storage = storage
        self.inference = inference
        self.notifications = notifications

    def process(self, media_id: str) -> None:
        record = self.repository.get_media(media_id)
        if not record or not record.get("object_path"):
            return
        self.repository.update_media(media_id, status=MediaStatus.PROCESSING, error=None)
        try:
            thumbnail_path = None
            if record["content_type"].startswith("image/"):
                thumbnail_path = self.storage.thumbnail_path(media_id)
                with Image.open(record["object_path"]) as source:
                    image = source.convert("RGB")
                    image.thumbnail((480, 480), Image.Resampling.LANCZOS)
                    image.save(thumbnail_path, "JPEG", quality=78, optimize=True)
            tags, model_version = self.inference.detect(
                Path(record["object_path"]), record["filename"], record["content_type"]
            )
            tags = {normalize_tag(tag): int(count) for tag, count in tags.items() if int(count) > 0}
            self.repository.update_media(
                media_id,
                thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
                tags=tags,
                model_version=model_version,
                status=MediaStatus.READY,
                error=None,
            )
            self.notifications.publish(media_id, set(tags))
        except Exception as exc:
            self.repository.update_media(
                media_id, status=MediaStatus.FAILED, error=f"{type(exc).__name__}: {exc}"
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
