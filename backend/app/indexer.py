"""Crawl containers and push documents into Meilisearch.

Sync strategy (v1): per-container Last-Modified watermark. Each pass lists a
container and only downloads/extracts blobs modified after the stored
watermark, so repeat passes are cheap. Listing itself is still a full
enumeration; Event Grid / Change Feed push sync is the planned v2 path
(see README roadmap) and this module is shaped so a queue consumer can call
`index_blob()` per event without touching the rest.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from . import azure_client, meili
from .config import settings
from .extractors import extension_of, extract_text, is_extractable

log = logging.getLogger("bloblens.indexer")

BATCH_SIZE = 200
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------- state

def load_state() -> dict[str, Any]:
    try:
        with open(settings.STATE_FILE) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"watermarks": {}, "last_sync": None, "indexed_total": 0}


def save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(settings.STATE_FILE), exist_ok=True)
    tmp = settings.STATE_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh)
    os.replace(tmp, settings.STATE_FILE)


# ---------------------------------------------------------------- documents

def doc_id(container: str, blob_name: str) -> str:
    return hashlib.sha1(f"{container}/{blob_name}".encode()).hexdigest()


def build_document(container: str, blob) -> dict[str, Any]:
    text = ""
    if is_extractable(blob.name):
        data = azure_client.download_bytes(
            container, blob.name, settings.MAX_BLOB_MB * 1024 * 1024
        )
        if data is not None:
            text = extract_text(blob.name, data, settings.MAX_TEXT_CHARS)
        else:
            log.info("skipped text extraction (too large): %s/%s", container, blob.name)

    return {
        "id": doc_id(container, blob.name),
        "name": blob.name.rsplit("/", 1)[-1],
        "path": blob.name,
        "container": container,
        "extension": extension_of(blob.name),
        "size": blob.size,
        "last_modified": int(blob.last_modified.timestamp()),
        "content_type": (blob.content_settings.content_type or "")
        if blob.content_settings else "",
        "text": text,
    }


def index_blob(container: str, blob) -> None:
    """Index a single blob. Entry point for future event-driven sync."""
    meili.index().add_documents([build_document(container, blob)])


# ---------------------------------------------------------------- sync

def sync_container(container: str, state: dict[str, Any]) -> int:
    watermark_iso = state["watermarks"].get(container)
    watermark = (
        datetime.fromisoformat(watermark_iso) if watermark_iso else EPOCH
    )
    newest = watermark
    batch: list[dict[str, Any]] = []
    indexed = 0

    container_client = azure_client.service().get_container_client(container)
    for blob in container_client.list_blobs():
        if blob.last_modified <= watermark:
            continue
        batch.append(build_document(container, blob))
        newest = max(newest, blob.last_modified)
        if len(batch) >= BATCH_SIZE:
            meili.index().add_documents(batch)
            indexed += len(batch)
            batch = []

    if batch:
        meili.index().add_documents(batch)
        indexed += len(batch)

    state["watermarks"][container] = newest.isoformat()
    return indexed


def sync_all() -> int:
    state = load_state()
    total = 0
    for container in azure_client.target_containers():
        try:
            count = sync_container(container, state)
            total += count
            log.info("container %s: %d new/updated blobs indexed", container, count)
        except Exception:  # noqa: BLE001 - one bad container must not stop the rest
            log.exception("sync failed for container %s", container)
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    state["indexed_total"] = state.get("indexed_total", 0) + total
    save_state(state)
    return total
