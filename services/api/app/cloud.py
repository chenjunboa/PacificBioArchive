from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote, urlparse

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .domain import MediaStatus, QueryFileReservation
from .repository import DuplicateChecksumError


def _normalise_numbers(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {key: _normalise_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_numbers(item) for item in value]
    return value


def _padded_count(count: int) -> str:
    return f"{int(count):010d}"


def _media_id_from_tag_item(item: dict) -> str:
    if item.get("mediaId"):
        return item["mediaId"]
    match = re.search(r"#MEDIA#(.+)$", item["SK"])
    if not match:
        raise ValueError(f"Cannot resolve media ID from tag item: {item}")
    return match.group(1)


def stable_thumbnail_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "s3":
        return f"https://{parsed.netloc}.s3.amazonaws.com/{quote(parsed.path.lstrip('/'))}"
    if parsed.scheme in {"http", "https"}:
        return parsed._replace(query="", fragment="").geturl()
    return value


def thumbnail_hash(value: str) -> str:
    return hashlib.sha256(stable_thumbnail_url(value).encode("utf-8")).hexdigest()


class DynamoDBRepository:
    """DynamoDB adapter for the cloud API.

    Media metadata, checksum locks, tag-count indexes, thumbnail mappings,
    subscriptions, and temporary query reservations all share the assignment's
    single-table PK/SK layout.
    """

    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise RuntimeError("TABLE_NAME is required in cloud mode")
        self.table_name = table_name
        self.resource = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.resource.Table(table_name)
        # Transactions use the low-level client because their Item fields must be
        # explicit DynamoDB AttributeValue maps.  The resource client installs a
        # document serializer and would serialize these maps a second time.
        self.client = boto3.client("dynamodb", region_name=region_name)
        self.serializer = TypeSerializer()

    def _wire(self, values: dict) -> dict:
        return {key: self.serializer.serialize(value) for key, value in values.items()}

    @staticmethod
    def _media_key(media_id: str) -> dict[str, str]:
        return {"PK": f"MEDIA#{media_id}", "SK": "META"}

    @staticmethod
    def _tag_key(tag: str, count: int, media_id: str) -> dict[str, str]:
        return {"PK": f"TAG#{tag}", "SK": f"COUNT#{_padded_count(count)}#MEDIA#{media_id}"}

    @staticmethod
    def _subscription_key(owner: str, tag: str) -> dict[str, str]:
        return {"PK": f"USER#{owner}", "SK": f"SUB#{tag}"}

    @staticmethod
    def _query_key(query_id: str) -> dict[str, str]:
        return {"PK": f"QUERY#{query_id}", "SK": "META"}

    @staticmethod
    def _thumb_key(value: str) -> dict[str, str]:
        return {"PK": f"THUMB#{thumbnail_hash(value)}", "SK": "MAP"}

    @staticmethod
    def _from_item(item: dict) -> dict:
        item = _normalise_numbers(item)
        return {
            "media_id": item["mediaId"],
            "owner": item["owner"],
            "filename": item["filename"],
            "content_type": item["contentType"],
            "size": item["size"],
            "checksum": item["checksum"],
            "object_path": item.get("objectUri"),
            "thumbnail_path": item.get("thumbnailUri"),
            "tags": item.get("tags", {}),
            "status": item["status"],
            "model_version": item.get("modelVersion"),
            "error": item.get("error"),
            "created_at": datetime.fromisoformat(item["createdAt"]),
        }

    def reserve_media(self, record: dict) -> None:
        created_at = datetime.now(UTC).isoformat()
        media_item = {
            **self._media_key(record["media_id"]),
            "mediaId": record["media_id"],
            "owner": record["owner"],
            "filename": record["filename"],
            "contentType": record["content_type"],
            "size": record["size"],
            "checksum": record["checksum"],
            "objectUri": record["object_path"],
            "tags": {},
            "status": MediaStatus.RESERVED.value,
            "createdAt": created_at,
            "GSI1PK": f"OWNER#{record['owner']}",
            "GSI1SK": f"{created_at}#MEDIA#{record['media_id']}",
        }
        lock_item = {
            "PK": f"CHECKSUM#{record['checksum']}",
            "SK": "LOCK",
            "mediaId": record["media_id"],
            "createdAt": created_at,
        }
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": self._wire(lock_item),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": self._wire(media_item),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                ]
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
                raise
            lock = self.table.get_item(
                Key={"PK": f"CHECKSUM#{record['checksum']}", "SK": "LOCK"},
                ConsistentRead=True,
            ).get("Item")
            if lock:
                raise DuplicateChecksumError(lock["mediaId"]) from exc
            raise

    def get_media(self, media_id: str) -> dict | None:
        item = self.table.get_item(Key=self._media_key(media_id), ConsistentRead=True).get("Item")
        return self._from_item(item) if item else None

    def list_media(self, ready_only: bool = False) -> list[dict]:
        # Stage three replaces this compatibility scan with TAG and owner indexes.
        expression = "SK = :meta"
        values: dict[str, object] = {":meta": "META"}
        if ready_only:
            expression += " AND #status = :ready"
            values[":ready"] = MediaStatus.READY.value
        kwargs = {"FilterExpression": expression, "ExpressionAttributeValues": values}
        if ready_only:
            kwargs["ExpressionAttributeNames"] = {"#status": "status"}
        response = self.table.scan(**kwargs)
        rows = [self._from_item(item) for item in response.get("Items", [])]
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def _tag_put_item(self, tag: str, count: int, media_id: str) -> dict:
        return {
            **self._tag_key(tag, count, media_id),
            "mediaId": media_id,
            "tag": tag,
            "count": int(count),
        }

    def _thumb_put_item(self, thumbnail_uri: str, media_id: str, original_uri: str | None) -> dict:
        return {
            **self._thumb_key(thumbnail_uri),
            "mediaId": media_id,
            "thumbnailUri": thumbnail_uri,
            "originalUri": original_uri,
            "stableThumbnailUrl": stable_thumbnail_url(thumbnail_uri),
        }

    def _write_index_changes(
        self,
        *,
        media_id: str,
        old_tags: dict[str, int] | None = None,
        new_tags: dict[str, int] | None = None,
        old_thumbnail: str | None = None,
        new_thumbnail: str | None = None,
        original_uri: str | None = None,
    ) -> None:
        actions: list[dict] = []
        old_tags = old_tags or {}
        new_tags = new_tags or {}
        for tag, count in old_tags.items():
            if new_tags.get(tag) != count:
                actions.append(
                    {
                        "Delete": {
                            "TableName": self.table_name,
                            "Key": self._wire(self._tag_key(tag, count, media_id)),
                        }
                    }
                )
        for tag, count in new_tags.items():
            if int(count) > 0 and old_tags.get(tag) != count:
                actions.append(
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": self._wire(self._tag_put_item(tag, int(count), media_id)),
                        }
                    }
                )
        old_thumb_keys = {thumbnail_hash(old_thumbnail)} if old_thumbnail else set()
        new_thumb_keys = {thumbnail_hash(new_thumbnail)} if new_thumbnail else set()
        for digest in old_thumb_keys - new_thumb_keys:
            actions.append(
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": self._wire({"PK": f"THUMB#{digest}", "SK": "MAP"}),
                    }
                }
            )
        if new_thumbnail and new_thumb_keys - old_thumb_keys:
            actions.append(
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": self._wire(
                            self._thumb_put_item(new_thumbnail, media_id, original_uri)
                        ),
                    }
                }
            )
        for index in range(0, len(actions), 25):
            chunk = actions[index : index + 25]
            if chunk:
                self.client.transact_write_items(TransactItems=chunk)

    def update_media(self, media_id: str, **changes) -> None:
        current = None
        if "tags" in changes or "thumbnail_path" in changes:
            current = self.get_media(media_id)
        names = {
            "object_path": "objectUri",
            "thumbnail_path": "thumbnailUri",
            "tags": "tags",
            "status": "status",
            "model_version": "modelVersion",
            "error": "error",
        }
        invalid = set(changes) - set(names)
        if invalid:
            raise ValueError(f"Unsupported media fields: {sorted(invalid)}")
        if not changes:
            return
        set_parts = []
        remove_parts = []
        attr_names = {}
        attr_values = {}
        for index, (key, value) in enumerate(changes.items()):
            name_token = f"#field{index}"
            value_token = f":value{index}"
            attr_names[name_token] = names[key]
            if isinstance(value, MediaStatus):
                value = value.value
            if value is None:
                remove_parts.append(name_token)
            else:
                set_parts.append(f"{name_token} = {value_token}")
                attr_values[value_token] = value
        sections = []
        if set_parts:
            sections.append("SET " + ", ".join(set_parts))
        if remove_parts:
            sections.append("REMOVE " + ", ".join(remove_parts))
        kwargs = {
            "Key": self._media_key(media_id),
            "UpdateExpression": " ".join(sections),
            "ExpressionAttributeNames": attr_names,
        }
        if attr_values:
            kwargs["ExpressionAttributeValues"] = attr_values
        self.table.update_item(**kwargs)
        if current:
            self._write_index_changes(
                media_id=media_id,
                old_tags=current.get("tags") if "tags" in changes else None,
                new_tags=changes.get("tags") if "tags" in changes else None,
                old_thumbnail=(
                    current.get("thumbnail_path") if "thumbnail_path" in changes else None
                ),
                new_thumbnail=(
                    changes.get("thumbnail_path") if "thumbnail_path" in changes else None
                ),
                original_uri=current.get("object_path"),
            )

    def find_by_tags(self, required: dict[str, int]) -> list[dict]:
        matches: set[str] | None = None
        for tag, count in required.items():
            media_ids: set[str] = set()
            start_key = None
            while True:
                kwargs = {
                    "KeyConditionExpression": Key("PK").eq(f"TAG#{tag}")
                    & Key("SK").between(
                        f"COUNT#{_padded_count(count)}#", "COUNT#9999999999#MEDIA#~"
                    )
                }
                if start_key:
                    kwargs["ExclusiveStartKey"] = start_key
                response = self.table.query(**kwargs)
                media_ids.update(
                    _media_id_from_tag_item(item) for item in response.get("Items", [])
                )
                start_key = response.get("LastEvaluatedKey")
                if not start_key:
                    break
            matches = media_ids if matches is None else matches & media_ids
            if not matches:
                return []
        rows = [self.get_media(media_id) for media_id in sorted(matches or set())]
        return [row for row in rows if row and row["status"] == MediaStatus.READY.value]

    def media_id_for_thumbnail(self, thumbnail_url: str) -> str | None:
        item = self.table.get_item(
            Key=self._thumb_key(thumbnail_url), ConsistentRead=True
        ).get("Item")
        return item.get("mediaId") if item else None

    def delete_media(self, media_id: str) -> None:
        record = self.get_media(media_id)
        if not record:
            return
        actions = [
            {
                "Delete": {
                    "TableName": self.table_name,
                    "Key": self._wire(self._media_key(media_id)),
                }
            },
            {
                "Delete": {
                    "TableName": self.table_name,
                    "Key": self._wire({"PK": f"CHECKSUM#{record['checksum']}", "SK": "LOCK"}),
                }
            },
        ]
        for tag, count in record["tags"].items():
            actions.append(
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": self._wire(self._tag_key(tag, int(count), media_id)),
                    }
                }
            )
        if record.get("thumbnail_path"):
            actions.append(
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": self._wire(self._thumb_key(record["thumbnail_path"])),
                    }
                }
            )
        for index in range(0, len(actions), 25):
            self.client.transact_write_items(TransactItems=actions[index : index + 25])

    def upsert_subscription(self, owner: str, tag: str, email: str) -> None:
        item = {
            "owner": owner,
            "tag": tag,
            "email": email,
            "status": "PENDING_CONFIRMATION",
        }
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": self._wire({**self._subscription_key(owner, tag), **item}),
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": self._wire(
                            {**item, "PK": f"TAG#{tag}", "SK": f"SUB#{owner}"}
                        ),
                    }
                },
            ]
        )

    def delete_subscription(self, owner: str, tag: str) -> None:
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": self._wire(self._subscription_key(owner, tag)),
                    }
                },
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": self._wire({"PK": f"TAG#{tag}", "SK": f"SUB#{owner}"}),
                    }
                },
            ]
        )

    def subscribers_for(self, tags: set[str]) -> list[dict]:
        subscribers: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for tag in tags:
            start_key = None
            while True:
                kwargs = {
                    "KeyConditionExpression": Key("PK").eq(f"TAG#{tag}")
                    & Key("SK").begins_with("SUB#")
                }
                if start_key:
                    kwargs["ExclusiveStartKey"] = start_key
                response = self.table.query(**kwargs)
                for item in response.get("Items", []):
                    key = (item["owner"], item["tag"])
                    if key not in seen:
                        subscribers.append(dict(item))
                        seen.add(key)
                start_key = response.get("LastEvaluatedKey")
                if not start_key:
                    break
        return subscribers

    def create_query_file(
        self,
        query_id: str,
        owner: str,
        filename: str,
        content_type: str,
        size: int,
        object_uri: str,
    ) -> QueryFileReservation:
        item = QueryFileReservation(
            query_id=query_id,
            owner=owner,
            filename=filename,
            content_type=content_type,
            size=size,
        )
        self.table.put_item(
            Item={
                **self._query_key(item.query_id),
                "queryId": item.query_id,
                "owner": owner,
                "filename": filename,
                "contentType": content_type,
                "size": size,
                "objectUri": object_uri,
                "createdAt": item.created_at.isoformat(),
                "ttl": int(item.created_at.timestamp()) + 86400,
            }
        )
        item.path = object_uri
        return item

    def get_query_file(self, query_id: str) -> QueryFileReservation | None:
        item = self.table.get_item(
            Key=self._query_key(query_id), ConsistentRead=True
        ).get("Item")
        if not item:
            return None
        value = _normalise_numbers(item)
        return QueryFileReservation(
            query_id=value["queryId"],
            owner=value["owner"],
            filename=value["filename"],
            content_type=value["contentType"],
            size=value["size"],
            path=value.get("objectUri"),
            created_at=datetime.fromisoformat(value["createdAt"]),
        )

    def delete_query_file(self, query_id: str) -> None:
        self.table.delete_item(Key=self._query_key(query_id))


