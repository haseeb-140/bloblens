"""BlobLens API: proxies Meilisearch and issues download links."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import azure_client, indexer, meili
from .config import settings

app = FastAPI(title="BlobLens", version="0.1.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/search")
def search(
    q: str = Query("", max_length=500),
    container: str | None = None,
    ext: str | None = None,
    sort: str | None = Query(None, pattern="^(last_modified|size|name):(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    filters = []
    if container:
        filters.append(f'container = "{container}"')
    if ext:
        filters.append(f'extension = "{ext}"')

    params: dict = {
        "limit": limit,
        "offset": offset,
        "filter": " AND ".join(filters) if filters else None,
        "facets": ["container", "extension"],
        "attributesToHighlight": ["name", "path", "text"],
        "attributesToCrop": ["text"],
        "cropLength": 30,
        "highlightPreTag": "<mark>",
        "highlightPostTag": "</mark>",
    }
    if sort:
        params["sort"] = [sort]

    try:
        result = meili.index().search(q, {k: v for k, v in params.items() if v is not None})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"search backend error: {exc}")

    hits = []
    for hit in result.get("hits", []):
        formatted = hit.get("_formatted", {})
        hits.append({
            "id": hit["id"],
            "name": hit["name"],
            "name_html": formatted.get("name", hit["name"]),
            "path": hit["path"],
            "path_html": formatted.get("path", hit["path"]),
            "container": hit["container"],
            "extension": hit["extension"],
            "size": hit["size"],
            "last_modified": hit["last_modified"],
            "excerpt_html": formatted.get("text", ""),
        })

    return {
        "hits": hits,
        "total": result.get("estimatedTotalHits", 0),
        "facets": result.get("facetDistribution", {}),
        "processing_ms": result.get("processingTimeMs", 0),
    }


@app.get("/api/stats")
def stats() -> dict:
    state = indexer.load_state()
    try:
        meili_stats = meili.index().get_stats()
        doc_count = meili_stats.number_of_documents
    except Exception:  # noqa: BLE001
        doc_count = 0
    return {
        "documents": doc_count,
        "last_sync": state.get("last_sync"),
        "containers": list(state.get("watermarks", {}).keys()),
    }


@app.get("/api/download")
def download(container: str, path: str) -> dict:
    try:
        return {"url": azure_client.sas_url(container, path)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"could not create link: {exc}")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
