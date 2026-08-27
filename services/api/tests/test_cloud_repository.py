from app import cloud


class FakeTable:
    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}
        self.updates: list[dict] = []
        self.query_results: list[list[dict]] = []

    def get_item(self, Key, **_kwargs):  # noqa: N803 - mirrors boto3
        return {"Item": self.items.get((Key["PK"], Key["SK"]))}

    def update_item(self, **kwargs) -> None:
        self.updates.append(kwargs)

    def put_item(self, Item) -> None:  # noqa: N803 - mirrors boto3
        self.items[(Item["PK"], Item["SK"])] = Item

    def delete_item(self, Key) -> None:  # noqa: N803 - mirrors boto3
        self.items.pop((Key["PK"], Key["SK"]), None)

    def query(self, **_kwargs):
        return {"Items": self.query_results.pop(0)}


class FakeResource:
    def __init__(self):
        self.table = FakeTable()

    def Table(self, _name: str) -> FakeTable:  # noqa: N802 - mirrors boto3
        return self.table


class FakeClient:
    def __init__(self):
        self.requests: list[dict] = []

    def transact_write_items(self, **request) -> None:
        self.requests.append(request)


def test_reserve_media_uses_low_level_dynamodb_attribute_values(monkeypatch):
    resource = FakeResource()
    client = FakeClient()
    monkeypatch.setattr(cloud.boto3, "resource", lambda *_args, **_kwargs: resource)
    monkeypatch.setattr(cloud.boto3, "client", lambda *_args, **_kwargs: client)

    repository = cloud.DynamoDBRepository("archive", "us-east-1")
    repository.reserve_media(
        {
            "media_id": "media-1",
            "owner": "researcher-1",
            "filename": "animal.jpg",
            "content_type": "image/jpeg",
            "size": 100,
            "checksum": "f" * 64,
            "object_path": "s3://archive/originals/media-1/animal.jpg",
        }
    )

    transaction = client.requests[0]["TransactItems"]
    lock_item = transaction[0]["Put"]["Item"]
    media_item = transaction[1]["Put"]["Item"]
    assert lock_item["PK"] == {"S": f"CHECKSUM#{'f' * 64}"}
    assert lock_item["SK"] == {"S": "LOCK"}
    assert media_item["PK"] == {"S": "MEDIA#media-1"}
    assert media_item["size"] == {"N": "100"}


def media_item(media_id: str, tags: dict[str, int] | None = None) -> dict:
    return {
        "PK": f"MEDIA#{media_id}",
        "SK": "META",
        "mediaId": media_id,
        "owner": "researcher-1",
        "filename": "animal.jpg",
        "contentType": "image/jpeg",
        "size": 100,
        "checksum": "f" * 64,
        "objectUri": f"s3://archive/originals/{media_id}/animal.jpg",
        "thumbnailUri": f"s3://archive/thumbnails/{media_id}.jpg",
        "tags": tags or {},
        "status": "READY",
        "modelVersion": "model-v1",
        "createdAt": "2026-08-27T00:00:00+00:00",
    }


def repository_with_fakes(monkeypatch):
    resource = FakeResource()
    client = FakeClient()
    monkeypatch.setattr(cloud.boto3, "resource", lambda *_args, **_kwargs: resource)
    monkeypatch.setattr(cloud.boto3, "client", lambda *_args, **_kwargs: client)
    return cloud.DynamoDBRepository("archive", "us-east-1"), resource.table, client


def test_update_media_maintains_tag_and_thumbnail_indexes(monkeypatch):
    repository, table, client = repository_with_fakes(monkeypatch)
    table.items[("MEDIA#media-1", "META")] = media_item("media-1", {"old_tag": 1})

    repository.update_media(
        "media-1",
        tags={"wombat": 2, "magpie": 1},
        thumbnail_path="s3://archive/thumbnails/media-1-new.jpg",
    )

    transaction = client.requests[0]["TransactItems"]
    deleted_old_tag = transaction[0]["Delete"]["Key"]
    put_items = [item["Put"]["Item"] for item in transaction if "Put" in item]
    new_tag_items = [item for item in put_items if item["PK"]["S"].startswith("TAG#")]
    thumb_item = next(item for item in put_items if item["PK"]["S"].startswith("THUMB#"))
    assert deleted_old_tag["PK"] == {"S": "TAG#old_tag"}
    assert {item["PK"]["S"] for item in new_tag_items} == {"TAG#wombat", "TAG#magpie"}
    assert {item["SK"]["S"] for item in new_tag_items} == {
        "COUNT#0000000002#MEDIA#media-1",
        "COUNT#0000000001#MEDIA#media-1",
    }
    assert thumb_item["PK"]["S"].startswith("THUMB#")
    assert thumb_item["mediaId"] == {"S": "media-1"}


def test_find_by_tags_intersects_tag_partitions(monkeypatch):
    repository, table, _client = repository_with_fakes(monkeypatch)
    table.query_results = [
        [
            {"PK": "TAG#wombat", "SK": "COUNT#0000000002#MEDIA#media-1", "mediaId": "media-1"},
            {"PK": "TAG#wombat", "SK": "COUNT#0000000003#MEDIA#media-2", "mediaId": "media-2"},
        ],
        [{"PK": "TAG#magpie", "SK": "COUNT#0000000001#MEDIA#media-2", "mediaId": "media-2"}],
    ]
    table.items[("MEDIA#media-1", "META")] = media_item("media-1", {"wombat": 2})
    table.items[("MEDIA#media-2", "META")] = media_item(
        "media-2", {"wombat": 3, "magpie": 1}
    )

    matches = repository.find_by_tags({"wombat": 2, "magpie": 1})

    assert [item["media_id"] for item in matches] == ["media-2"]


def test_delete_media_removes_metadata_checksum_tag_and_thumbnail_rows(monkeypatch):
    repository, table, client = repository_with_fakes(monkeypatch)
    table.items[("MEDIA#media-1", "META")] = media_item(
        "media-1", {"wombat": 2, "magpie": 1}
    )

    repository.delete_media("media-1")

    deleted_keys = [item["Delete"]["Key"] for item in client.requests[0]["TransactItems"]]
    assert {"S": "MEDIA#media-1"} in [key["PK"] for key in deleted_keys]
    assert {"S": "CHECKSUM#ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"} in [
        key["PK"] for key in deleted_keys
    ]
    assert {"S": "TAG#wombat"} in [key["PK"] for key in deleted_keys]
    assert {"S": "TAG#magpie"} in [key["PK"] for key in deleted_keys]
    assert any(key["PK"]["S"].startswith("THUMB#") for key in deleted_keys)
