"""Dongqiudi national-team roster scraper.

Uses the official-like member_v2 endpoint behind pc.dongqiudi.com team pages.
Keeps Dongqiudi data in dedicated tables and links to core Zafronix players
by national team + jersey number.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models.team import Team
from ..models.player import Player
from ..models.dongqiudi_data import (
    DongqiudiTeamData,
    DongqiudiCoachData,
    DongqiudiPlayerData,
)

WORLD_CUP_CID = 61
STANDINGS_URL = "https://pc.dongqiudi.com/data?cid=61&tab=standings"
MEMBER_V2_URL = "https://pc.dongqiudi.com/sport-data/soccer/biz/dqd/v1/team/member_v2/{team_id}"
BASE_URL = "https://pc.dongqiudi.com"
REQUEST_DELAY = 0.5

# Mapping extracted from Dongqiudi World Cup standings page.
DONGQIUDI_TEAM_ID_TO_CODE = {
    "1278": "MEX", "1181": "KOR", "1753": "RSA", "453": "CZE",
    "303": "CAN", "1931": "SUI", "1542": "QAT", "219": "BIH",
    "269": "BRA", "1289": "MAR", "1683": "SCO", "916": "HAI",
    "2008": "USA", "87": "AUS", "1405": "PAR", "1977": "TUR",
    "868": "GER", "510": "ECU", "454": "CIV", "1332": "CUW",
    "1331": "NED", "1146": "JPN", "1941": "TUN", "1904": "SWE",
    "203": "BEL", "986": "IRN", "511": "EGY", "1341": "NZL",
    "1869": "ESP", "2026": "URU", "1640": "KSA", "304": "CPV",
    "789": "FRA", "1684": "SEN", "1389": "NOR", "987": "IRQ",
    "67": "ARG", "108": "AUT", "13": "ALG", "1147": "JOR",
    "1540": "POR", "364": "COL", "2027": "UZB", "366": "COD",
    "627": "ENG", "396": "CRO", "1393": "PAN", "869": "GHA",
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _to_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(str(value).replace("岁", "").strip())
    except (ValueError, TypeError):
        return None


DIACRITIC_MAP = {
    'ć': 'c', 'č': 'c', 'ç': 'c',
    'š': 's',
    'ž': 'z',
    'đ': 'd',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
    'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
    'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
    'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
    'ý': 'y',
    'ñ': 'n',
    'ł': 'l',
    # Japanese macrons
    'ō': 'o',  # o with macron
    'ū': 'u',  # u with macron
    'ā': 'a',  # a with macron
    'ē': 'e',  # e with macron
    'ī': 'i',  # i with macron
    'ğ': 'g',
}


def normalize_diacritics(name: str | None) -> str | None:
    if not name:
        return name
    result = []
    for ch in name:
        result.append(DIACRITIC_MAP.get(ch, ch))
    return ''.join(result)


def try_name_reversal(name: str) -> str | None:
    """Reverse 'Given Family' -> 'Family Given' for East Asian names."""
    if not name or ' ' not in name.strip():
        return None
    parts = name.strip().split()
    if len(parts) != 2:
        return None
    # Only reverse if given name contains a hyphen (e.g. Heung-min, Kang-in)
    if '-' in parts[0]:
        return f'{parts[1]} {parts[0]}'
    return None


def extract_standings_teams(html: str) -> list[dict]:
    """Extract unique national team links from Dongqiudi WC standings HTML."""
    matches = re.findall(r'href=["\'](/team/(\d+))["\'][^>]*>([^<]+)<', html)
    seen: set[str] = set()
    teams: list[dict] = []

    for path, team_id, name_cn in matches:
        if team_id in seen:
            continue
        seen.add(team_id)
        teams.append({
            "dongqiudi_team_id": team_id,
            "name_cn": name_cn.strip(),
            "team_url": f"{BASE_URL}{path}",
        })

    return teams


def parse_statistics(statistic: list[dict] | None) -> dict:
    """Normalize Dongqiudi statistic list to a dictionary."""
    result: dict = {}
    for item in statistic or []:
        if isinstance(item, dict):
            result.update(item)
    return result


def build_profile_url(person_id: str | None) -> str | None:
    if not person_id:
        return None
    return f"{BASE_URL}/player/{person_id}"


def parse_team_members(team_id: str, payload: dict) -> dict:
    """Parse member_v2 response into normalized coaches/players."""
    if payload.get("code") != 0:
        raise RuntimeError(f"Dongqiudi member_v2 returned error: {payload}")

    groups = payload.get("data", {}).get("list", [])
    parsed = {"dongqiudi_team_id": str(team_id), "coaches": [], "players": [], "raw_data": payload}

    for group in groups:
        group_title = group.get("title")
        group_type = group.get("type")
        people = group.get("data", []) or []

        for person in people:
            person_id = str(person.get("person_id") or "")
            stats = parse_statistics(person.get("statistic"))

            if group_type == "coach":
                parsed["coaches"].append({
                    "person_id": person_id,
                    "person_name": person.get("person_name"),
                    "person_logo": person.get("person_logo"),
                    "age_text": person.get("age"),
                    "nationality_name": person.get("nationality_name"),
                    "role_type": person.get("type"),
                    "scheme": person.get("scheme"),
                    "profile_url": build_profile_url(person_id),
                    "raw_data": person,
                })
            else:
                parsed["players"].append({
                    "person_id": person_id,
                    "person_name": person.get("person_name"),
                    "person_en_name": person.get("person_en_name"),
                    "person_logo": person.get("person_logo"),
                    "jersey_number": _to_int(person.get("shirtnumber")),
                    "age_text": person.get("age"),
                    "club_name_cn": person.get("nationality_name"),
                    "position_group": group_title,
                    "position_type": group_type,
                    "weekly_salary": person.get("weekly_salary"),
                    "appearances": _to_int(stats.get("出场")) or 0,
                    "goals": _to_int(stats.get("进球")) or 0,
                    "assists": _to_int(stats.get("助攻")) or 0,
                    "market_value_text": stats.get("身价(欧)"),
                    "scheme": person.get("scheme"),
                    "profile_url": build_profile_url(person_id),
                    "stats_raw": stats,
                    "raw_data": person,
                })

    return parsed


def member_headers(team_id: str) -> dict:
    return {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/team/{team_id}",
        "Accept": "application/json,text/plain,*/*",
    }


def fetch_standings_html(client: httpx.Client | None = None) -> str:
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(STANDINGS_URL, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    finally:
        if close_client:
            client.close()


def fetch_member_v2(team_id: str, client: httpx.Client | None = None) -> dict:
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(
            MEMBER_V2_URL.format(team_id=team_id),
            params={"app": "dqd"},
            headers=member_headers(team_id),
        )
        resp.raise_for_status()
        return resp.json()
    finally:
        if close_client:
            client.close()


def match_player_by_team_and_jersey(
    db: Session, core_team_id: int | None, jersey_number: int | None
) -> tuple[Player | None, str, float]:
    """Match Dongqiudi player to core Zafronix player by team + jersey."""
    if not core_team_id or jersey_number is None:
        return None, "missing_team_or_jersey", 0.0

    matches = (
        db.query(Player)
        .filter(Player.team_id == core_team_id, Player.jersey == jersey_number)
        .all()
    )
    if len(matches) == 1:
        return matches[0], "team_jersey", 1.0
    if len(matches) > 1:
        return None, "ambiguous_team_jersey", 0.0
    return None, "no_team_jersey_match", 0.0


def match_player_by_team_and_name(
    db: Session, core_team_id: int | None, en_name: str | None
) -> tuple[Player | None, str, float]:
    """Match Dongqiudi player to core Zafronix player by team + English name.
    Tries name variants: original, diacritic-normalized, reversed (East Asian), and combos.
    Both search term and DB values are normalized for comparison."""
    if not core_team_id or not en_name:
        return None, "missing_team_or_name", 0.0

    # Build search variants
    raw = en_name.strip().lower()
    candidates = [raw]
    norm = normalize_diacritics(raw)
    if norm != raw:
        candidates.append(norm)
    rev = try_name_reversal(en_name.strip())
    if rev:
        rl = rev.lower()
        candidates.append(rl)
        rn = normalize_diacritics(rl)
        if rn != rl:
            candidates.append(rn)

    # Get all players for this team, match in Python (to handle diacritics)
    team_players = db.query(Player).filter(Player.team_id == core_team_id).all()

    seen = set()
    for variant in candidates:
        if variant in seen:
            continue
        seen.add(variant)
        matched = []
        for p in team_players:
            p_norm = normalize_diacritics(p.name.lower())
            if variant in p_norm:
                matched.append(p)
        if len(matched) == 1:
            return matched[0], "team_en_name", 0.9
        if len(matched) > 1:
            exact = [p for p in matched if normalize_diacritics(p.name.lower()) == variant]
            if len(exact) == 1:
                return exact[0], "team_en_name", 0.95

    return None, "no_team_name_match", 0.0


def _core_team_for_dongqiudi(db: Session, dongqiudi_team_id: str) -> tuple[Team | None, str | None]:
    code = DONGQIUDI_TEAM_ID_TO_CODE.get(str(dongqiudi_team_id))
    if not code:
        return None, None
    return db.query(Team).filter(Team.code == code).first(), code


def upsert_dongqiudi_team(db: Session, team_info: dict, parsed_members: dict | None = None) -> DongqiudiTeamData:
    team_id = str(team_info["dongqiudi_team_id"])
    core_team, code = _core_team_for_dongqiudi(db, team_id)

    row = db.query(DongqiudiTeamData).filter(DongqiudiTeamData.dongqiudi_team_id == team_id).first()
    if not row:
        row = DongqiudiTeamData(dongqiudi_team_id=team_id)
        db.add(row)

    row.team_url = team_info.get("team_url") or f"{BASE_URL}/team/{team_id}"
    row.name_cn = team_info.get("name_cn")
    row.name_en = core_team.name if core_team else None
    row.matched_team_id = core_team.id if core_team else None
    row.matched_team_code = code
    row.match_method = "configured_team_code_map" if core_team else "unmapped_team"
    row.raw_data = _json_dumps({"team_info": team_info, "members": parsed_members or {}})
    db.commit()
    db.refresh(row)
    return row


def upsert_dongqiudi_coaches(db: Session, dqd_team: DongqiudiTeamData, coaches: list[dict]) -> int:
    saved = 0
    for coach in coaches:
        row = (
            db.query(DongqiudiCoachData)
            .filter(
                DongqiudiCoachData.dongqiudi_team_data_id == dqd_team.id,
                DongqiudiCoachData.person_id == coach["person_id"],
                DongqiudiCoachData.role_type == coach.get("role_type"),
            )
            .first()
        )
        if not row:
            row = DongqiudiCoachData(
                dongqiudi_team_data_id=dqd_team.id,
                person_id=coach["person_id"],
            )
            db.add(row)
        row.person_name = coach.get("person_name")
        row.person_logo = coach.get("person_logo")
        row.age_text = coach.get("age_text")
        row.nationality_name = coach.get("nationality_name")
        row.role_type = coach.get("role_type")
        row.scheme = coach.get("scheme")
        row.profile_url = coach.get("profile_url")
        row.raw_data = _json_dumps(coach.get("raw_data", coach))
        saved += 1
    db.commit()
    return saved


def upsert_dongqiudi_players(db: Session, dqd_team: DongqiudiTeamData, players: list[dict]) -> tuple[int, int]:
    saved = 0
    matched = 0
    for player_data in players:
        # Primary: team + jersey
        matched_player, method, confidence = match_player_by_team_and_jersey(
            db, dqd_team.matched_team_id, player_data.get("jersey_number")
        )
        # Fallback: team + English name
        if not matched_player and player_data.get("person_en_name"):
            alt_player, alt_method, alt_confidence = match_player_by_team_and_name(
                db, dqd_team.matched_team_id, player_data.get("person_en_name")
            )
            if alt_player:
                matched_player, method, confidence = alt_player, alt_method, alt_confidence
        if not matched_player:
            matched_player, method, confidence = None, "not_matched", 0.0
        if matched_player:
            matched += 1

        row = (
            db.query(DongqiudiPlayerData)
            .filter(
                DongqiudiPlayerData.dongqiudi_team_data_id == dqd_team.id,
                DongqiudiPlayerData.person_id == player_data["person_id"],
            )
            .first()
        )
        if not row:
            row = DongqiudiPlayerData(
                dongqiudi_team_data_id=dqd_team.id,
                person_id=player_data["person_id"],
            )
            db.add(row)

        row.person_name = player_data.get("person_name")
        row.person_en_name = player_data.get("person_en_name")
        row.person_logo = player_data.get("person_logo")
        row.jersey_number = player_data.get("jersey_number")
        row.age_text = player_data.get("age_text")
        row.club_name_cn = player_data.get("club_name_cn")
        row.position_group = player_data.get("position_group")
        row.position_type = player_data.get("position_type")
        row.weekly_salary = player_data.get("weekly_salary")
        row.appearances = player_data.get("appearances", 0)
        row.goals = player_data.get("goals", 0)
        row.assists = player_data.get("assists", 0)
        row.market_value_text = player_data.get("market_value_text")
        row.scheme = player_data.get("scheme")
        row.profile_url = player_data.get("profile_url")
        row.stats_raw = _json_dumps(player_data.get("stats_raw", {}))
        row.raw_data = _json_dumps(player_data.get("raw_data", player_data))
        row.matched_player_id = matched_player.id if matched_player else None
        row.match_method = method
        row.match_confidence = confidence
        saved += 1
    db.commit()
    return saved, matched


def scrape_all_national_rosters(db: Session) -> dict:
    """Fetch standings, scrape every national roster, and persist it."""
    errors: list[dict] = []
    teams_scraped = 0
    coaches_saved = 0
    players_saved = 0
    players_matched = 0

    with httpx.Client(timeout=15.0) as client:
        html = fetch_standings_html(client)
        teams = extract_standings_teams(html)

        for team_info in teams:
            team_id = team_info["dongqiudi_team_id"]
            try:
                payload = fetch_member_v2(team_id, client)
                parsed = parse_team_members(team_id, payload)
                dqd_team = upsert_dongqiudi_team(db, team_info, parsed)
                coaches_saved += upsert_dongqiudi_coaches(db, dqd_team, parsed["coaches"])
                saved, matched = upsert_dongqiudi_players(db, dqd_team, parsed["players"])
                players_saved += saved
                players_matched += matched
                teams_scraped += 1
                time.sleep(REQUEST_DELAY)
            except Exception as exc:
                errors.append({"team_id": team_id, "error": str(exc)})

    return {
        "teams_found": len(teams),
        "teams_scraped": teams_scraped,
        "coaches_saved": coaches_saved,
        "players_saved": players_saved,
        "players_matched": players_matched,
        "errors": errors,
    }
