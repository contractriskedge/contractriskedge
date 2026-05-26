from io import BytesIO

import boto3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from celery import shared_task

from app.config import settings
from app.domains.ingestion.models import UploadSession


DATABASE_URL = settings.database_url.replace("+asyncpg", "")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name="us-east-1",
)


@shared_task(name="ingest_document")
def ingest_document(upload_id: str, tenant_id: str):
    print("=" * 80)
    print("INGEST DOCUMENT TASK STARTED")
    print("=" * 80)

    print(f"UPLOAD ID: {upload_id}")
    print(f"TENANT ID: {tenant_id}")

    print("STEP 1 — loading upload session")

    db = SessionLocal()

    try:
        stmt = select(UploadSession).where(
            UploadSession.upload_id == upload_id,
            UploadSession.tenant_id == tenant_id,
        )

        upload = db.execute(stmt).scalar_one_or_none()

        if not upload:
            print("UPLOAD SESSION NOT FOUND")
            return

        print("UPLOAD SESSION LOADED")
        print(f"FILENAME: {upload.filename}")
        print(f"CONTENT TYPE: {upload.content_type}")
        print(f"STORAGE BUCKET: {upload.storage_bucket}")
        print(f"STORAGE KEY: {upload.storage_key}")

        print("STEP 2 — downloading document from MinIO")

        response = s3_client.get_object(
            Bucket=upload.storage_bucket,
            Key=upload.storage_key,
        )

        file_bytes = response["Body"].read()

        print("MINIO DOWNLOAD COMPLETE")
        print(f"DOWNLOADED BYTES: {len(file_bytes)}")

        pdf_stream = BytesIO(file_bytes)

        print("STEP 3 — extracting document text")

        # TODO: Persist document pages
        print("STEP 4 — saving document pages")

        # TODO: Generate semantic chunks
        print("STEP 5 — generating semantic chunks")

        # TODO: Generate embeddings
        print("STEP 6 — generating embeddings")

        # TODO: Update ingestion status
        print("STEP 7 — marking ingestion complete")

    finally:
        db.close()

    print("=" * 80)
    print("INGEST DOCUMENT TASK COMPLETED")
    print("=" * 80)