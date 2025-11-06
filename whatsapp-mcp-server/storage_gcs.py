"""Google Cloud Storage utilities for WhatsApp session persistence."""

import logging
import os
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def is_gcs_configured() -> bool:
    """Check if GCS is configured via environment variables.

    Returns:
        bool: True if GCS_SESSION_BUCKET is set, False otherwise.
    """
    bucket_name = os.getenv("GCS_SESSION_BUCKET", "").strip()
    return bool(bucket_name)


def upload_session_to_gcs(
    bucket_name: str,
    local_file_path: str,
    object_name: str = "whatsapp.db"
) -> Tuple[bool, str]:
    """Upload session database file to Google Cloud Storage.

    Args:
        bucket_name: GCS bucket name
        local_file_path: Path to local file to upload
        object_name: Destination object name in bucket (default: whatsapp.db)

    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        from google.cloud import storage

        # Check if local file exists
        if not os.path.exists(local_file_path):
            msg = f"Local file does not exist: {local_file_path}"
            logger.warning(msg)
            return False, msg

        # Create GCS client using Application Default Credentials
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Upload file
        blob.upload_from_filename(local_file_path)

        msg = f"Successfully uploaded {local_file_path} to gs://{bucket_name}/{object_name}"
        logger.info(msg)
        return True, msg

    except Exception as e:
        msg = f"Failed to upload session to GCS: {str(e)}"
        logger.error(msg)
        return False, msg


def download_session_from_gcs(
    bucket_name: str,
    object_name: str,
    local_file_path: str
) -> Tuple[bool, str]:
    """Download session database file from Google Cloud Storage.

    Args:
        bucket_name: GCS bucket name
        object_name: Source object name in bucket
        local_file_path: Destination path for downloaded file

    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        from google.cloud import storage

        # Create GCS client using Application Default Credentials
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Check if blob exists
        if not blob.exists():
            msg = f"Object does not exist in GCS: gs://{bucket_name}/{object_name}"
            logger.info(msg)
            return False, msg

        # Create local directory if needed
        local_dir = os.path.dirname(local_file_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        # Download file
        blob.download_to_filename(local_file_path)

        msg = f"Successfully downloaded gs://{bucket_name}/{object_name} to {local_file_path}"
        logger.info(msg)
        return True, msg

    except Exception as e:
        msg = f"Failed to download session from GCS: {str(e)}"
        logger.error(msg)
        return False, msg
