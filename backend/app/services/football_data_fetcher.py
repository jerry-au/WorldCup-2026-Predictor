"""football-data.org fetcher — wraps the API into FetchJobs.

Free tier: 10 req/min, per-competition scorers (top 10).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import settings
from ..models.player import Player
from ..models.player_stats import PlayerSeasonStats
from .fetcher import DataFetcher, FetchJob

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

# Competitions relevant to our 1254 players
# (top leagues = most WC players)
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


def enqueue_scorers(fetcher: DataFetcher, db: Session) -> int:
    """Enqueue scorer fetch jobs for all target competitions.

    Returns number of jobs enqueued.
    """

    def _save_scorers(job: FetchJob, data: dict):
        """Callback: save scorer data into PlayerSeasonStats."""
        competition = job.params.get("competition_code", "?")
        for item in data.get("scorers", []):
            pdata = item["player"]
            player_name = pdata["name"]
            team_name = item.get("team", {}).get("name", "")

            # Fuzzy match player by name containing their last name
            # (football-data names like "Erling Haaland" vs our "Erling Haaland")
            players = (
                db.query(Player)
                .filter(
                    Player.name.ilike(f"%{pdata['name'].split()[-1]}%"),
                    Player.club_name.ilike(f"%{team_name.split()[-1]}%"),
                )
                .all()
            )

            if not players:
                # Fallback: match by last name only
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
                        PlayerSeasonStats.competition_code == competition,
                    )
                    .first()
                )
                if existing:
                    existing.goals = item.get("goals", 0)
                    existing.assists = item.get("assists", 0)
                    existing.appearances = item.get("playedMatches", 0)
                    existing.penalties = item.get("penalties", 0)
                else:
                    stat = PlayerSeasonStats(
                        player_id=pl.id,
                        season=SEASON,
                        competition_code=competition,
                        goals=item.get("goals", 0),
                        assists=item.get("assists", 0),
                        appearances=item.get("playedMatches", 0),
                        penalties=item.get("penalties", 0),
                        source="football-data.org",
                        fetched_at=str(datetime.utcnow()),
                    )
                    db.add(stat)
        db.commit()

    from datetime import datetime

    count = 0
    for code, name in TARGET_COMPETITIONS:
        job = FetchJob(
            source="football-data.org",
            url=f"{FOOTBALL_DATA_BASE}/competitions/{code}/scorers",
            params={"competition_code": code, "limit": 10},
            headers=make_headers(),
            callback=_save_scorers,
            priority=5,  # Medium priority
        )
        fetcher.enqueue(job)
        count += 1
    return count


def enqueue_competition_standings(fetcher: DataFetcher) -> int:
    """Enqueue standings fetch for all target competitions."""
    count = 0
    for code, name in TARGET_COMPETITIONS:
        job = FetchJob(
            source="football-data.org",
            url=f"{FOOTBALL_DATA_BASE}/competitions/{code}/standings",
            headers=make_headers(),
            priority=3,
        )
        fetcher.enqueue(job)
        count += 1
    return count
