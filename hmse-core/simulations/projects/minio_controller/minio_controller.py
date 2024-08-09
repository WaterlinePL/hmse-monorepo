import io
import json
import logging
import os
from enum import auto
from pathlib import Path
from typing import Dict

from minio import Minio
from strenum import StrEnum

from simulations.projects.minio_controller.typing_help import FilePathInBucket, PrefixEndedWithSlash

# Needed environment variables:
# MINIO_ACCESS_KEY
# MINIO_SECRET_KEY
# MINIO_ENDPOINT
# MINIO_REGION
# HMSE_MINIO_ROOT_BUCKET
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_REGION = os.environ.get("MINIO_REGION")
ROOT_BUCKET = os.environ.get("HMSE_MINIO_ROOT_BUCKET")

__INSTANCE = None
logger = logging.getLogger(__name__)


class S3StorageType(StrEnum):
    AWS_S3 = auto()
    MINIO = auto()


class MinIOController:
    def __init__(self, s3_type: str):
        logger.debug(f"Initializing MinIO controller for following s3 clinet: {s3_type}")
        endpoint = MINIO_ENDPOINT if MINIO_ENDPOINT else "s3.amazon.com/endpoint"
        self.s3_type = s3_type
        self.minio_client = Minio(
            endpoint=endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            region=MINIO_REGION
        )

    def list_bucket_content(self, name_prefix: PrefixEndedWithSlash, recursive: bool = False):
        logger.debug(f"Retrieving list of object in bucket {ROOT_BUCKET} with prefix: {name_prefix} "
                     f"(recursive: {recursive})")
        return list(self.minio_client.list_objects(ROOT_BUCKET, name_prefix, recursive=recursive))

    def get_json_content(self, file_name: FilePathInBucket):
        logger.debug(f"Getting JSON file from bucket {ROOT_BUCKET}: {file_name}")
        response = self.minio_client.get_object(ROOT_BUCKET, file_name,
                                                request_headers={"Content-Type": "application/json"})
        return json.loads(response.data.decode('utf-8'))

    def get_file(self, file_name: FilePathInBucket, output_location: os.PathLike):
        logger.debug(f"Getting object from bucket {ROOT_BUCKET}: {file_name} (saved as {output_location})")
        return self.minio_client.fget_object(ROOT_BUCKET, file_name, output_location)

    def get_file_bytes(self, file_name: FilePathInBucket):
        logger.debug(f"Getting object from bucket {ROOT_BUCKET}: {file_name} (raw bytes)")
        return self.minio_client.get_object(ROOT_BUCKET, file_name)

    def put_file(self, input_file: os.PathLike, bucket_location: FilePathInBucket):
        logger.debug(f"Putting object {input_file} to bucket {ROOT_BUCKET} under path: {bucket_location}")
        return self.minio_client.fput_object(ROOT_BUCKET, bucket_location, input_file)

    def put_json_file(self, json_data: Dict, object_location: FilePathInBucket):
        logger.debug(f"Putting JSON object to bucket {ROOT_BUCKET} under path: {object_location}")
        serialized = json.dumps(json_data, indent=2, default=lambda o: o.__dict__).encode('utf-8')
        return self.minio_client.put_object(ROOT_BUCKET, object_location, io.BytesIO(serialized), len(serialized),
                                            content_type="application/json")

    def delete_file(self, object_location: FilePathInBucket):
        logger.debug(f"Deleting object in bucket {ROOT_BUCKET} under path: {object_location}")
        return self.minio_client.remove_object(ROOT_BUCKET, object_location)

    def delete_directory(self, dir_location: PrefixEndedWithSlash):
        logger.debug(f"Deleting all objects recursively in bucket {ROOT_BUCKET} with prefix: {dir_location}")
        files_to_delete = [obj.object_name for obj in self.list_bucket_content(dir_location, recursive=True)]
        for file in files_to_delete:
            self.delete_file(file)

    def upload_directory_to_bucket(self, directory: os.PathLike, bucket_location_root: FilePathInBucket):
        logger.debug(f"Uploading all objects in directory {directory} recursively to bucket {ROOT_BUCKET} "
                     f"under prefix: {bucket_location_root}")
        files_to_upload = [str(file) for file in Path(directory).rglob("*")
                           if file.is_file()]
        for file in files_to_upload:
            bucket_file = file.replace("\\", "/")
            location_in_bucket = bucket_file.replace(f"{directory}/", '')
            self.put_file(file, f"{bucket_location_root}/{location_in_bucket}")

    def get_root(self) -> str:
        return ROOT_BUCKET

    def get_s3_prefix(self) -> str:
        return {
            S3StorageType.AWS_S3: "s3://",
            S3StorageType.MINIO: "minio/"
        }[self.s3_type]


def get() -> MinIOController:
    global __INSTANCE
    __INSTANCE = __INSTANCE or MinIOController(os.environ.get("S3_TYPE", "MINIO"))
    return __INSTANCE
