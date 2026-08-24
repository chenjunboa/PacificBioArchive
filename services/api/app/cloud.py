from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlparse

import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .domain import MediaStatus
from .repository import DuplicateChecksumError


def _normalise_numbers(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {key: _normalise_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_numbers(item) for item in value]
    return value


class DynamoDBRepository:
    """Stage-two DynamoDB adapter.

    It establishes the fixed keys and atomic checksum reservation used by the cloud
    deployment. Tag indexes and the remaining transactional hardening are deliberately
    left behind this interface for the stage-three handoff.
    """

    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise RuntimeError("TABLE_NAME is required in cloud mode")
        self.table_name = table_name
        self.resource = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.resource.Table(table_name)
        self.client = self.resource.meta.client

    @staticmethod
    def _media_key(media_id: str) -> dict[str, str]:
        return {"PK": f"MEDIA#{media_id}", "SK": "META"}

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
        serializer = TypeSerializer()

        def encode(item: dict) -> dict:
            return {key: serializer.serialize(value) for key, value in item.items()}
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": encode(lock_item),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": encode(media_item),
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

    def update_media(self, media_id: str, **changes) -> None:
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

    def find_by_tags(self, required: dict[str, int]) -> list[dict]:
        return [
            media
            for media in self.list_media(ready_only=True)
            if all(media["tags"].get(tag, 0) >= count for tag, count in required.items())
        ]

    def delete_media(self, media_id: str) -> None:
        record = self.get_media(media_id)
        if not record:
            return
        self.table.delete_item(Key=self._media_key(media_id))
        self.table.delete_item(Key={"PK": f"CHECKSUM#{record['checksum']}", "SK": "LOCK"})

    def upsert_subscription(self, owner: str, tag: str, email: str) -> None:
        self.table.put_item(
            Item={
                "PK": f"USER#{owner}",
                "SK": f"SUB#{tag}",
                "owner": owner,
                "tag": tag,
                "email": email,
                "status": "PENDING_CONFIRMATION",
            }
        )

    def delete_subscription(self, owner: str, tag: str) -> None:
        self.table.delete_item(Key={"PK": f"USER#{owner}", "SK": f"SUB#{tag}"})

    def subscribers_for(self, tags: set[str]) -> list[dict]:
        # SNS delivery is configured by the cloud deployment; stage three adds tag indexes.
        return []


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
