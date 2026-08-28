from io import BytesIO

from PIL import Image

from services.worker import handler
from services.worker.handler import _media_id_from_key, _replace_indexes, _thumbnail


def test_media_id_prefers_signed_object_metadata():
    assert _media_id_from_key("originals/path-id/file.jpg", {"media-id": "metadata-id"}) == (
        "metadata-id"
    )
    assert _media_id_from_key("originals/path-id/file.jpg", {}) == "path-id"


def test_worker_thumbnail_preserves_aspect_ratio(tmp_path):
    source = tmp_path / "wide.png"
    destination = tmp_path / "thumb.jpg"
    Image.new("RGBA", (1200, 400), (10, 20, 30, 128)).save(source)

    _thumbnail(source, destination)

    with Image.open(BytesIO(destination.read_bytes())) as image:
        assert image.size == (480, 160)
        assert image.mode == "RGB"


class FakeDynamoDBClient:
    def __init__(self):
        self.requests: list[dict] = []

    def transact_write_items(self, **request) -> None:
        self.requests.append(request)


def test_worker_success_path_writes_tag_and_thumbnail_indexes(monkeypatch):
    client = FakeDynamoDBClient()
    monkeypatch.setenv("TABLE_NAME", "archive")
    monkeypatch.setattr(handler, "dynamodb_client", lambda: client)

    _replace_indexes(
        "media-1",
        {"old_tag": 1},
        {"wombat": 2, "magpie": 1},
        "s3://archive/thumbnails/media-1.jpg",
        "s3://archive/originals/media-1/animal.jpg",
    )

    transaction = client.requests[0]["TransactItems"]
    deleted = [item["Delete"]["Key"] for item in transaction if "Delete" in item]
    puts = [item["Put"]["Item"] for item in transaction if "Put" in item]
    assert deleted[0]["PK"] == {"S": "TAG#old_tag"}
    assert {item["PK"]["S"] for item in puts if item["PK"]["S"].startswith("TAG#")} == {
        "TAG#wombat",
        "TAG#magpie",
    }
    assert any(item["PK"]["S"].startswith("THUMB#") for item in puts)
