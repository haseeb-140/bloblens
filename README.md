# ◍ BlobLens

**Full-text search for Azure Blob Storage. Self-hosted, one command, $0.**

Azure's answer to "search my blobs" is Azure AI Search — roughly **$75/month
(Basic)** to **$250+/month (Standard)** just to index your own storage.
Azure Storage Explorer's "search" is a prefix-only name listing.

BlobLens gives you file-name, path, and **inside-the-document** search
(PDF, DOCX, text/code files) over your storage account, running on any box
that has Docker:

```
docker compose up
```

Then open **http://localhost:8000**.

|                          | Azure AI Search | Storage Explorer | BlobLens |
| ------------------------ | --------------- | ---------------- | -------- |
| Full-text inside PDF/DOCX| ✅              | ❌               | ✅       |
| Search-as-you-type UI    | ❌ (BYO)        | ❌               | ✅       |
| Facets (container, type) | ✅              | ❌               | ✅       |
| Incremental sync         | ✅              | —                | ✅       |
| Monthly cost             | $75–$250+       | $0               | **$0**   |
| Runs on a $6 droplet     | ❌              | —                | ✅       |

> Typo-tolerant, sub-50ms search courtesy of [Meilisearch](https://meilisearch.com).

<!-- Replace with a screenshot / GIF of the search UI, e.g.:
     ![BlobLens search UI](docs/screenshot.png)
     A short GIF of search-as-you-type over a real container is the single
     most effective thing you can add to this README. -->

## Quickstart

```bash
git clone https://github.com/YOURNAME/bloblens && cd bloblens
cp .env.example .env
# paste your storage connection string into .env
docker compose up -d
```

The worker starts a first crawl immediately; watch it with
`docker compose logs -f worker`. Search is live at `http://localhost:8000`
as documents stream in.

**Where to get the connection string:** Azure Portal → your Storage account →
*Access keys* → *Connection string*. A key with read access is enough for
indexing; the same key is used to mint short-lived SAS download links.

## What gets indexed

Every blob's **name, path, container, extension, size, and last-modified
date** — plus extracted text for:

| Type | Parser |
| ---- | ------ |
| `pdf` | pypdf |
| `docx` | python-docx |
| `txt md csv json log yml xml html sql py js ts sh cs java go rb php …` | UTF-8 decode |

Extracted text is capped (`MAX_TEXT_CHARS`, default 50k chars) so a 300-page
PDF doesn't bloat the index — the excerpt plus a download link is what you
want anyway. Blobs over `MAX_BLOB_MB` (default 50) are indexed by metadata
only.

## How sync works

```
Azure Blob Storage ──list──▶ worker ──extract──▶ Meilisearch ◀──/api/search── FastAPI ◀── UI
        ▲                      │
        └──── download ────────┘  (per-container Last-Modified watermark)
```

Each pass, the worker lists a container and only downloads blobs modified
after the stored watermark, so repeat passes after the initial crawl are
cheap. State lives in a named volume (`indexer_state`), so restarts don't
re-crawl.

Download links are **SAS URLs generated on demand** (default 60-minute
expiry) — nothing is pre-signed, nothing is proxied through the app.

## Configuration

All via `.env` — see [`.env.example`](.env.example). The useful ones:

| Variable | Default | Meaning |
| -------- | ------- | ------- |
| `BLOB_CONTAINERS` | *(all)* | Comma-separated containers to index |
| `SYNC_INTERVAL_SECONDS` | `300` | Delay between incremental passes |
| `MAX_TEXT_CHARS` | `50000` | Extracted text stored per document |
| `MAX_BLOB_MB` | `50` | Skip text extraction above this size |
| `SAS_EXPIRY_MINUTES` | `60` | Download link lifetime |
| `MEILI_MASTER_KEY` | dev key | **Change before exposing anything** |

## API

The UI is a thin client over three endpoints you can use directly:

```
GET /api/search?q=invoice&container=uploads&ext=pdf&sort=last_modified:desc
GET /api/stats
GET /api/download?container=uploads&path=2026/03/invoice-081.pdf
```

## Security notes

- BlobLens is built to run **inside your network** (localhost, VPN, or behind
  your reverse proxy + auth). It ships with no login of its own.
- The connection string never leaves the backend containers; the browser only
  ever sees search results and short-lived SAS links.
- Set a real `MEILI_MASTER_KEY`; Meilisearch is not exposed by the compose
  file, but defense in depth is free.

## Roadmap

- [ ] **Event-driven sync** — Event Grid / Blob Change Feed → queue → indexer,
      for near-real-time indexing without list scans (`indexer.index_blob()`
      is already shaped for this)
- [ ] Deletion reconciliation (remove index docs for deleted blobs)
- [ ] Managed identity / `DefaultAzureCredential` auth
- [ ] Blob index tags + user metadata as filterable facets
- [ ] Optional Tika sidecar profile for long-tail formats (eml, odt, legacy doc)
- [ ] Optional OCR profile (Tesseract) for scanned PDFs and images
- [ ] Multi-account support

## Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload            # needs MEILI_URL pointing somewhere
python -m app.worker                     # one-shot: python -c "from app import indexer; indexer.sync_all()"
```

PRs welcome — especially on the roadmap items above.

## License

[MIT](LICENSE)
