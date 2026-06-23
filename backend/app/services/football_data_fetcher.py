"""football-data.org fetcher — wraps the API into FetchJobs.

Free tier: 10 req/min, per-competition scorers (top 10).
"""

from __future__ import annotations

import httpx
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..config import settings
from ..models.player import Player
from ..models.player_stats import PlayerSeasonStats
from ..database import SessionLocal

logger = logging.getLogger(__name__)

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

TARGET_COMPETITIONS = [
    ("PL", "Premier League"),
    ("PD", "Primera Division"),
    ("BL1", "Bundesliga"),
    ("SA", "Serie A"),
    ("FL1", "Ligue 1"),
    ("DED", "Eredivisie"),
    ("PPL", "Primeira Liga"),
    ("BSA", "Campeonato Brasileiro Série A"),
    ("ELC", "Championship"),
    ("CL", "UEFA Champions League"),
]

SEASON = "2025-2026"


def make_headers() -> dict:
    return {"X-Auth-Token": settings.football_data_key}


async def fetch_scorers(competition_code: str) -> dict:
    """Fetch top scorers for a competition."""
    if not settings.football_data_key:
        return {}

    url = f"{FOOTBALL_DATA_BASE}/competitions/{competition_code}/scorers"
    headers = make_headers()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("Failed to fetch scorers for %s", competition_code, exc_info=True)
            return {}


def _save_scorers(db: Session, competition_code: str, data: dict):
    """Save scorer data into PlayerSeasonStats."""
    for item in data.get("scorers", []):
        pdata = item["player"]
        player_name = pdata["name"]
        team_name = item.get("team", {}).get("name", "")

        players = (
            db.query(Player)
            .filter(
                Player.name.ilike(f"%{pdata['name'].split()[-1]}%"),
                Player.club_name.ilike(f"%{team_name.split()[-1]}%"),
            )
            .all()
        )

        if not players:
            last = pdata["name"].split()[-1]
            players = db.query(Player).filter(Player.name.ilike(f"%{last}%")).all()

        if not players:
            continue

        for pl in players:
            existing = (
                db.query(PlayerSeasonStats)
                .filter(
                    PlayerSeasonStats.player_id == pl.id,
                    PlayerSeasonStats.season == SEASON,
                    PlayerSeasonStats.competition_code == competition_code,
                )
                .first()
            )
            if existing:
                existing.goals = item.get("goals", 0)
                existing.assists = item.get("assists", 0)
                existing.appearances = item.get("playedMatches", 0)
                existing.penalties = item.get("penalties", 0)
                existing.fetched_at = str(datetime.utcnow())
            else:
                stat = PlayerSeasonStats(
                    player_id=pl.id,
                    season=SEASON,
                    competition_code=competition_code,
                    goals=item.get("goals", 0),
                    assists=item.get("assists", 0),
                    appearances=item.get("playedMatches", 0),
                    penalties=item.get("penalties", 0),
                    source="football-data.org",
                    fetched_at=str(datetime.utcnow()),
                )
                db.add(stat)


async def refresh_player_data():
    """Refresh player data from Football-Data.org."""
    db = SessionLocal()
    try:
        for code, name in TARGET_COMPETITIONS[:5]:
            data = await fetch_scorers(code)
            if data:
                _save_scorers(db, code, data)
        db.commit()
    finally:
        db.close()


async def fetch_competition_standings(competition_code: str) -> dict:
    """Fetch standings for a competition."""
    if not settings.football_data_key:
        return {}

    url = f"{FOOTBALL_DATA_BASE}/competitions/{competition_code}/standings"
    headers = make_headers()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("Failed to fetch standings for %s", competition_code, exc_info=True)
            return {}


class FootballDataFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)

    async def fetch_scorers(self, competition_code: str) -> dict:
        if not settings.football_data_key:
            return {}

        url = f"{FOOTBALL_DATA_BASE}/competitions/{competition_code}/scorers"
        headers = make_headers()

        try:
            resp = await self.client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("Failed to fetch scorers for %s", competition_code, exc_info=True)
            return {}

    async def refresh_player_data(self):
        await refresh_player_data()

    async def close(self):
        await self.client.aclose()


football_data_fetcher = FootballDataFetcher()