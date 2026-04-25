import logging
import uuid

import boto3
from botocore.config import Config as BotoConfig

from app.config import (
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    R2_SECRET_ACCESS_KEY,
)

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    "png": "image/png",
    "pdf": "application/pdf",
}


def _get_client():
    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def upload_certificate(file_path: str, fmt: str) -> str:
    key = f"certificate-downloads/{uuid.uuid4()}.{fmt}"
    content_type = CONTENT_TYPES.get(fmt, "application/octet-stream")

    client = _get_client()
    client.upload_file(
        file_path,
        R2_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type},
    )

    url = f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
    logger.info(f"Uploaded certificate to R2: {url}")
    return url
