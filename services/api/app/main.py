from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from mangum import Mangum

from .auth import AuthService, current_user, get_auth_service
from .config import Settings, get_settings
from .domain import (
    BulkTagRequest,
    DeleteMediaRequest,
    DevTokenRequest,
    MediaStatus,
    MediaView,
    QueryFileInitRequest,
    SpeciesQueryRequest,
    SubscriptionRequest,
    TagQueryRequest,
    ThumbnailQueryRequest,
    UploadInitRequest,
    UploadInitResponse,
    User,
    normalize_tag,
)
from .repository import DuplicateChecksumError, SQLiteRepository
from .services import (
    InferenceClient,
    LocalStorage,
    MediaProcessor,
    NotificationService,
    QueryFileStore,
    sha256_file,
)


class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repository = SQLiteRepository(settings.database_path)
        self.storage = LocalStorage(settings.local_data_dir)
        self.inference = InferenceClient(settings)
        self.notifications = NotificationService(settings.local_data_dir, self.repository)
        self.query_files = QueryFileStore()
        self.processor = MediaProcessor(
            self.repository, self.storage, self.inference, self.notifications
        )


@lru_cache
def get_container() -> Container:
    return Container(get_settings())


def media_id_from_url(value: str) -> str:
    if re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        return value
    match = re.search(r"/media/([0-9a-fA-F-]{36})(?:/|$)", value)
    if not match:
        raise HTTPException(status_code=422, detail=f"Cannot resolve media URL: {value}")
    return match.group(1)


