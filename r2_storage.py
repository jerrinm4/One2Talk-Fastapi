"""
Cloudflare R2 Storage Service

Provides S3-compatible file upload functionality for Cloudflare R2.
Uses boto3 with custom endpoint configuration for R2.
"""

import boto3
from botocore.exceptions import ClientError
import config


def get_r2_client():
    """Create and return a boto3 S3 client configured for Cloudflare R2."""
    if not config.R2_ENABLED:
        return None
    
    return boto3.client(
        's3',
        endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )


def upload_to_r2(file_content: bytes, filename: str, content_type: str = "image/jpeg") -> str | None:
    """
    Upload a file to Cloudflare R2.
    
    Args:
        file_content: The file bytes to upload
        filename: The destination filename in R2
        content_type: MIME type of the file
        
    Returns:
        The public URL of the uploaded file, or None if upload fails
    """
    if not config.R2_ENABLED:
        return None
    
    client = get_r2_client()
    if not client:
        return None
    
    try:
        client.put_object(
            Bucket=config.R2_BUCKET_NAME,
            Key=filename,
            Body=file_content,
            ContentType=content_type
        )
        
        # Return the public URL
        public_url = config.R2_PUBLIC_URL.rstrip('/')
        return f"{public_url}/{filename}"
        
    except ClientError as e:
        print(f"R2 upload error: {e}")
        return None


def file_exists_in_r2(filename: str) -> bool:
    """
    Check if a file already exists in R2 bucket.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if file exists, False otherwise
    """
    if not config.R2_ENABLED:
        return False
    
    client = get_r2_client()
    if not client:
        return False
    
    try:
        client.head_object(Bucket=config.R2_BUCKET_NAME, Key=filename)
        return True
    except ClientError:
        return False
