from app import cloud


class FakeTable:
    pass


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
