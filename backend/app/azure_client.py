"""Azure Blob Storage access. Connection-string auth for the MVP."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)

from .config import settings

_service: BlobServiceClient | None = None


def service() -> BlobServiceClient:
    global _service
    if _service is None:
        if not settings.AZURE_CONNECTION_STRING:
            raise RuntimeError(
                "AZURE_STORAGE_CONNECTION_STRING is not set. "
                "Copy .env.example to .env and fill it in."
            )
        _service = BlobServiceClient.from_connection_string(
            settings.AZURE_CONNECTION_STRING
        )
    return _service


def target_containers() -> list[str]:
    """Configured containers, or every container in the account."""
    if settings.CONTAINERS:
        return settings.CONTAINERS
    return [c.name for c in service().list_containers()]


def download_bytes(container: str, blob_name: str, max_bytes: int) -> bytes | None:
    """Download a blob, or None when it exceeds the size ceiling."""
    bc = service().get_blob_client(container, blob_name)
    props = bc.get_blob_properties()
    if props.size > max_bytes:
        return None
    return bc.download_blob().readall()


def sas_url(container: str, blob_name: str) -> str:
    """Short-lived read-only link, generated on demand (never pre-generated)."""
    svc = service()
    sas = generate_blob_sas(
        account_name=svc.account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=svc.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc)
        + timedelta(minutes=settings.SAS_EXPIRY_MINUTES),
    )
    return f"{svc.url}{container}/{blob_name}?{sas}"
