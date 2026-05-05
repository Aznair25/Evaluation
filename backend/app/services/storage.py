import boto3
from botocore.exceptions import ClientError
from app.config import get_settings

settings = get_settings()


class StorageService:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_s3_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.bucket = settings.aws_s3_bucket

    def upload_bytes(self, data: bytes, key: str, content_type: str = "application/octet-stream"):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def upload_file(self, file_path: str, key: str, content_type: str = "application/octet-stream"):
        self.client.upload_file(
            file_path,
            self.bucket,
            key,
            ExtraArgs={
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            },
        )

    def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def download_file(self, key: str, dest_path: str):
        self.client.download_file(self.bucket, key, dest_path)

    def delete_object(self, key: str):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError:
            pass

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiration,
        )
