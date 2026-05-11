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
    minio_client: MinioAsync, bucket_name: str, object_name: str
) -> io.BytesIO:
    client = minio_client
    try:
        response = await client.get_object(bucket_name, object_name)
        response = io.BytesIO(await response.read())
        return response
    except Exception as e:
        print(f"Error fetching object from MinIO: {e}")
        raise InternalServerError(
            exception_type="minio.object_fetch_error",
            msg=f"Error fetching object from MinIO: {e}",
        )


async def put_minio_object(
    miniio_client: MinioAsync, bucket_name: str, object_name: str, data: io.BytesIO
):
    client = miniio_client
    try:
        await client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=data,
            length=len(data.getvalue()),
        )
    except Exception as e:
        print(f"Error fetching object from MinIO: {e}")
        raise InternalServerError(
            exception_type="minio.object_fetch_error",
            msg=f"Error fetching object from MinIO: {e}",
        )
