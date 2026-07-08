"""Central configuration, read once from environment."""
import os


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    # Azure
    AZURE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    # Comma-separated container names. Empty = crawl every container in the account.
    CONTAINERS: list[str] = _csv(os.getenv("BLOB_CONTAINERS", ""))

    # Meilisearch
    MEILI_URL: str = os.getenv("MEILI_URL", "http://meilisearch:7700")
    MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "bloblens-dev-key")
    INDEX_NAME: str = os.getenv("INDEX_NAME", "blobs")

    # Indexer behaviour
    SYNC_INTERVAL_SECONDS: int = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))
    MAX_TEXT_CHARS: int = int(os.getenv("MAX_TEXT_CHARS", "50000"))
    MAX_BLOB_MB: int = int(os.getenv("MAX_BLOB_MB", "50"))
    STATE_FILE: str = os.getenv("STATE_FILE", "/data/state.json")

    # Download links
    SAS_EXPIRY_MINUTES: int = int(os.getenv("SAS_EXPIRY_MINUTES", "60"))


settings = Settings()
