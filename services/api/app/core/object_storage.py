# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""S3 (SeaweedFS) access. Objects are content-addressed and only ever streamed
through the API (no presigned URLs), so authorization stays in one place."""

from collections.abc import Iterator
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

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


def stream_bytes(key: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    body = s3_client().get_object(Bucket=get_settings().s3_bucket, Key=key)["Body"]
    try:
        yield from body.iter_chunks(chunk_size)
    finally:
        body.close()
