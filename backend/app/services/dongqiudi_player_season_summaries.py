"""Dongqiudi player season summary scraper.

Fetches season-level career statistics from:
https://sport-data.dongqiudi.com/soccer/biz/dqd/person/statistic_new/{person_id}?lang=zh-cn

The returned data includes four categories: total, league, cup, national.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models.dongqiudi_data import DongqiudiPlayerData
from ..models.player_season_summary import DongqiudiPlayerSeasonSummary

API_URL = "https://sport-data.dongqiudi.com/soccer/biz/dqd/person/statistic_new/{player_id}?lang=zh-cn"
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

CATEGORY_NAMES = {
    "总计": "total",
    "联赛": "league",
    "杯赛": "cup",
    "国家队": "national",
    "国家/地区队": "national",
}


def _parse_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "")
    if text in ("", "-"):
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_table_category(html: str) -> str:
    tabs_match = re.search(r'<div[^>]*class="[^"]*pp-stat-tabs[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not tabs_match:
        tabs_match = re.search(r'<div[^>]*class="[^"]*pp-tabs[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not tabs_match:
        return "total"

    active_match = re.search(
        r'<button[^>]*class="[^"]*(?:pp-stat-tab--active|active)[^"]*"[^>]*>(.*?)</button>',
        tabs_match.group(1),
        re.DOTALL,
    )
    if not active_match:
        return "total"

    title = _strip_html(active_match.group(1))
    return CATEGORY_NAMES.get(title, "total")


def parse_player_page(html: str, player_id: str) -> list[dict]:
    """Parse a Dongqiudi season-summary HTML table.

    This parser is mainly used as a fallback/test helper. Runtime scraping uses
    the JSON career-stats API via parse_statistic_payload().
    """
    category = _extract_table_category(html)
    table_match = re.search(
        r'<table[^>]*class="[^"]*pp-table[^"]*"[^>]*>\s*<thead[^>]*>\s*<tr[^>]*>\s*'
        r'<th[^>]*>\s*赛季\s*</th>\s*<th[^>]*>\s*俱乐部\s*</th>.*?'
        r'</thead>\s*<tbody[^>]*>(.*?)</tbody>',
        html,
        re.DOTALL,
    )
    if not table_match:
        return []

    records = []
    for row_html in re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(1), re.DOTALL):
        cells = [_strip_html(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)]
        if len(cells) < 8:
            continue
        records.append({
            "category": category,
            "season": cells[0],
            "club_name": cells[1],
            "appearances": _parse_int(cells[2]),
            "starts": _parse_int(cells[3]),
            "goals": _parse_int(cells[4]),
            "assists": _parse_int(cells[5]),
            "yellow_cards": _parse_int(cells[6]),
            "red_cards": _parse_int(cells[7]),
        })

    return records


def _list_to_stats(items: list[dict]) -> dict[str, int]:
    values = {str(i.get("title", "")): i.get("value") for i in items}
    return {
        "appearances": _parse_int(values.get("出场")),
        "starts": _parse_int(values.get("首发")),
        "goals": _parse_int(values.get("进球")),
        "assists": _parse_int(values.get("助攻")),
        "yellow_cards": _parse_int(values.get("黄牌")),
        "red_cards": _parse_int(values.get("红牌")),
    }


def _record_from_api(category: str, item: dict) -> dict:
    season = item.get("season") or {}
    team = item.get("team") or {}
    competition = item.get("competition") or {}

    if category == "total":
        stats = _list_to_stats(item.get("list") or [])
    else:
        base_info = item.get("base_info") or {}
        discipline = item.get("discipline") or {}
        stats = {
            "appearances": _parse_int(base_info.get("appearances")),
            "starts": _parse_int(base_info.get("starts")),
            "goals": _parse_int(base_info.get("goals")),
            "assists": _parse_int(base_info.get("assists")),
            "yellow_cards": _parse_int(discipline.get("yellow_cards")),
            "red_cards": _parse_int(discipline.get("red_cards")),
        }

    return {
        "category": category,
        "season": str(season.get("name") or season.get("season") or ""),
        "club_name": str(team.get("short_name") or team.get("name") or ""),
        "competition_name": competition.get("short_name") or competition.get("name"),
        **stats,
    }


def parse_statistic_payload(payload: dict) -> list[dict]:
    """Parse career-stats JSON payload into normalized season summary records."""
    records = []
    for category in ("total", "league", "cup", "national"):
        for item in payload.get(category) or []:
            record = _record_from_api(category, item)
            if record["season"] and record["club_name"]:
                records.append(record)
    return records


def scrape_player_season_summaries(
    player_id: str,
    db: Session,
    client: httpx.Client | None = None,
) -> dict:
    """Scrape season summary records for a single Dongqiudi player."""
    close_client = client is None
    client = client or httpx.Client(headers=HEADERS, timeout=15.0)

    try:
        resp = client.get(API_URL.format(player_id=player_id))
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        return {
            "player_id": player_id,
            "error": str(exc),
            "records_found": 0,
            "records_saved": 0,
        }
    finally:
        if close_client:
            client.close()

    records = parse_statistic_payload(payload)
    dqd_player = (
        db.query(DongqiudiPlayerData)
        .filter(DongqiudiPlayerData.person_id == str(player_id))
        .first()
    )

    if not dqd_player:
        return {
            "player_id": player_id,
            "error": "Dongqiudi player not found in DB",
            "records_found": len(records),
            "records_saved": 0,
        }

    saved = 0
    for rec in records:
        existing = (
            db.query(DongqiudiPlayerSeasonSummary)
            .filter(
                DongqiudiPlayerSeasonSummary.dongqiudi_player_id == dqd_player.id,
                DongqiudiPlayerSeasonSummary.category == rec["category"],
                DongqiudiPlayerSeasonSummary.season == rec["season"],
                DongqiudiPlayerSeasonSummary.club_name == rec["club_name"],
                DongqiudiPlayerSeasonSummary.competition_name == rec.get("competition_name"),
            )
            .first()
        )

        if existing:
            existing.appearances = rec["appearances"]
            existing.starts = rec["starts"]
            existing.goals = rec["goals"]
            existing.assists = rec["assists"]
            existing.yellow_cards = rec["yellow_cards"]
            existing.red_cards = rec["red_cards"]
        else:
            db.add(DongqiudiPlayerSeasonSummary(
                dongqiudi_player_id=dqd_player.id,
                matched_player_id=dqd_player.matched_player_id,
                category=rec["category"],
                season=rec["season"],
                club_name=rec["club_name"],
                competition_name=rec.get("competition_name"),
                appearances=rec["appearances"],
                starts=rec["starts"],
                goals=rec["goals"],
                assists=rec["assists"],
                yellow_cards=rec["yellow_cards"],
                red_cards=rec["red_cards"],
            ))
        saved += 1

    db.commit()
    return {
        "player_id": player_id,
        "person_name": dqd_player.person_name,
        "records_found": len(records),
        "records_saved": saved,
        "matched_player_id": dqd_player.matched_player_id,
    }


def scrape_all_player_season_summaries(db: Session) -> dict:
    """Scrape season summary records for all Dongqiudi players with a person_id."""
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
    total_found = 0
    total_saved = 0
    errors = []

    with httpx.Client(headers=HEADERS, timeout=15.0) as client:
        for player in unique_players:
            try:
                result = scrape_player_season_summaries(str(player.person_id), db, client)
                results.append(result)
                total_found += result.get("records_found", 0)
                total_saved += result.get("records_saved", 0)
                if "error" in result:
                    errors.append(result)
                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                errors.append({"player_id": str(player.person_id), "error": str(exc)})

    return {
        "players_total": len(unique_players),
        "players_scraped": len(results) - len(errors),
        "records_found": total_found,
        "records_saved": total_saved,
        "errors": errors,
    }
