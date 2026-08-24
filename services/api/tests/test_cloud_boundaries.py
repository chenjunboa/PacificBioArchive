from app.cloud import S3Storage


def test_cloud_storage_uses_stable_s3_uris_and_safe_keys():
    storage = object.__new__(S3Storage)
    storage.bucket = "archive-bucket"
    key = storage.media_key("media-id", "../Camera trap 01.JPG")

    assert key == "originals/media-id/Camera_trap_01.JPG"
    assert storage.uri(key) == "s3://archive-bucket/originals/media-id/Camera_trap_01.JPG"
    assert storage._split_uri(storage.uri(key)) == ("archive-bucket", key)
