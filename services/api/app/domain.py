from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png"}
SUPPORTED_VIDEO_TYPES = {"video/mp4", "video/quicktime"}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_VIDEO_TYPES


class MediaStatus(StrEnum):
    RESERVED = "RESERVED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


def normalize_tag(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip().lower()
    value = re.sub(r"[\s-]+", "_", value)
    if not value or len(value) > 64:
        raise ValueError("Tag must contain 1-64 characters")
    if not re.fullmatch(r"[\w.]+", value, flags=re.UNICODE):
        raise ValueError("Tag contains unsupported characters")
    return value


class User(BaseModel):
    sub: str
    email: str
    given_name: str = ""
    family_name: str = ""


class DevTokenRequest(BaseModel):
    email: EmailStr
    givenName: str = "Prototype"
    familyName: str = "User"


class UploadInitRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    contentType: str
    size: int = Field(gt=0)
    checksumSha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    @field_validator("contentType")
    @classmethod
    def supported_content_type(cls, value: str) -> str:
        if value not in SUPPORTED_TYPES:
            raise ValueError("Supported types: JPG, JPEG, PNG, MP4 and MOV")
        return value


class UploadInitResponse(BaseModel):
    mediaId: str
    uploadUrl: str
    objectKey: str


class MediaView(BaseModel):
    mediaId: str
    owner: str
    filename: str
    contentType: str
    size: int
    checksumSha256: str
    status: MediaStatus
    tags: dict[str, int] = {}
    originalUrl: str | None = None
    thumbnailUrl: str | None = None
    modelVersion: str | None = None
    error: str | None = None
    createdAt: datetime


class TagQueryRequest(BaseModel):
    tags: dict[str, Annotated[int, Field(ge=1)]]

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("At least one tag is required")
        return {normalize_tag(tag): count for tag, count in value.items()}


class SpeciesQueryRequest(BaseModel):
    species: str

    @field_validator("species")
    @classmethod
    def normalize_species(cls, value: str) -> str:
        return normalize_tag(value)


class ThumbnailQueryRequest(BaseModel):
    thumbnailUrl: str


class QueryFileInitRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    contentType: str
    size: int = Field(gt=0)

    @field_validator("contentType")
    @classmethod
    def supported_content_type(cls, value: str) -> str:
        if value not in SUPPORTED_TYPES:
            raise ValueError("Unsupported query file type")
        return value


class BulkTagRequest(BaseModel):
    urls: list[str] = Field(min_length=1)
    tags: list[str] = Field(min_length=1)
    operation: int = Field(ge=0, le=1)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_tag(tag) for tag in value))


class DeleteMediaRequest(BaseModel):
    urls: list[str] = Field(min_length=1)


class SubscriptionRequest(BaseModel):
    tag: str
    email: EmailStr

    @field_validator("tag")
    @classmethod
    def normalize_subscription_tag(cls, value: str) -> str:
        return normalize_tag(value)


class QueryFileReservation(BaseModel):
    query_id: str
    owner: str
    filename: str
    content_type: str
    size: int
    path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
