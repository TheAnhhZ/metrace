# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""S3 (SeaweedFS) access. Objects are content-addressed and only ever streamed
through the API (no presigned URLs), so authorization stays in one place."""

from collections.abc import Iterator
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors import InfraError
from app.core.settings import get_settings


@lru_cache
def s3_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
    )


def ensure_bucket() -> None:
    bucket = get_settings().s3_bucket
    try:
        s3_client().head_bucket(Bucket=bucket)
    except ClientError:
        s3_client().create_bucket(Bucket=bucket)


def storage_key_for(sha256: str) -> str:
    return f"{sha256[:2]}/{sha256}"


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    s3_client().put_object(
        Bucket=get_settings().s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        ContentDisposition="attachment",
    )


class ObjectMissingError(Exception):
    """Metadata says the file exists but the bytes are gone."""


def open_stream(key: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    """Fetch EAGERLY (errors surface before any response header is sent), then stream."""
    try:
        body = s3_client().get_object(Bucket=get_settings().s3_bucket, Key=key)["Body"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
            raise ObjectMissingError(key) from exc
        raise InfraError(f"object storage: {exc}") from exc
    except BotoCoreError as exc:
        raise InfraError(f"object storage: {exc}") from exc

    def chunks() -> Iterator[bytes]:
        try:
            yield from body.iter_chunks(chunk_size)
        finally:
            body.close()

    return chunks()
