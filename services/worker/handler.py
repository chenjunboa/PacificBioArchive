from __future__ import annotations

import hashlib
import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote_plus, urlparse

import boto3
import httpx
from boto3.dynamodb.types import TypeSerializer
from google.auth import aws, impersonated_credentials
from google.auth.transport.requests import Request
from PIL import Image


@lru_cache
def s3_client():
    return boto3.client("s3")


@lru_cache
def dynamodb_table():
    table_name = os.environ["TABLE_NAME"]
    return boto3.resource("dynamodb").Table(table_name)


@lru_cache
def sns_client():
    return boto3.client("sns")


@lru_cache
def dynamodb_client():
    return boto3.client("dynamodb")


@lru_cache
def serializer():
    return TypeSerializer()


def _wire(values: dict) -> dict:
    return {key: serializer().serialize(value) for key, value in values.items()}


def _padded_count(count: int) -> str:
    return f"{int(count):010d}"


def _tag_key(tag: str, count: int, media_id: str) -> dict[str, str]:
    return {"PK": f"TAG#{tag}", "SK": f"COUNT#{_padded_count(count)}#MEDIA#{media_id}"}


def _stable_thumbnail_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "s3":
        return f"https://{parsed.netloc}.s3.amazonaws.com/{quote(parsed.path.lstrip('/'))}"
    if parsed.scheme in {"http", "https"}:
        return parsed._replace(query="", fragment="").geturl()
    return value


def _thumbnail_hash(value: str) -> str:
    return hashlib.sha256(_stable_thumbnail_url(value).encode("utf-8")).hexdigest()


def _replace_indexes(
    media_id: str,
    old_tags: dict[str, int],
    new_tags: dict[str, int],
    thumbnail_uri: str | None,
    original_uri: str,
) -> None:
    actions: list[dict] = []
    for tag, count in old_tags.items():
        if new_tags.get(tag) != count:
            actions.append(
                {
                    "Delete": {
                        "TableName": os.environ["TABLE_NAME"],
                        "Key": _wire(_tag_key(tag, int(count), media_id)),
                    }
                }
            )
    for tag, count in new_tags.items():
        if int(count) > 0 and old_tags.get(tag) != count:
            actions.append(
                {
                    "Put": {
                        "TableName": os.environ["TABLE_NAME"],
                        "Item": _wire(
                            {
                                **_tag_key(tag, int(count), media_id),
                                "mediaId": media_id,
                                "tag": tag,
                                "count": int(count),
                            }
                        ),
                    }
                }
            )
    if thumbnail_uri:
        actions.append(
            {
                "Put": {
                    "TableName": os.environ["TABLE_NAME"],
                    "Item": _wire(
                        {
                            "PK": f"THUMB#{_thumbnail_hash(thumbnail_uri)}",
                            "SK": "MAP",
                            "mediaId": media_id,
                            "thumbnailUri": thumbnail_uri,
                            "originalUri": original_uri,
                            "stableThumbnailUrl": _stable_thumbnail_url(thumbnail_uri),
                        }
                    ),
                }
            }
        )
    for index in range(0, len(actions), 25):
        chunk = actions[index : index + 25]
        if chunk:
            dynamodb_client().transact_write_items(TransactItems=chunk)


def _wif_id_token(target_audience: str) -> str:
    """Exchange the Lambda AWS role for a short-lived Google ID token."""
    external = aws.Credentials(
        audience=os.environ["GCP_WIF_AUDIENCE"],
        subject_token_type="urn:ietf:params:aws:token-type:aws4_request",
        credential_source={
            "environment_id": "aws1",
            "region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
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
        target_principal=os.environ["GCP_WIF_SERVICE_ACCOUNT"],
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        lifetime=900,
    )
    identity = impersonated_credentials.IDTokenCredentials(
        target,
        target_audience=target_audience,
        include_email=True,
    )
    identity.refresh(Request())
    if not identity.token:
        raise RuntimeError("GCP WIF did not return an ID token")
    return identity.token


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _media_id_from_key(key: str, metadata: dict[str, str]) -> str:
    media_id = metadata.get("media-id", "")
    if media_id:
        return media_id
    parts = key.split("/")
    if len(parts) >= 3 and parts[0] == "originals":
        return parts[1]
    raise ValueError("S3 object is missing its media ID")


def _thumbnail(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        converted = image.convert("RGB")
        converted.thumbnail((480, 480), Image.Resampling.LANCZOS)
        converted.save(destination, "JPEG", quality=78, optimize=True)


def _infer(path: Path, filename: str, content_type: str) -> dict:
    inference_url = os.environ["INFERENCE_URL"].rstrip("/")
    token = _wif_id_token(inference_url)
    with path.open("rb") as source:
        response = httpx.post(
            f"{inference_url}/infer",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, source, content_type)},
            timeout=840,
        )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result.get("tags"), dict) or not result.get("modelVersion"):
        raise RuntimeError("Inference response is missing tags or modelVersion")
    return result


