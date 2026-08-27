"""Dependency-light Member 3 S3 -> SQS -> Lambda media worker.

This handler intentionally uses only boto3 (included in the Lambda Python
runtime) plus Pillow, which is supplied in the deployment ZIP.  It makes the
AWS portion of the assignment demonstrable without Docker.  The large
PyTorch models live in the private GCS model bucket and are used later by the
separate inference service; this worker never pretends that a placeholder tag
is an ML species result.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.parse
from pathlib import Path

import boto3
from boto3.dynamodb.types import TypeSerializer

TABLE_NAME = os.environ["TABLE_NAME"]
MEDIA_BUCKET = os.environ["MEDIA_BUCKET"]
THUMBNAIL_SIZE = (480, 480)

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table(TABLE_NAME)
dynamodb = boto3.client("dynamodb")
serializer = TypeSerializer()


def _wire(values: dict) -> dict:
    """Encode normal Python values for DynamoDB's low-level transaction client."""
    return {key: serializer.serialize(value) for key, value in values.items()}


def _media_id(key: str) -> str | None:
    parts = key.split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "originals" else None


def _process(media_id: str, key: str) -> None:
    record = table.get_item(Key={"PK": f"MEDIA#{media_id}", "SK": "META"}).get("Item")
    if not record:
        # An object uploaded outside the API has no reservation to process.
        return
    try:
        table.update_item(
            Key={"PK": f"MEDIA#{media_id}", "SK": "META"},
            UpdateExpression="SET #status = :processing, #error = :empty",
            ConditionExpression="#status IN (:reserved, :uploaded, :failed)",
            ExpressionAttributeNames={"#status": "status", "#error": "error"},
            ExpressionAttributeValues={
                ":processing": "PROCESSING",
                ":reserved": "RESERVED",
                ":uploaded": "UPLOADED",
                ":failed": "FAILED",
                ":empty": None,
            },
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return

    thumbnail_key = None
    try:
        content_type = str(record.get("content_type", record.get("contentType", "")))
        if (
            os.getenv("ENABLE_THUMBNAILS", "false").lower() == "true"
            and content_type.startswith("image/")
        ):
            from PIL import Image

            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "source"
                thumbnail = Path(directory) / "thumbnail.jpg"
                s3.download_file(MEDIA_BUCKET, key, str(source))
                with Image.open(source) as image:
                    image = image.convert("RGB")
                    image.thumbnail(THUMBNAIL_SIZE)
                    image.save(thumbnail, "JPEG", quality=78, optimize=True)
                thumbnail_key = f"thumbnails/{media_id}.jpg"
                s3.upload_file(
                    str(thumbnail),
                    MEDIA_BUCKET,
                    thumbnail_key,
                    ExtraArgs={"ContentType": "image/jpeg"},
                )

        # This is explicitly a workflow-state tag, not an ML prediction.
        tags = {"pending_ml": 1}
        remote_schema = "mediaId" in record
        update_names = {"#status": "status", "#error": "error"}
        update_values = {
            ":ready": "READY",
            ":tags": tags,
            ":version": "awaiting-cloud-run-ml",
        }
        update_expression = "SET #status = :ready, tags = :tags"
        if remote_schema:
            update_expression += ", modelVersion = :version"
        else:
            update_expression += ", model_version = :version, sampled_frames = :frames"
            update_values[":frames"] = 1
        if thumbnail_key:
            update_expression += ", #thumbnail = :thumbnail"
            update_names["#thumbnail"] = "thumbnailUri" if remote_schema else "thumbnail_key"
            update_values[":thumbnail"] = (
                f"s3://{MEDIA_BUCKET}/{thumbnail_key}" if remote_schema else thumbnail_key
            )
        update_expression += " REMOVE #error"
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": _wire(
                            {
                                "PK": "TAG#pending_ml",
                                "SK": f"COUNT#0000000001#MEDIA#{media_id}",
                                "media_id": media_id,
                                "count": 1,
                            }
                        ),
                    }
                },
                {
                    "Update": {
                        "TableName": TABLE_NAME,
                        "Key": _wire({"PK": f"MEDIA#{media_id}", "SK": "META"}),
                        "UpdateExpression": update_expression,
                        "ExpressionAttributeNames": update_names,
                        "ExpressionAttributeValues": _wire(update_values),
                    }
                },
            ]
        )
    except Exception:
        table.update_item(
            Key={"PK": f"MEDIA#{media_id}", "SK": "META"},
            UpdateExpression="SET #status = :failed, #error = :error",
            ExpressionAttributeNames={"#status": "status", "#error": "error"},
            ExpressionAttributeValues={":failed": "FAILED", ":error": "Lambda processing failed"},
        )
        raise


def handler(event: dict, _context: object) -> None:
    """Consume SQS messages containing S3 ObjectCreated notifications."""
    for message in event.get("Records", []):
        body = json.loads(message["body"])
        for item in body.get("Records", []):
            key = urllib.parse.unquote_plus(item["s3"]["object"]["key"])
            media_id = _media_id(key)
            if media_id:
                _process(media_id, key)
