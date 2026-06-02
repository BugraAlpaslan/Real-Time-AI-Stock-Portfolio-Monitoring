"""Unit tests for S3Service — boto3 calls are patched with MagicMock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.services.s3_service import S3Service, get_s3_service


# ────────────────────────────── helpers ──────────────────────────────


def _make_service(endpoint: str | None = "http://localhost:4566") -> tuple[S3Service, MagicMock]:
    """Return (S3Service, mock_boto3_client)."""
    with patch("app.services.s3_service.boto3.client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        svc = S3Service(
            endpoint_url=endpoint,
            bucket="test-bucket",
            access_key="test",
            secret_key="test",
            region="us-east-1",
        )
    return svc, mock_client


# ────────────────────────────── put_object ──────────────────────────────


def test_put_object_str_body_encodes_and_calls_boto3():
    svc, mock_client = _make_service()
    mock_client.head_bucket.return_value = {}

    uri = svc.put_object("exports/test.json", '{"hello": "world"}')

    assert uri == "s3://test-bucket/exports/test.json"
    mock_client.put_object.assert_called_once()
    call_kwargs = mock_client.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == "exports/test.json"
    assert call_kwargs["Body"] == b'{"hello": "world"}'
    assert call_kwargs["ContentType"] == "application/json"


def test_put_object_bytes_body():
    svc, mock_client = _make_service()
    mock_client.head_bucket.return_value = {}

    data = b"\x00\x01\x02"
    svc.put_object("raw/data.bin", data, content_type="application/octet-stream")

    call_kwargs = mock_client.put_object.call_args.kwargs
    assert call_kwargs["Body"] == data
    assert call_kwargs["ContentType"] == "application/octet-stream"


def test_put_object_creates_bucket_when_missing():
    svc, mock_client = _make_service()
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    svc.put_object("key.json", "{}")

    mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.put_object.assert_called_once()


def test_put_object_no_bucket_create_when_no_localstack_endpoint():
    """When endpoint_url is None (real AWS), _ensure_bucket does nothing."""
    svc, mock_client = _make_service(endpoint=None)

    svc.put_object("key.json", "{}")

    mock_client.head_bucket.assert_not_called()
    mock_client.create_bucket.assert_not_called()
    mock_client.put_object.assert_called_once()


# ────────────────────────────── get_object ──────────────────────────────


def test_get_object_returns_bytes():
    svc, mock_client = _make_service()
    mock_client.get_object.return_value = {"Body": MagicMock(read=lambda: b"content")}

    result = svc.get_object("some/key.json")

    assert result == b"content"
    mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="some/key.json")


def test_get_object_raises_file_not_found_on_no_such_key():
    svc, mock_client = _make_service()
    error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}
    mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

    with pytest.raises(FileNotFoundError, match="missing.json"):
        svc.get_object("missing.json")


def test_get_object_re_raises_other_client_errors():
    svc, mock_client = _make_service()
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}
    mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

    with pytest.raises(ClientError):
        svc.get_object("secret.json")


# ────────────────────────────── list_objects ──────────────────────────────


def test_list_objects_returns_keys():
    svc, mock_client = _make_service()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "prefix/a.json"}, {"Key": "prefix/b.json"}]},
        {"Contents": [{"Key": "prefix/c.json"}]},
    ]
    mock_client.get_paginator.return_value = mock_paginator

    keys = svc.list_objects("prefix/")

    assert keys == ["prefix/a.json", "prefix/b.json", "prefix/c.json"]


def test_list_objects_empty_prefix_returns_empty():
    svc, mock_client = _make_service()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"Contents": []}]
    mock_client.get_paginator.return_value = mock_paginator

    keys = svc.list_objects("nothing/")

    assert keys == []


def test_list_objects_page_without_contents_key():
    svc, mock_client = _make_service()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{}]  # no 'Contents' key
    mock_client.get_paginator.return_value = mock_paginator

    keys = svc.list_objects("prefix/")

    assert keys == []


# ────────────────────────────── ensure_bucket edge case ──────────────────────────────


def test_ensure_bucket_reraises_unexpected_client_error():
    svc, mock_client = _make_service()
    error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Outage"}}
    mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    with pytest.raises(ClientError):
        svc.put_object("key.json", "{}")


# ────────────────────────────── get_s3_service factory ──────────────────────────────


def test_get_s3_service_returns_singleton():
    get_s3_service.cache_clear()
    with patch("app.services.s3_service.boto3.client"):
        svc1 = get_s3_service()
        svc2 = get_s3_service()
    assert svc1 is svc2
    get_s3_service.cache_clear()
