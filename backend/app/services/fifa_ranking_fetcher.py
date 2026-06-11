"""FIFA World Ranking fetcher.

Fetches the latest FIFA/Coca-Cola World Ranking from the official FIFA website.
Updates Team.fifa_rank in the database.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models.team import Team

FIFA_RANKING_URL = "https://www.fifa.com/fifa-world-ranking/men"
FIFA_API_URL = "https://inside.fifa.com/api/rankings/men"


def fetch_rankings_from_api(client: httpx.Client | None = None) -> list[dict]:
    """Fetch FIFA rankings from the official FIFA API.

    Returns a list of { name, rank, points, confederation } dicts.
    """
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(
            FIFA_API_URL,
            params={"locale": "en"},
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            rankings = []
            # Handle various API response structures
            raw_rankings = (
                data.get("results", [])
                or data.get("rankings", [])
                or data.get("data", [])
                or (data if isinstance(data, list) else [])
            )
            for entry in raw_rankings:
                if not isinstance(entry, dict):
                    continue
                name = (
                    entry.get("name")
                    or entry.get("teamName")
                    or entry.get("country")
                    or ""
                )
                rank = entry.get("rank") or entry.get("position") or entry.get("ranking")
                points = entry.get("points") or entry.get("totalPoints")
                confed = entry.get("confederation") or entry.get("confed")

                if name and rank:
                    rankings.append({
                        "name": name.strip(),
                        "rank": int(rank) if rank else None,
                        "points": float(points) if points else None,
                        "confederation": confed,
                    })
            return rankings
    except Exception:
        pass
    finally:
        if close_client:
            client.close()

    return []


def fetch_rankings_from_web(client: httpx.Client | None = None) -> list[dict]:
    """Fallback: scrape FIFA rankings from the web page."""
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(
            FIFA_RANKING_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        rankings = []
        # Try to find JSON data embedded in the page
        json_pattern = re.compile(
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});', re.DOTALL
        )
        match = json_pattern.search(resp.text)
        if match:
            import json

            state = json.loads(match.group(1))
            ranking_data = (
                state.get("rankingData")
                or state.get("rankings")
                or state.get("pageData", {}).get("rankings")
                or []
            )
            for entry in ranking_data:
                name = entry.get("name") or entry.get("team") or ""
                rank = entry.get("rank") or entry.get("position")
                if name and rank:
                    rankings.append({
                        "name": name.strip(),
                        "rank": int(rank),
                        "points": entry.get("points"),
                        "confederation": entry.get("confederation"),
                    })

        return rankings
    except Exception:
        pass
    finally:
        if close_client:
            client.close()

    return []


def match_team(
    db: Session, ranking_name: str
) -> Team | None:
    """Match a FIFA ranking name to a Team in the database.

    Tries exact match first, then case-insensitive, then partial match.
    """
    # Exact match
    team = db.query(Team).filter(Team.name == ranking_name).first()
    if team:
        return team

    # Case-insensitive
    team = (
        db.query(Team)
        .filter(Team.name.ilike(ranking_name))
        .first()
    )
    if team:
        return team

    # Partial match (e.g., "USA" contains "United States")
    teams = db.query(Team).all()
    for t in teams:
        if ranking_name.lower() in t.name.lower() or t.name.lower() in ranking_name.lower():
            return t

    # Try by common name aliases
    NAME_ALIASES = {
        "USA": "United States",
        "IR Iran": "Iran",
        "Korea Republic": "South Korea",
        "Korea DPR": "North Korea",
        "Côte d'Ivoire": "Ivory Coast",
        "DR Congo": "Congo DR",
    }
    normalized = NAME_ALIASES.get(ranking_name, ranking_name)
    if normalized != ranking_name:
        return match_team(db, normalized)

    return None


def fetch_and_update_rankings(db: Session) -> dict:
    """Fetch latest FIFA rankings and update Team.fifa_rank."""
    rankings: list[dict] = []

    with httpx.Client(timeout=15.0) as client:
        rankings = fetch_rankings_from_api(client)
        if not rankings:
            rankings = fetch_rankings_from_web(client)

    if not rankings:
        return {
            "source": "fifa",
            "status": "error",
            "message": "Could not fetch FIFA rankings from any source",
            "teams_updated": 0,
        }

    updated = 0
    errors: list[dict] = []

    for entry in rankings:
        try:
            team = match_team(db, entry["name"])
            if team:
                team.fifa_rank = entry["rank"]
                updated += 1
        except Exception as exc:
            errors.append({"name": entry["name"], "error": str(exc)})

    if updated > 0:
        db.commit()

    return {
        "source": "fifa",
        "status": "ok" if not errors else "partial",
        "rankings_found": len(rankings),
        "teams_updated": updated,
        "errors": errors,
    }