class S3Storage:
    def __init__(self, bucket: str, region_name: str, expires_in: int = 900):
        if not bucket:
            raise RuntimeError("MEDIA_BUCKET is required in cloud mode")
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region_name)
        self.expires_in = expires_in

    @staticmethod
    def safe_filename(filename: str) -> str:
        name = Path(filename).name
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "upload.bin"

    def media_key(self, media_id: str, filename: str) -> str:
        return f"originals/{media_id}/{self.safe_filename(filename)}"

    def thumbnail_key(self, media_id: str) -> str:
        return f"thumbnails/{media_id}.jpg"

    def query_key(self, query_id: str, filename: str) -> str:
        return f"temporary-queries/{query_id}/{self.safe_filename(filename)}"

    def uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    def create_upload(
        self,
        media_id: str,
        key: str,
        content_type: str,
        size: int,
        checksum: str,
    ) -> dict:
        fields = {
            "Content-Type": content_type,
            "x-amz-meta-media-id": media_id,
            "x-amz-meta-checksum-sha256": checksum,
        }
        conditions = [
            {"Content-Type": content_type},
            {"x-amz-meta-media-id": media_id},
            {"x-amz-meta-checksum-sha256": checksum},
            ["content-length-range", size, size],
        ]
        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=self.expires_in,
        )

    def create_query_upload(
        self,
        key: str,
        content_type: str,
        size: int,
    ) -> dict:
        fields = {"Content-Type": content_type}
        conditions = [
            {"Content-Type": content_type},
            ["content-length-range", size, size],
        ]
        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=self.expires_in,
        )

    @staticmethod
    def _split_uri(uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
            raise ValueError("Expected a stable s3:// URI")
        return parsed.netloc, parsed.path.lstrip("/")

    def read_url(self, uri: str | None) -> str | None:
        if not uri:
            return None
        bucket, key = self._split_uri(uri)
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=self.expires_in,
        )

    def download_to_temp(self, uri: str, suffix: str = "") -> Path:
        bucket, key = self._split_uri(uri)
        temporary = NamedTemporaryFile(suffix=suffix, delete=False)
        temporary.close()
        path = Path(temporary.name)
        try:
            self.client.download_file(bucket, key, str(path))
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path

    def delete_uri(self, uri: str | None) -> None:
        if not uri:
            return
        bucket, key = self._split_uri(uri)
        if bucket != self.bucket:
            raise ValueError("Refusing to delete an object outside MEDIA_BUCKET")
        self.client.delete_object(Bucket=bucket, Key=key)

    def delete_media(self, record: dict) -> None:
        objects = []
        for field in ("object_path", "thumbnail_path"):
            if record.get(field):
                bucket, key = self._split_uri(record[field])
                if bucket != self.bucket:
                    raise ValueError("Refusing to delete an object outside MEDIA_BUCKET")
                objects.append({"Key": key})
        if objects:
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})

    def describe_uri(self, uri: str) -> str:
        bucket, key = self._split_uri(uri)
        return f"https://{bucket}.s3.amazonaws.com/{quote(key)}"


class SNSNotificationService:
    def __init__(self, topic_arn: str):
        self.topic_arn = topic_arn
        self.client = boto3.client("sns") if topic_arn else None

    def publish(self, media_id: str, tags: set[str]) -> None:
        if not self.client or not tags:
            return
        self.client.publish(
            TopicArn=self.topic_arn,
            Subject="Pacific BioArchive species update",
            Message=f"Media {media_id} contains: {', '.join(sorted(tags))}",
        )