def to_view(request: Request, record: dict) -> MediaView:
    base = str(request.base_url).rstrip("/") + get_settings().api_prefix
    return MediaView(
        mediaId=record["media_id"],
        owner=record["owner"],
        filename=record["filename"],
        contentType=record["content_type"],
        size=record["size"],
        checksumSha256=record["checksum"],
        status=record["status"],
        tags=record["tags"],
        originalUrl=f"{base}/media/{record['media_id']}/content"
        if record.get("object_path")
        else None,
        thumbnailUrl=(
            f"{base}/media/{record['media_id']}/thumbnail" if record.get("thumbnail_path") else None
        ),
        modelVersion=record.get("model_version"),
        error=record.get("error"),
        createdAt=record["created_at"],
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Pacific BioArchive API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = settings.api_prefix

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "environment": settings.app_env}

    @app.post(f"{prefix}/auth/dev-token")
    def dev_token(
        payload: DevTokenRequest,
        auth: AuthService = Depends(get_auth_service),
    ) -> dict:
        token = auth.create_dev_token(payload.email, payload.givenName, payload.familyName)
        return {"accessToken": token, "tokenType": "Bearer", "expiresIn": 28800}

    @app.get(f"{prefix}/me")
    def me(user: User = Depends(current_user)) -> User:
        return user

    @app.post(f"{prefix}/uploads/init", response_model=UploadInitResponse)
    def initialise_upload(
        payload: UploadInitRequest,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> UploadInitResponse:
        limit = (
            settings.max_image_bytes
            if payload.contentType.startswith("image/")
            else settings.max_video_bytes
        )
        if payload.size > limit:
            raise HTTPException(status_code=413, detail=f"File exceeds {limit} byte limit")
        media_id = str(uuid4())
        try:
            container.repository.reserve_media(
                {
                    "media_id": media_id,
                    "owner": user.sub,
                    "filename": payload.filename,
                    "content_type": payload.contentType,
                    "size": payload.size,
                    "checksum": payload.checksumSha256.lower(),
                }
            )
        except DuplicateChecksumError as exc:
            raise HTTPException(
                status_code=409,
                detail={"message": "Duplicate file", "existingMediaId": exc.media_id},
            ) from exc
        return UploadInitResponse(
            mediaId=media_id,
            uploadUrl=f"{prefix}/uploads/{media_id}/content",
            objectKey=f"originals/{media_id}/{container.storage.safe_filename(payload.filename)}",
        )

    @app.put(f"{prefix}/uploads/{{media_id}}/content", status_code=202)
    async def upload_content(
        media_id: str,
        request: Request,
        background: BackgroundTasks,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        record = container.repository.get_media(media_id)
        if not record:
            raise HTTPException(status_code=404, detail="Upload reservation not found")
        if record["owner"] != user.sub:
            raise HTTPException(status_code=403, detail="Not the upload owner")
        if record["status"] != MediaStatus.RESERVED.value:
            raise HTTPException(status_code=409, detail="Upload has already been completed")
        body = await request.body()
        if len(body) != record["size"]:
            raise HTTPException(status_code=422, detail="Uploaded size does not match reservation")
        path = container.storage.media_path(media_id, record["filename"])
        path.write_bytes(body)
        if sha256_file(path) != record["checksum"]:
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="SHA-256 checksum mismatch")
        container.repository.update_media(
            media_id, object_path=str(path), status=MediaStatus.UPLOADED
        )
        background.add_task(container.processor.process, media_id)
        return {"mediaId": media_id, "status": MediaStatus.UPLOADED}

    @app.get(f"{prefix}/media/{{media_id}}", response_model=MediaView)
    def get_media(
        media_id: str,
        request: Request,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> MediaView:
        record = container.repository.get_media(media_id)
        if not record:
            raise HTTPException(status_code=404, detail="Media not found")
        return to_view(request, record)

    @app.get(f"{prefix}/media/{{media_id}}/content")
    def get_content(
        media_id: str,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> FileResponse:
        record = container.repository.get_media(media_id)
        if not record or not record.get("object_path"):
            raise HTTPException(status_code=404, detail="Content not found")
        return FileResponse(record["object_path"], media_type=record["content_type"])

    @app.get(f"{prefix}/media/{{media_id}}/thumbnail")
    def get_thumbnail(
        media_id: str,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> FileResponse:
        record = container.repository.get_media(media_id)
        if not record or not record.get("thumbnail_path"):
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(record["thumbnail_path"], media_type="image/jpeg")

    def query_views(
        required: dict[str, int], request: Request, container: Container
    ) -> list[MediaView]:
        return [to_view(request, row) for row in container.repository.find_by_tags(required)]

    @app.post(f"{prefix}/queries/tags", response_model=list[MediaView])
    def query_tags(
        payload: TagQueryRequest,
        request: Request,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> list[MediaView]:
        return query_views(payload.tags, request, container)

    @app.post(f"{prefix}/queries/species", response_model=list[MediaView])
    def query_species(
        payload: SpeciesQueryRequest,
        request: Request,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> list[MediaView]:
        return query_views({payload.species: 1}, request, container)

    @app.post(f"{prefix}/queries/thumbnail")
    def query_thumbnail(
        payload: ThumbnailQueryRequest,
        request: Request,
        _: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        media_id = media_id_from_url(payload.thumbnailUrl)
        record = container.repository.get_media(media_id)
        if not record or not record.get("thumbnail_path"):
            raise HTTPException(status_code=404, detail="Thumbnail mapping not found")
        return {"mediaId": media_id, "originalUrl": to_view(request, record).originalUrl}

    @app.post(f"{prefix}/queries/file/init")
    def query_file_init(
        payload: QueryFileInitRequest,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        item = container.query_files.create(
            user.sub, payload.filename, payload.contentType, payload.size
        )
        return {
            "queryId": item.query_id,
            "uploadUrl": f"{prefix}/queries/file/{item.query_id}/content",
        }

    @app.put(f"{prefix}/queries/file/{{query_id}}/content", status_code=204)
    async def query_file_upload(
        query_id: str,
        request: Request,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> Response:
        item = container.query_files.get(query_id)
        if not item:
            raise HTTPException(status_code=404, detail="Query reservation not found")
        if item.owner != user.sub:
            raise HTTPException(status_code=403, detail="Not the query owner")
        body = await request.body()
        if len(body) != item.size:
            raise HTTPException(status_code=422, detail="Query file size mismatch")
        path = container.storage.query_path(query_id, item.filename)
        path.write_bytes(body)
        container.query_files.set_path(query_id, path)
        return Response(status_code=204)

    @app.post(f"{prefix}/queries/file/{{query_id}}/execute", response_model=list[MediaView])
    def query_file_execute(
        query_id: str,
        request: Request,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> list[MediaView]:
        item = container.query_files.get(query_id)
        if not item or not item.path:
            raise HTTPException(status_code=404, detail="Uploaded query file not found")
        if item.owner != user.sub:
            raise HTTPException(status_code=403, detail="Not the query owner")
        try:
            tags, _ = container.inference.detect(Path(item.path), item.filename, item.content_type)
            required = {normalize_tag(tag): 1 for tag, count in tags.items() if count > 0}
            return query_views(required, request, container)
        finally:
            container.storage.delete_query(query_id)
            container.query_files.remove(query_id)

    @app.post(f"{prefix}/tags/bulk")
    def bulk_tags(
        payload: BulkTagRequest,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        updated: list[str] = []
        for value in payload.urls:
            media_id = media_id_from_url(value)
            record = container.repository.get_media(media_id)
            if not record:
                continue
            if record["owner"] != user.sub:
                raise HTTPException(status_code=403, detail=f"Not owner of {media_id}")
            tags = dict(record["tags"])
            if payload.operation == 1:
                for tag in payload.tags:
                    tags[tag] = max(tags.get(tag, 0), 1)
                container.notifications.publish(media_id, set(payload.tags))
            else:
                for tag in payload.tags:
                    tags.pop(tag, None)
            container.repository.update_media(media_id, tags=tags)
            updated.append(media_id)
        return {"updated": updated, "operation": payload.operation}

    @app.delete(f"{prefix}/media")
    def delete_media(
        payload: DeleteMediaRequest,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        deleted: list[str] = []
        for value in payload.urls:
            media_id = media_id_from_url(value)
            record = container.repository.get_media(media_id)
            if not record:
                continue
            if record["owner"] != user.sub:
                raise HTTPException(status_code=403, detail=f"Not owner of {media_id}")
            container.repository.update_media(media_id, status=MediaStatus.DELETING)
            container.storage.delete_media(record)
            container.repository.delete_media(media_id)
            deleted.append(media_id)
        return {"deleted": deleted}

    @app.post(f"{prefix}/subscriptions", status_code=201)
    def subscribe(
        payload: SubscriptionRequest,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> dict:
        container.repository.upsert_subscription(user.sub, payload.tag, str(payload.email))
        return {"tag": payload.tag, "email": str(payload.email), "status": "CONFIRMED_LOCAL"}

    @app.delete(f"{prefix}/subscriptions/{{tag}}", status_code=204)
    def unsubscribe(
        tag: str,
        user: User = Depends(current_user),
        container: Container = Depends(get_container),
    ) -> Response:
        container.repository.delete_subscription(user.sub, normalize_tag(tag))
        return Response(status_code=204)

    @app.get(f"{prefix}/species")
    def species(
        _: User = Depends(current_user),
        settings: Settings = Depends(get_settings),
    ) -> list[dict]:
        if not settings.labels_path.exists():
            return []
        result = []
        for line in settings.labels_path.read_text(encoding="utf-8").splitlines():
            fields = line.split(";")
            if len(fields) >= 7:
                result.append(
                    {
                        "tag": normalize_tag(f"{fields[4]}_{fields[5]}"),
                        "commonName": fields[6],
                    }
                )
        return result

    return app


app = create_app()
handler = Mangum(app)
