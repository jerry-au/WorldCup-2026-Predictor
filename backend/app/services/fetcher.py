"""Rate-limited data fetcher with queue management.

Manages API quota across multiple data sources and executes
fetch jobs in batches without exceeding free-tier limits.
"""

import time
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable

import httpx


@dataclass
class FetchJob:
    """A single fetch task."""
    source: str          # "football-data.org", "zafronix", "odds-api"
    url: str
    params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    callback: Callable | None = None  # Called with (job, response_json)
    priority: int = 0     # Higher = more urgent
    retries: int = 0
    max_retries: int = 3


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.tokens = max_per_minute
        self.last_refill = time.time()

    def wait_if_needed(self):
        now = time.time()
        elapsed = now - self.last_refill
        # Refill tokens
        self.tokens = min(self.max_per_minute, self.tokens + elapsed * self.max_per_minute / 60.0)
        self.last_refill = now

        if self.tokens < 1:
            sleep_time = 60.0 / self.max_per_minute
            time.sleep(sleep_time)
            self.tokens = 0
            self.last_refill = time.time()
        else:
            self.tokens -= 1


class DataFetcher:
    """Orchestrates fetch jobs across multiple data sources."""

    def __init__(self):
        self.limiters = {
            "football-data.org": RateLimiter(8),   # keep 2 buffer below 10/min
            "zafronix": RateLimiter(8),             # 250/day ≈ 10/hr, keep buffer
            "odds-api": RateLimiter(2),             # 500/month ≈ 1/90min
        }
        self.queue: list[FetchJob] = []
        self.results: list[dict] = []
        self.stats = {"total": 0, "success": 0, "failed": 0}

    def enqueue(self, job: FetchJob):
        self.queue.append(job)

    def run_batch(self, batch_size: int = 10) -> list[dict]:
        """Process up to batch_size jobs from the queue."""
        # Sort by priority descending
        self.queue.sort(key=lambda j: j.priority, reverse=True)

        batch = self.queue[:batch_size]
        self.queue = self.queue[batch_size:]
        results = []

        for job in batch:
            limiter = self.limiters.get(job.source)
            if limiter:
                limiter.wait_if_needed()

            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(job.url, params=job.params, headers=job.headers)
                    resp.raise_for_status()
                    data = resp.json()

                if job.callback:
                    job.callback(job, data)

                results.append({"job": job, "status": "ok", "data": data})
                self.stats["success"] += 1

            except Exception as e:
                job.retries += 1
                if job.retries < job.max_retries:
                    self.queue.append(job)  # Re-queue
                results.append({"job": job, "status": "error", "error": str(e)})
                self.stats["failed"] += 1

            self.stats["total"] += 1

        return results

    def queue_status(self) -> dict:
        return {
            "queue_length": len(self.queue),
            "stats": self.stats,
        }
