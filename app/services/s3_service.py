from __future__ import annotations

import os
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError


class S3Service:
    def __init__(
        self,
        endpoint_url: str | None,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> None:
        self.bucket = bucket
        client_kwargs: dict[str, str] = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        self.client = boto3.client("s3", **client_kwargs)

    def put_object(
        self,
        key: str,
        body: bytes | str,
        content_type: str = "application/json",
    ) -> str:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
        return f"s3://{self.bucket}/{key}"

    def get_object(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(key) from exc
            raise
        return response["Body"].read()

    def list_objects(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                keys.append(item["Key"])
        return keys


def _settings_value(name: str, default: str | None = None) -> str | None:
    try:
        from app.config import get_settings

        settings = get_settings()
        return getattr(settings, name, None) or default
    except Exception:
        return os.environ.get(name.upper(), default)


@lru_cache
def get_s3_service() -> S3Service:
    endpoint = _settings_value("aws_endpoint_url") or os.environ.get("AWS_ENDPOINT_URL")
    bucket = _settings_value("s3_bucket") or os.environ.get("S3_BUCKET", "portfolio-exports")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return S3Service(
        endpoint_url=endpoint,
        bucket=bucket or "portfolio-exports",
        access_key=access_key,
        secret_key=secret_key,
        region=region,
    )
