import hashlib
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

os.environ["APP_ENV"] = "local"
os.environ["LOCAL_DATA_DIR"] = tempfile.mkdtemp(prefix="bioarchive-tests-")
os.environ["LABELS_PATH"] = str(Path(__file__).resolve().parents[3] / "labels.txt")

from app.main import app, get_container  # noqa: E402
from app.repository import DuplicateChecksumError, SQLiteRepository  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

client = TestClient(app)


def token(email: str = "owner@example.com") -> str:
    response = client.post(
        "/api/v1/auth/dev-token",
        json={"email": email, "givenName": "Test", "familyName": "User"},
    )
    assert response.status_code == 200
    return response.json()["accessToken"]


def headers(email: str = "owner@example.com") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(email)}"}


def image_bytes(size: tuple[int, int] = (900, 450), colour=(20, 120, 50)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, colour).save(output, "JPEG")
    return output.getvalue()


def upload(filename: str, body: bytes, auth: dict[str, str] | None = None) -> dict:
    auth = auth or headers()
    checksum = hashlib.sha256(body).hexdigest()
    init = client.post(
        "/api/v1/uploads/init",
        headers=auth,
        json={
            "filename": filename,
            "contentType": "image/jpeg",
            "size": len(body),
            "checksumSha256": checksum,
        },
    )
    assert init.status_code == 200, init.text
    reservation = init.json()
    sent = client.put(reservation["uploadUrl"], headers=auth, content=body)
    assert sent.status_code == 202, sent.text
    result = client.get(f"/api/v1/media/{reservation['mediaId']}", headers=auth)
    assert result.status_code == 200
    return result.json()


def test_authentication_required():
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/health").json()["status"] == "ok"


def test_complete_image_workflow_and_duplicate_detection():
    auth = headers("workflow@example.com")
    body = image_bytes()
    media = upload("Alectura_lathami_1.JPG", body, auth)
    assert media["status"] == "READY"
    assert media["tags"] == {"alectura_lathami": 1}
    assert media["thumbnailUrl"]

    thumbnail = client.get(media["thumbnailUrl"], headers=auth)
    assert thumbnail.status_code == 200
    with Image.open(BytesIO(thumbnail.content)) as thumb:
        assert thumb.width <= 480 and thumb.height <= 480
        assert thumb.width / thumb.height == 2

    duplicate = client.post(
        "/api/v1/uploads/init",
        headers=auth,
        json={
            "filename": "renamed.jpg",
            "contentType": "image/jpeg",
            "size": len(body),
            "checksumSha256": hashlib.sha256(body).hexdigest(),
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["existingMediaId"] == media["mediaId"]


def test_tag_and_species_queries_use_and_and_minimum_counts():
    auth = headers("query@example.com")
    media = upload("Bos_taurus_1.JPG", image_bytes(colour=(90, 40, 30)), auth)
    update = client.post(
        "/api/v1/tags/bulk",
        headers=auth,
        json={
            "urls": [media["originalUrl"]],
            "tags": ["Wombat", "Magpie"],
            "operation": 1,
        },
    )
    assert update.status_code == 200

    matches = client.post(
        "/api/v1/queries/tags",
        headers=auth,
        json={"tags": {"wombat": 1, "magpie": 1}},
    )
    assert [item["mediaId"] for item in matches.json()] == [media["mediaId"]]
    no_match = client.post(
        "/api/v1/queries/tags",
        headers=auth,
        json={"tags": {"wombat": 2, "magpie": 1}},
    )
    assert no_match.json() == []
    species = client.post("/api/v1/queries/species", headers=auth, json={"species": "Bos-taurus"})
    assert any(item["mediaId"] == media["mediaId"] for item in species.json())


def test_thumbnail_reverse_query_and_temporary_file_cleanup():
    auth = headers("reverse@example.com")
    media = upload("Felis_catus_3.JPG", image_bytes(colour=(10, 10, 10)), auth)
    reverse = client.post(
        "/api/v1/queries/thumbnail",
        headers=auth,
        json={"thumbnailUrl": media["thumbnailUrl"]},
    )
    assert reverse.status_code == 200
    assert reverse.json()["originalUrl"] == media["originalUrl"]

    query_body = image_bytes(size=(300, 300), colour=(5, 5, 5))
    init = client.post(
        "/api/v1/queries/file/init",
        headers=auth,
        json={
            "filename": "Felis_catus_99.JPG",
            "contentType": "image/jpeg",
            "size": len(query_body),
        },
    ).json()
    assert client.put(init["uploadUrl"], headers=auth, content=query_body).status_code == 204
    result = client.post(f"/api/v1/queries/file/{init['queryId']}/execute", headers=auth)
    assert any(item["mediaId"] == media["mediaId"] for item in result.json())
    assert get_container().query_files.get(init["queryId"]) is None
    assert not (get_container().storage.queries / init["queryId"]).exists()


def test_owner_only_mutation_and_idempotent_delete():
    owner = headers("delete-owner@example.com")
    stranger = headers("stranger@example.com")
    media = upload("Sus_scrofa_1.JPG", image_bytes(colour=(70, 70, 70)), owner)
    forbidden = client.post(
        "/api/v1/tags/bulk",
        headers=stranger,
        json={"urls": [media["originalUrl"]], "tags": ["reviewed"], "operation": 1},
    )
    assert forbidden.status_code == 403
    deleted = client.request(
        "DELETE", "/api/v1/media", headers=owner, json={"urls": [media["originalUrl"]]}
    )
    assert deleted.json()["deleted"] == [media["mediaId"]]
    repeated = client.request(
        "DELETE", "/api/v1/media", headers=owner, json={"urls": [media["mediaId"]]}
    )
    assert repeated.status_code == 200
    assert repeated.json()["deleted"] == []


def test_subscription_writes_matching_local_notification():
    auth = headers("notify@example.com")
    subscribed = client.post(
        "/api/v1/subscriptions",
        headers=auth,
        json={"tag": "Casuarius casuarius", "email": "notify@example.com"},
    )
    assert subscribed.status_code == 201
    media = upload("Casuarius_casuarius_1.JPG", image_bytes(colour=(12, 80, 120)), auth)
    log = get_container().settings.local_data_dir / "notifications.jsonl"
    assert media["mediaId"] in log.read_text(encoding="utf-8")


def test_repository_concurrent_checksum_reservation(tmp_path):
    repository = SQLiteRepository(tmp_path / "concurrent.sqlite3")

    def reserve(index: int) -> str:
        try:
            repository.reserve_media(
                {
                    "media_id": f"media-{index}",
                    "owner": "owner",
                    "filename": "same.jpg",
                    "content_type": "image/jpeg",
                    "size": 100,
                    "checksum": "f" * 64,
                }
            )
            return "created"
        except DuplicateChecksumError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reserve, range(4)))
    assert results.count("created") == 1
    assert results.count("duplicate") == 3
