"""Fetch document bytes from S3, GCS, or HTTP/HTTPS."""

import asyncio
import logging
import re
from urllib.parse import urlparse, unquote

from engine.pipelines.ingestion.exceptions import CloudStorageError  # noqa: I001

logger = logging.getLogger(__name__)


def _get_query_param(uri: str, key: str) -> str | None:
    """Best-effort query parameter extraction (no secret logging)."""
    try:
        parsed = urlparse(uri)
        qs = parsed.query or ""
        for part in qs.split("&"):
            if not part:
                continue
            k, _, v = part.partition("=")
            if k == key:
                return v
        return None
    except Exception:
        return None


def _parse_s3_https_url(uri: str) -> tuple[str, str, str | None] | None:
    """
    Parse an S3 virtual-hosted-style HTTPS URL into (bucket, key, region).

    Example:
      https://dev-enterprisegpt.s3.ap-south-1.amazonaws.com/temp/abc.pdf
    """
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower()

    # 1) Virtual-hosted style: <bucket>.s3.<region>.amazonaws.com/<key>
    m = re.match(r"^(?P<bucket>.+)\.s3\.(?P<region>[^.]+)\.amazonaws\.com$", host)
    if not m:
        # 2) Path-style: s3.<region>.amazonaws.com/<bucket>/<key>
        m2 = re.match(r"^s3\.(?P<region>[^.]+)\.amazonaws\.com$", host)
        if not m2:
            return None

        region = m2.group("region")
        parts = (parsed.path or "").lstrip("/").split("/", 1)
        if len(parts) != 2:
            return None
        bucket, key = unquote(parts[0]), unquote(parts[1])
        if not bucket or not key:
            return None
        return bucket, key, region

    bucket = unquote(m.group("bucket"))
    region = m.group("region")
    key = unquote((parsed.path or "").lstrip("/"))
    if not bucket or not key:
        return None

    return bucket, key, region


def _fetch_s3_https_via_boto3(uri: str) -> bytes:
    parsed = urlparse(uri)
    parts = _parse_s3_https_url(uri)
    if not parts:
        raise CloudStorageError(f"Not an S3 HTTPS URL: {uri}")
    bucket, key, region = parts

    import boto3

    client = boto3.client("s3", region_name=region) if region else boto3.client("s3")
    logger.info("boto3 get_object: bucket=%s region=%s key=%s", bucket, region, key)
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except Exception as e:
        logger.error("boto3 get_object failed: %s", e)
        raise


def _fetch_s3_sync(uri: str) -> bytes:
    path = uri.replace("s3://", "", 1)
    if "/" not in path:
        raise CloudStorageError(f"Invalid S3 URI (no key): {uri}")
    bucket, key = path.split("/", 1)
    import boto3
    client = boto3.client("s3")
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _fetch_gcs_sync(uri: str) -> bytes:
    path = uri.replace("gs://", "", 1)
    if "/" not in path:
        raise CloudStorageError(f"Invalid GCS URI (no path): {uri}")
    bucket_name, blob_path = path.split("/", 1)
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()


def _fetch_file_sync(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def _fetch_http_sync(uri: str) -> bytes:
    """
    Fetch bytes over HTTP/HTTPS.

    Uses httpx when available (bundles its own certifi CA store, works on
    macOS Python 3.x where urllib raises CERTIFICATE_VERIFY_FAILED).
    Falls back to urllib + certifi / system cert store.
    """
    try:
        import httpx
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(uri, headers={"User-Agent": "ai-platform-ingestion/1.0"})
            resp.raise_for_status()
            return resp.content
    except ImportError:
        pass

    import os
    import ssl
    import urllib.request

    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        macos_ca = "/etc/ssl/cert.pem"
        ctx = (
            ssl.create_default_context(cafile=macos_ca)
            if os.path.exists(macos_ca)
            else ssl.create_default_context()
        )

    req = urllib.request.Request(uri, headers={"User-Agent": "ai-platform-ingestion/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        return resp.read()


async def fetch_bytes_from_uri(uri: str) -> bytes:
    """
    Fetch raw bytes from uri (s3://, gs://, http://, https://, file://).

    Raises:
        CloudStorageError: On fetch failure.
        ValueError: Unsupported scheme.
    """
    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()

    try:
        if scheme == "file":
            path = unquote(parsed.path)
            import os
            if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
            return await asyncio.to_thread(_fetch_file_sync, path)
        if scheme == "s3":
            return await asyncio.to_thread(_fetch_s3_sync, uri)
        if scheme == "gs":
            return await asyncio.to_thread(_fetch_gcs_sync, uri)
        if scheme in ("http", "https"):
            # If this is an S3 HTTPS URL (even if the presign is PutObject),
            # prefer boto3 with our AWS credentials. This avoids failures
            # like 403 Forbidden when the portal sends a non-download presigned URL.
            if scheme == "https" and (parsed.hostname or "").lower().endswith(".amazonaws.com"):
                x_id = _get_query_param(uri, "x-id")
                print(f"[ingestion-fetch] detected S3 https host={(parsed.hostname or '').lower()} x-id={x_id}")
                # Only force boto3 when we suspect the presigned URL is for upload/put.
                # For GET presigns, HTTP GET is usually the simplest path.
                if x_id and x_id.lower() == "putobject":
                    parts = _parse_s3_https_url(uri)
                    if parts:
                        print("[ingestion-fetch] x-id=PutObject -> boto3 fallback enabled")
                        bucket, key, region = parts
                        print(f"[ingestion-fetch] boto3 bucket={bucket} region={region} key={key}")
                        logger.info(
                            "forcing boto3 fetch because x-id=PutObject bucket=%s region=%s key=%s",
                            bucket,
                            region,
                            key,
                        )
                        return await asyncio.to_thread(_fetch_s3_https_via_boto3, uri)
                else:
                    parts = _parse_s3_https_url(uri)
                    if parts:
                        bucket, key, region = parts
                        logger.info(
                            "S3 https parsed for logging (x-id=%s bucket=%s region=%s key=%s) -> using HTTP fetch",
                            x_id,
                            bucket,
                            region,
                            key,
                        )
            return await asyncio.to_thread(_fetch_http_sync, uri)
    except ImportError as e:
        raise CloudStorageError(f"Missing dependency for {scheme}: {e}") from e
    except Exception as e:
        if isinstance(e, CloudStorageError):
            raise
        logger.exception("Fetch failed for %s", uri)
        raise CloudStorageError(f"Fetch failed: {e}") from e

    raise ValueError(f"Unsupported URI scheme: {scheme}")