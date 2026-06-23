"""Dongqiudi World Cup group standings scraper.

Fetches group standings from the Dongqiudi World Cup standings page.
Reuses team-matching infrastructure from the national roster scraper.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models.dongqiudi_standings import DongqiudiStanding
from ..services.dongqiudi_national_roster import (
    DONGQIUDI_TEAM_ID_TO_CODE,
    BASE_URL,
    STANDINGS_URL,
    REQUEST_DELAY,
)

logger = logging.getLogger(__name__)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _to_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def fetch_standings_html(client: httpx.Client | None = None) -> str:
    """Fetch the Dongqiudi World Cup standings page HTML."""
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(STANDINGS_URL, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    finally:
        if close_client:
            client.close()


def fetch_standings_data(
    client: httpx.Client | None = None,
) -> list[dict]:
    """Try to fetch standings data from Dongqiudi API.

    Falls back to HTML parsing if API is not available.
    """
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        url = "https://pc.dongqiudi.com/sport-data/soccer/biz/dqd/v1/standings"
        params = {"cid": "61", "app": "dqd"}
        resp = client.get(
            url,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://pc.dongqiudi.com/data?cid=61&tab=standings",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and data.get("code") == 0:
                return data.get("data", []) or []
    except Exception:
        logger.warning("Failed to fetch standings data from Dongqiudi API", exc_info=True)

    return []


def parse_standings_from_api(
    items: list[dict],
) -> list[dict]:
    """Parse group standings from Dongqiudi API response.

    Expected format: list of groups, each with name and teams/entries.
    """
    results: list[dict] = []

    for group_item in items:
        if not isinstance(group_item, dict):
            continue

        group_name = (
            group_item.get("group_name")
            or group_item.get("group")
            or group_item.get("name")
        )
        entries = (
            group_item.get("teams")
            or group_item.get("table")
            or group_item.get("standings")
            or group_item.get("entries")
            or []
        )

        if not group_name or not entries:
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            team_name_cn = (
                entry.get("team_name")
                or entry.get("name")
                or entry.get("team")
                or ""
            )
            if not team_name_cn:
                continue

            # Map Chinese team name to Team code
            team_code = DONGQIUDI_TEAM_ID_TO_CODE_INV.get(team_name_cn)

            results.append({
                "group_name": group_name.strip(),
                "position": _to_int(entry.get("position") or entry.get("rank")),
                "team_code": team_code or "",
                "team_name_cn": team_name_cn.strip(),
                "played": _to_int(entry.get("played") or entry.get("matches_played") or entry.get("mp")),
                "won": _to_int(entry.get("won") or entry.get("wins")),
                "drawn": _to_int(entry.get("drawn") or entry.get("draws")),
                "lost": _to_int(entry.get("lost") or entry.get("losses")),
                "goals_for": _to_int(entry.get("goals_for") or entry.get("gf") or entry.get("scored")),
                "goals_against": _to_int(entry.get("goals_against") or entry.get("ga") or entry.get("conceded")),
                "goal_diff": _to_int(entry.get("goal_diff") or entry.get("gd")),
                "points": _to_int(entry.get("points") or entry.get("pts")),
                "raw_data": _json_dumps(entry),
            })

    return results


def parse_standings_from_html(html: str) -> list[dict]:
    """Parse group standings from Dongqiudi standings page HTML.

    Falls back to this if the API is not available.
    """
    results: list[dict] = []

    # Try to find group tables in HTML
    # Pattern: look for group headers followed by table rows
    group_pattern = re.compile(
        r'class=["\']group[^"\']*["\'][^>]*>.*?<span[^>]*>([A-Z])</span>.*?(?=<div\s+class=["\']group|\Z)',
        re.DOTALL,
    )

    # Simpler approach: try to find JSON data embedded in the page
    json_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', re.DOTALL)
    match = json_pattern.search(html)
    if match:
        try:
            state = json.loads(match.group(1))
            standings_data = (
                state.get("standings")
                or state.get("data", {}).get("standings")
                or state.get("pageData", {}).get("standings")
                or []
            )
            if standings_data:
                return parse_standings_from_api(standings_data)
        except (json.JSONDecodeError, AttributeError):
            pass

    return results


def upsert_standings(db: Session, records: list[dict]) -> int:
    """Upsert standings records into the dongqiudi_standings table."""
    saved = 0
    for rec in records:
        if not rec.get("team_code"):
            continue

        existing = (
            db.query(DongqiudiStanding)
            .filter(
                DongqiudiStanding.tournament_year == 2026,
                DongqiudiStanding.group_name == rec["group_name"],
                DongqiudiStanding.team_code == rec["team_code"],
            )
            .first()
        )

        if existing:
            for k, v in rec.items():
                if k not in ("group_name", "team_code"):
                    setattr(existing, k, v)
        else:
            db.add(DongqiudiStanding(
                tournament_year=2026,
                **rec,
            ))
        saved += 1

    db.commit()
    return saved


# Build inverse mapping: Chinese team name -> code
# This is populated dynamically from the DB when scrape_all_standings is called
DONGQIUDI_TEAM_ID_TO_CODE_INV: dict[str, str] = {}


def _build_team_name_mapping(db: Session) -> dict[str, str]:
    """Build a mapping of Chinese team names to team codes."""
    from ..models.dongqiudi_data import DongqiudiTeamData

    mapping: dict[str, str] = {}
    teams = db.query(DongqiudiTeamData).filter(
        DongqiudiTeamData.matched_team_code.isnot(None)
    ).all()
    for t in teams:
        if t.name_cn:
            mapping[t.name_cn.strip()] = t.matched_team_code
    return mapping


def scrape_all_standings(db: Session) -> dict:
    """Fetch all group standings from Dongqiudi and persist to DB."""
    global DONGQIUDI_TEAM_ID_TO_CODE_INV
    DONGQIUDI_TEAM_ID_TO_CODE_INV = _build_team_name_mapping(db)

    errors: list[dict] = []

    with httpx.Client(timeout=15.0) as client:
        try:
            items = fetch_standings_data(client)
            if items:
                records = parse_standings_from_api(items)
            else:
                html = fetch_standings_html(client)
                records = parse_standings_from_html(html)

            saved = upsert_standings(db, records)

        except Exception as exc:
            errors.append({"error": str(exc)})
            saved = 0

    return {
        "source": "dongqiudi",
        "type": "standings",
        "records_saved": saved,
        "errors": errors,
    }
