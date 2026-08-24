from io import BytesIO

from PIL import Image

from services.worker.handler import _media_id_from_key, _thumbnail


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
