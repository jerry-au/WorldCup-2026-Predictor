"""Batch data fetching orchestration.

Run via API trigger or scheduled interval.
Usage:
    from app.tasks.batch_fetch import run_football_data_batch
    result = run_football_data_batch()
"""

from ..database import SessionLocal
from ..services.fetcher import DataFetcher

# ── football-data.org ──

def run_football_data_batch() -> dict:
    """Fetch scorers from all target leagues via football-data.org.

    Respects 10 req/min rate limit. Processes ~10 leagues = ~10 req.
    """
    from ..services.football_data_fetcher import enqueue_scorers

    db = SessionLocal()
    fetcher = DataFetcher()

    try:
        jobs = enqueue_scorers(fetcher, db)
        results = fetcher.run_batch(batch_size=jobs)
    finally:
        db.close()

    success = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    return {
        "source": "football-data.org",
        "total_jobs": len(results),
        "success": success,
        "failed": failed,
        "queue_remaining": fetcher.queue_status()["queue_length"],
    }


# ── Zafronix ──

def run_zafronix_results_batch() -> dict:
    """Fetch latest match results from Zafronix.

    Respects 250 req/day limit.
    """
    from ..services.fetcher import FetchJob
    from ..config import settings

    db = SessionLocal()
    fetcher = DataFetcher()

    try:
        job = FetchJob(
            source="zafronix",
            url="https://api.zafronix.com/fifa/worldcup/v1/matches",
            params={"tournament": "2026", "status": "completed"},
            headers={"X-API-Key": settings.zafronix_api_key},
            priority=10,
        )
        fetcher.enqueue(job)
        results = fetcher.run_batch(batch_size=1)
    finally:
        db.close()

    return {
        "source": "zafronix",
        "total_jobs": len(results),
        "success": sum(1 for r in results if r["status"] == "ok"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "queue_remaining": fetcher.queue_status()["queue_length"],
    }