def _mark_failed(media_id: str, reason: Exception) -> None:
    safe_reason = f"{type(reason).__name__}: {reason}"[:240]
    dynamodb_table().update_item(
        Key={"PK": f"MEDIA#{media_id}", "SK": "META"},
        UpdateExpression="SET #status = :failed, #error = :error",
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={":failed": "FAILED", ":error": safe_reason},
    )


def _process_s3_record(record: dict) -> None:
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    if not key.startswith("originals/"):
        return
    head = s3_client().head_object(Bucket=bucket, Key=key)
    metadata = head.get("Metadata", {})
    media_id = _media_id_from_key(key, metadata)
    table = dynamodb_table()
    item = table.get_item(
        Key={"PK": f"MEDIA#{media_id}", "SK": "META"}, ConsistentRead=True
    ).get("Item")
    if not item:
        raise ValueError(f"No media reservation exists for {media_id}")
    if item.get("status") == "READY":
        return
    table.update_item(
        Key={"PK": f"MEDIA#{media_id}", "SK": "META"},
        UpdateExpression="SET #status = :processing REMOVE #error",
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={":processing": "PROCESSING"},
    )
    suffix = Path(item["filename"]).suffix
    with tempfile.TemporaryDirectory(prefix="pba-") as directory:
        source_path = Path(directory) / f"source{suffix}"
        s3_client().download_file(bucket, key, str(source_path))
        expected_checksum = metadata.get("checksum-sha256") or item["checksum"]
        if _sha256(source_path) != expected_checksum:
            raise ValueError("Uploaded object checksum does not match its reservation")
        thumbnail_uri = None
        if item["contentType"].startswith("image/"):
            thumbnail_path = Path(directory) / "thumbnail.jpg"
            _thumbnail(source_path, thumbnail_path)
            thumbnail_key = f"thumbnails/{media_id}.jpg"
            s3_client().upload_file(
                str(thumbnail_path),
                bucket,
                thumbnail_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            thumbnail_uri = f"s3://{bucket}/{thumbnail_key}"
        result = _infer(source_path, item["filename"], item["contentType"])
    expression = (
        "SET #status = :ready, tags = :tags, modelVersion = :version, "
        "objectUri = :object_uri"
    )
    names = {"#status": "status"}
    new_tags = {tag: int(count) for tag, count in result["tags"].items() if int(count) > 0}
    values = {
        ":ready": "READY",
        ":tags": new_tags,
        ":version": result["modelVersion"],
        ":object_uri": f"s3://{bucket}/{key}",
    }
    if thumbnail_uri:
        expression += ", thumbnailUri = :thumbnail_uri"
        values[":thumbnail_uri"] = thumbnail_uri
    expression += " REMOVE #error"
    names["#error"] = "error"
    table.update_item(
        Key={"PK": f"MEDIA#{media_id}", "SK": "META"},
        UpdateExpression=expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )
    _replace_indexes(
        media_id,
        {tag: int(count) for tag, count in item.get("tags", {}).items()},
        new_tags,
        thumbnail_uri,
        values[":object_uri"],
    )
    topic_arn = os.getenv("NOTIFICATION_TOPIC_ARN")
    if topic_arn and new_tags:
        sns_client().publish(
            TopicArn=topic_arn,
            Subject="Pacific BioArchive species update",
            Message=f"Media {media_id} contains: {', '.join(sorted(new_tags))}",
        )


def lambda_handler(event: dict, _context) -> dict:
    failures = []
    for message in event.get("Records", []):
        message_id = message.get("messageId", "unknown")
        try:
            body = json.loads(message["body"])
            for record in body.get("Records", []):
                try:
                    _process_s3_record(record)
                except Exception as exc:
                    metadata = s3_client().head_object(
                        Bucket=record["s3"]["bucket"]["name"],
                        Key=unquote_plus(record["s3"]["object"]["key"]),
                    ).get("Metadata", {})
                    media_id = _media_id_from_key(
                        unquote_plus(record["s3"]["object"]["key"]), metadata
                    )
                    if int(message.get("attributes", {}).get("ApproximateReceiveCount", "1")) >= 3:
                        _mark_failed(media_id, exc)
                    raise
        except Exception:
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
