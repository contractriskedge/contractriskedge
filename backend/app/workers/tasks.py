from celery import shared_task


@shared_task(name="ingest_document")
def ingest_document(upload_id: str, tenant_id: str):
    print(
        f"[CELERY] ingest_document called "
        f"upload_id={upload_id} tenant_id={tenant_id}"
    )

    # TODO:
    # OCR
    # chunking
    # embeddings
    # indexing