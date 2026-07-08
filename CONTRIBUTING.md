# Contributing to BlobLens

Thanks for your interest in improving BlobLens! Contributions of all sizes are
welcome — bug reports, docs, and PRs against the [roadmap](README.md#roadmap).

## Getting started

```bash
git clone https://github.com/<your-github-username>/bloblens && cd bloblens
cp .env.example .env         # fill in AZURE_STORAGE_CONNECTION_STRING
docker compose up            # full stack at http://localhost:8000
```

For backend-only work without Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # needs MEILI_URL pointing at a Meilisearch
```

## Running the tests

```bash
cd backend
pip install pytest
pytest
```

The current tests cover the pure text-extraction helpers (no Azure or
Meilisearch needed). New parsers or filters should come with a unit test.

## Pull requests

- Keep changes focused; one logical change per PR.
- Match the existing style — small modules, type hints, no new heavy
  dependencies in the core image (heavier parsers belong behind an optional
  compose profile).
- Never commit secrets. `.env` is gitignored; put example values in
  `.env.example` only.
- Describe what you changed and how you verified it.

## Reporting bugs

Open an issue with the BlobLens version, `docker compose logs` output (with
any secrets redacted), and steps to reproduce.
