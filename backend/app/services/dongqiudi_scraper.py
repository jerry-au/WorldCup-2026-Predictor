"""Dongqiudi player stats scraper v2.

Strategy:
  1. Scrape league player listing → extract player IDs + goals/assists
  2. Scrape each player's detail page → extract English name
  3. Save ALL scraped data to scraped_data table (raw data store)
  4. Match English name against our database for those we can
  5. Save matched season stats to PlayerSeasonStats

League CID mapping:
  PL=82 英超 | PD=119 西甲 | BL1=92 德甲
  SA=116 意甲 | FL1=158 法甲 | ELC=14 英冠
"""

import logging
import re
import time

import httpx

from ..models.player import Player
from ..models.player_stats import PlayerSeasonStats
from ..models.scraped_data import ScrapedPlayerData

logger = logging.getLogger(__name__)

LEAGUE_CID = {
    "PL": 82, "PD": 119, "BL1": 92,
    "SA": 116, "FL1": 158, "ELC": 14,
}

SEASON = "2025-2026"
DELAY_BETWEEN_PLAYERS = 0.8
DELAY_BETWEEN_LEAGUES = 2.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

client = httpx.Client(headers=HEADERS, timeout=15.0)


def _parse_int(val: str) -> int:
    try:
        return int(val.replace(",", "").replace("(", "").replace(")", ""))
    except (ValueError, TypeError):
        return 0


def scrape_listing(cid: int) -> list[dict]:
    """Scrape player listing for a league."""
    url = f"https://pc.dongqiudi.com/data?cid={cid}&tab=person&sub=goal"
    resp = client.get(url)
    html = resp.text

    id_links = re.findall(r"/player/(\d+)", html)
    player_ids = list(dict.fromkeys(id_links))

    tbody = re.search(r"<tbody[^>]*>(.*?)</tbody>", html, re.DOTALL)
    if not tbody:
        return []

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1), re.DOTALL)

    players = []
    for i, row in enumerate(rows):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) < 3:
            continue
        pid = player_ids[i] if i < len(player_ids) else None
        name_cn = re.sub(r"<[^>]+>", "", cells[1]).strip() if len(cells) > 1 else ""
        goals_raw = re.sub(r"<[^>]+>", "", cells[3]).strip() if len(cells) > 3 else "0"
        goals = _parse_int(goals_raw)
        if pid and name_cn:
            players.append({"player_id": pid, "name_cn": name_cn, "goals": goals})
    return players


def scrape_player_detail(player_id: str) -> dict | None:
    """Scrape player detail page for English name."""
    url = f"https://pc.dongqiudi.com/player/{player_id}"
    resp = client.get(url)
    html = resp.text
    m = re.search(r'class="pp-hero__en"[^>]*>([^<]+)<', html)
    if not m:
        return None
    return {"en_name": m.group(1).strip()}


def match_player(en_name: str, db_session) -> Player | None:
    if not en_name or len(en_name) < 2:
        return None
    player = db_session.query(Player).filter(Player.name == en_name).first()
    if player:
        return player
    parts = en_name.split()
    if parts:
        last = parts[-1]
        candidates = db_session.query(Player).filter(Player.name.ilike(f"%{last}%")).all()
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1 and len(parts) > 1:
            first = parts[0]
            for c in candidates:
                if first.lower() in c.name.lower():
                    return c
    return None


def save_stats(player: Player, goals: int, competition: str, db_session):
    existing = db_session.query(PlayerSeasonStats).filter(
        PlayerSeasonStats.player_id == player.id,
        PlayerSeasonStats.season == SEASON,
        PlayerSeasonStats.competition_code == competition,
    ).first()
    if existing:
        existing.goals = max(existing.goals, goals)
    else:
        s = PlayerSeasonStats(
            player_id=player.id, season=SEASON,
            competition_code=competition, goals=goals,
            source="dongqiudi",
        )
        db_session.add(s)
    db_session.commit()


def save_scraped(item: dict, detail: dict, competition: str,
                 player: Player | None, db_session):
    """Save raw scraped data to scraped_data table."""
    s = ScrapedPlayerData(
        dongqiudi_player_id=int(item["player_id"]),
        dongqiudi_url=f"https://pc.dongqiudi.com/player/{item['player_id']}",
        source_league_code=competition,
        name_cn=item.get("name_cn", ""),
        name_en=detail.get("en_name", ""),
        goals=item.get("goals", 0),
        matched_player_id=player.id if player else None,
        match_method="en_name" if player else None,
    )
    db_session.add(s)
    db_session.commit()


def scrape_league(cid: int, db_session) -> dict:
    """Scrape one league: listing + individual player pages."""
    competition = {v: k for k, v in LEAGUE_CID.items()}.get(cid, f"cid_{cid}")
    listing = scrape_listing(cid)
    if not listing:
        return {"competition": competition, "cid": cid, "error": "empty listing"}

    matched = 0
    total = len(listing)

    for item in listing:
        try:
            detail = scrape_player_detail(item["player_id"])
        except Exception:
            logger.warning("Failed to scrape player detail for player_id=%s", item.get("player_id"), exc_info=True)
            continue
        if not detail:
            continue

        player = match_player(detail["en_name"], db_session)

        # Always save raw scraped data
        save_scraped(item, detail, competition, player, db_session)

        if player:
            save_stats(player, item["goals"], competition, db_session)
            matched += 1

        time.sleep(DELAY_BETWEEN_PLAYERS)

    return {"competition": competition, "cid": cid,
            "listing_total": total, "matched": matched, "scraped_saved": total}


def scrape_all_leagues(db_session) -> list[dict]:
    results = []
    for league_code, cid in LEAGUE_CID.items():
        r = scrape_league(cid, db_session)
        results.append(r)
        time.sleep(DELAY_BETWEEN_LEAGUES)
    return results
