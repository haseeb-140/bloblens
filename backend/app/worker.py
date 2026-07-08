"""Indexer worker: bootstrap the index, then sync on an interval."""
import logging
import time

from . import indexer, meili
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("bloblens.worker")


def wait_for_meili(retries: int = 30, delay: float = 2.0) -> None:
    for attempt in range(retries):
        try:
            meili.client().health()
            return
        except Exception:  # noqa: BLE001
            log.info("waiting for Meilisearch (%d/%d)...", attempt + 1, retries)
            time.sleep(delay)
    raise RuntimeError("Meilisearch did not become healthy in time")


def main() -> None:
    wait_for_meili()
    meili.ensure_index()
    log.info(
        "starting sync loop, interval=%ss, containers=%s",
        settings.SYNC_INTERVAL_SECONDS,
        settings.CONTAINERS or "(all)",
    )
    while True:
        started = time.monotonic()
        try:
            count = indexer.sync_all()
            log.info(
                "sync pass complete: %d documents in %.1fs",
                count,
                time.monotonic() - started,
            )
        except Exception:  # noqa: BLE001
            log.exception("sync pass failed; retrying next interval")
        time.sleep(settings.SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
