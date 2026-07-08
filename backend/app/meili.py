"""Meilisearch client + index bootstrap."""
from __future__ import annotations

import meilisearch

from .config import settings

_client: meilisearch.Client | None = None


def client() -> meilisearch.Client:
    global _client
    if _client is None:
        _client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)
    return _client


def index():
    return client().index(settings.INDEX_NAME)


def ensure_index() -> None:
    """Create the index (if missing) and apply settings. Idempotent."""
    c = client()
    task = c.create_index(settings.INDEX_NAME, {"primaryKey": "id"})
    c.wait_for_task(task.task_uid)
    task = index().update_settings({
        "searchableAttributes": ["name", "path", "text"],
        "filterableAttributes": ["container", "extension", "size", "last_modified"],
        "sortableAttributes": ["last_modified", "size", "name"],
        "displayedAttributes": [
            "id", "name", "path", "container", "extension",
            "size", "last_modified", "content_type", "text",
        ],
        "pagination": {"maxTotalHits": 10000},
    })
    c.wait_for_task(task.task_uid)
