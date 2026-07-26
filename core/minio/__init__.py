import io
from miniopy_async.api import Minio as MinioAsync
from config import settings
from core.exception import InternalServerError


async def get_minio_client():
    client = MinioAsync(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=True,
    )
    return client


async def get_minio_object(
    bucket_name: str, object_name: str
) -> io.BytesIO:
    client = await get_minio_client()
    try:
        response = await client.get_object(bucket_name, object_name)
        data = await response.read()
        return io.BytesIO(data)
    except Exception as e:
        print(f"Error fetching object from MinIO: {e}")
        raise InternalServerError(
            exception_type="minio.object_fetch_error",
            msg=f"Error fetching object from MinIO: {e}",
        )


async def get_minio_object_by_url(url: str) -> io.BytesIO:
    """Fetch object from MinIO using a full URL like s3://bucket/key or http://endpoint/bucket/key"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    # Handle s3:// URLs
    if parsed.scheme == 's3':
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        return await get_minio_object(bucket, key)
    
    # Handle http:// URLs
    if parsed.scheme in ('http', 'https'):
        # Assume format: http://endpoint/bucket/key
        path_parts = parsed.path.strip('/').split('/', 1)
        if len(path_parts) == 2:
            bucket = path_parts[0]
            key = path_parts[1]
            return await get_minio_object(bucket, key)
    
    # Fallback: assume it's just the object name in default bucket
    raise ValueError(f"Unsupported URL format: {url}")


async def put_minio_object(
    bucket_name: str, object_name: str, data: io.BytesIO
):
    client = await get_minio_client()
    try:
        await client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=data,
            length=len(data.getvalue()),
        )
    except Exception as e:
        print(f"Error uploading object to MinIO: {e}")
        raise InternalServerError(
            exception_type="minio.object_upload_error",
            msg=f"Error uploading object to MinIO: {e}",
        )
