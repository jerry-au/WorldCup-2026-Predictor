"""Dongqiudi player ability (综合能力) scraper.

Fetches FIFA-style player ability ratings from:
https://sport-data.dongqiudi.com/soccer/data/sofifa/v1/player_ability/{ability_id}?player_type=

The ability_id is extracted from the person/detail API response (ability_url field).

Data includes:
- Overall rating and hexagon radar stats (pace, shooting, passing, dribbling, defending, physical)
- Star skills (international_reputation, weak_foot, skill_moves)
- Detailed bar info (7 categories with sub-skills)
- Position ratings for all positions
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models.dongqiudi_data import DongqiudiPlayerData
from ..models.player_ability import DongqiudiPlayerAbility

logger = logging.getLogger(__name__)

ABILITY_API_URL = (
    "https://sport-data.dongqiudi.com/soccer/data/sofifa/v1/player_ability/{ability_id}?player_type="
)
PERSON_DETAIL_URL = (
    "https://sport-data.dongqiudi.com/soccer/biz/dqd/v1/person/detail/{person_id}?app=dqd&lang=zh-cn"
)
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://topic.dongqiudi.com",
    "Referer": "https://topic.dongqiudi.com/",
    "Accept": "application/json, text/plain, */*",
}

RADAR_KEYS = {
    "速度": "pace",
    "力量": "physical",
    "防守": "defending",
    "盘带": "dribbling",
    "传球": "passing",
    "射门": "shooting",
}

STAR_SKILL_KEYS = {
    "国际声望": "international_reputation",
    "逆足能力": "weak_foot",
    "花式技巧": "skill_moves",
}


def _extract_ability_id(person_detail: dict) -> str | None:
    """Extract ability_id from person/detail API response."""
    base_info = person_detail.get("base_info") or {}
    ability_url = base_info.get("ability_url") or ""
    m = re.search(r"id=(\d+)", ability_url)
    if m:
        return m.group(1)
    return None


def parse_ability_payload(payload: dict, ability_id: str) -> dict | None:
    """Parse sofifa player ability API response into a normalized dict.

    Returns None if the API response contains no data (data is None).
    """
    data = payload.get("data")
    if data is None:
        return None

    average = data.get("average") or {}
    foot_info = data.get("foot_info") or {}
    good_pos = data.get("good_pos") or {}
    redar_list = data.get("redar") or []
    star_bar = data.get("star_bar") or []
    bar_info = data.get("bar_info") or []
    fields = data.get("fields") or []

    result: dict[str, Any] = {
        "ability_id": ability_id,
        "overall": int(average.get("val", 0)),
        "pace": 0,
        "shooting": 0,
        "passing": 0,
        "dribbling": 0,
        "defending": 0,
        "physical": 0,
        "foot": str(foot_info.get("val", "")),
        "registered_position": str(good_pos.get("val", "")),
        "version": str(data.get("version", "")),
        "last_grab_time": str(data.get("last_grab_time", "")),
        "star_skills": json.dumps(star_bar, ensure_ascii=False),
        "position_ratings": json.dumps(fields, ensure_ascii=False),
        "bar_info": json.dumps(bar_info, ensure_ascii=False),
        "raw_data": json.dumps(payload, ensure_ascii=False),
    }

    for item in redar_list:
        name = item.get("name", "")
        val = int(item.get("val", 0))
        key = RADAR_KEYS.get(name)
        if key:
            result[key] = val

    return result


def fetch_ability_id(person_id: str, client: httpx.Client) -> str | None:
    """Fetch ability_id from person/detail API."""
    try:
        resp = client.get(PERSON_DETAIL_URL.format(person_id=person_id))
        resp.raise_for_status()
        data = resp.json()
        return _extract_ability_id(data)
    except Exception:
        logger.warning("Failed to fetch ability_id for person_id=%s", person_id, exc_info=True)
        return None


def scrape_player_ability(
    person_id: str,
    db: Session,
    client: httpx.Client | None = None,
) -> dict:
    """Scrape ability data for a single Dongqiudi player.

    Two-step process:
    1. Fetch person/detail to get ability_id from ability_url
    2. Fetch player_ability API with ability_id
    """
    close_client = client is None
    client = client or httpx.Client(headers=HEADERS, timeout=15.0)

    dqd_player = (
        db.query(DongqiudiPlayerData)
        .filter(DongqiudiPlayerData.person_id == str(person_id))
        .first()
    )

    if not dqd_player:
        if close_client:
            client.close()
        return {
            "person_id": person_id,
            "error": "Dongqiudi player not found in DB",
            "saved": False,
        }

    try:
        # Step 1: Get ability_id from person/detail
        ability_id = fetch_ability_id(person_id, client)
        if not ability_id:
            return {
                "person_id": person_id,
                "person_name": dqd_player.person_name,
                "error": "Could not extract ability_id",
                "saved": False,
            }

        # Step 2: Fetch ability data
        resp = client.get(ABILITY_API_URL.format(ability_id=ability_id))
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        return {
            "person_id": person_id,
            "person_name": dqd_player.person_name,
            "error": str(exc),
            "saved": False,
        }
    finally:
        if close_client:
            client.close()

    record = parse_ability_payload(payload, ability_id)
    if record is None:
        return {
            "person_id": person_id,
            "person_name": dqd_player.person_name,
            "ability_id": ability_id,
            "error": "API returned empty data",
            "saved": False,
        }

    existing = (
        db.query(DongqiudiPlayerAbility)
        .filter(DongqiudiPlayerAbility.dongqiudi_player_id == dqd_player.id)
        .first()
    )

    if existing:
        existing.ability_id = record["ability_id"]
        existing.overall = record["overall"]
        existing.pace = record["pace"]
        existing.shooting = record["shooting"]
        existing.passing = record["passing"]
        existing.dribbling = record["dribbling"]
        existing.defending = record["defending"]
        existing.physical = record["physical"]
        existing.star_skills = record["star_skills"]
        existing.position_ratings = record["position_ratings"]
        existing.bar_info = record["bar_info"]
        existing.foot = record["foot"]
        existing.registered_position = record["registered_position"]
        existing.version = record["version"]
        existing.last_grab_time = record["last_grab_time"]
        existing.raw_data = record["raw_data"]
    else:
        db.add(DongqiudiPlayerAbility(
            dongqiudi_player_id=dqd_player.id,
            matched_player_id=dqd_player.matched_player_id,
            ability_id=record["ability_id"],
            overall=record["overall"],
            pace=record["pace"],
            shooting=record["shooting"],
            passing=record["passing"],
            dribbling=record["dribbling"],
            defending=record["defending"],
            physical=record["physical"],
            star_skills=record["star_skills"],
            position_ratings=record["position_ratings"],
            bar_info=record["bar_info"],
            foot=record["foot"],
            registered_position=record["registered_position"],
            version=record["version"],
            last_grab_time=record["last_grab_time"],
            raw_data=record["raw_data"],
        ))

    db.commit()
    return {
        "person_id": person_id,
        "person_name": dqd_player.person_name,
        "ability_id": ability_id,
        "overall": record["overall"],
        "saved": True,
        "matched_player_id": dqd_player.matched_player_id,
    }


def scrape_all_player_abilities(db: Session) -> dict:
    """Scrape ability data for all Dongqiudi players with a person_id."""
    players = (
        db.query(DongqiudiPlayerData)
        .filter(DongqiudiPlayerData.person_id.isnot(None))
        .all()
    )

    seen_ids: set[str] = set()
    unique_players = []
    for player in players:
        person_id = str(player.person_id)
        if person_id not in seen_ids:
            seen_ids.add(person_id)
            unique_players.append(player)

    results = []
    total_saved = 0
    errors = []

    with httpx.Client(headers=HEADERS, timeout=15.0) as client:
        for player in unique_players:
            try:
                result = scrape_player_ability(str(player.person_id), db, client)
                results.append(result)
                if result.get("saved"):
                    total_saved += 1
                if "error" in result:
                    errors.append(result)
                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                errors.append({"person_id": str(player.person_id), "error": str(exc)})

    return {
        "players_total": len(unique_players),
        "players_scraped": len(results) - len(errors),
        "abilities_saved": total_saved,
        "errors": errors,
    }
