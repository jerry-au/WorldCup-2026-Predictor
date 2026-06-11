"""Seed core Team/Player tables from Dongqiudi.

This is the primary seed script. It replaces import_teams.py (Zafronix JSON source).

Strategy:
  1. Fetch Dongqiudi standings page → extract all 48 team IDs + Chinese names
  2. Fetch each team's member_v2 API → parse squad (players + coaches)
  3. Create/update Team records (code, name, group, confederation, Elo, coach)
  4. Create/update Player records (name, jersey, position, club)
  5. Also populate DongqiudiTeamData/CoachData/PlayerData for cross-linking

Position mapping (Chinese → standard):
  门将 → GK, 后卫 → DF, 中场 → MF, 前锋 → FW

Elo ratings are seeded from historical power rankings (kept from existing seed).
Group info comes from standings data.
Confederation is determined by team code.
Market value is computed dynamically by the API — not stored here.

Usage:
    cd backend
    python seed_data/seed_from_dongqiudi.py
"""

import os
import sys
import time
import random
import re
from datetime import date
from typing import Any

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db, SessionLocal
from app.models.team import Team
from app.models.player import Player
from app.models.dongqiudi_data import DongqiudiTeamData, DongqiudiCoachData, DongqiudiPlayerData

# ── Constants ───────────────────────────────────────────────────────

STANDINGS_URL = "https://pc.dongqiudi.com/data?cid=61&tab=standings"
BASE_URL = "https://pc.dongqiudi.com"
MEMBER_V2_URL = "https://pc.dongqiudi.com/sport-data/soccer/biz/dqd/v1/team/member_v2/{team_id}"

BASE_DELAY = 0.5  # seconds between API calls
DELAY_JITTER = 0.2  # ±jitter

# Dongqiudi team ID → code mapping (48 teams)
# IDs extracted from dongqiudi standings page: https://pc.dongqiudi.com/data?cid=61&tab=standings
DONGQIUDI_TEAM_ID_TO_CODE: dict[str, str] = {
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
    "627": "ENG", "396": "CRO", "1393": "PAN", "1969": "GHA",
}

# Position Chinese → English mapping
POSITION_MAP: dict[str, str] = {
    "门将": "GK",
    "后卫": "DF",
    "中场": "MF",
    "前锋": "FW",
}

# Confederation mapping by team code
CONFEDERATION_MAP: dict[str, str] = {
    # AFC
    "AUS": "AFC", "JPN": "AFC", "KOR": "AFC", "IRN": "AFC",
    "IRQ": "AFC", "JOR": "AFC", "QAT": "AFC", "KSA": "AFC",
    "UZB": "AFC",
    # CAF
    "ALG": "CAF", "CPV": "CAF", "CMR": "CAF", "EGY": "CAF",
    "GHA": "CAF", "CIV": "CAF", "MAR": "CAF", "RSA": "CAF",
    "SEN": "CAF", "TUN": "CAF", "COD": "CAF",
    # CONCACAF
    "CAN": "CONCACAF", "CRC": "CONCACAF", "HAI": "CONCACAF",
    "MEX": "CONCACAF", "PAN": "CONCACAF", "USA": "CONCACAF",
    "CUW": "CONCACAF",
    # CONMEBOL
    "ARG": "CONMEBOL", "BRA": "CONMEBOL", "COL": "CONMEBOL",
    "ECU": "CONMEBOL", "PAR": "CONMEBOL", "URU": "CONMEBOL",
    # OFC
    "NZL": "OFC",
    # UEFA
    "AUT": "UEFA", "BEL": "UEFA", "BIH": "UEFA", "CRO": "UEFA",
    "CZE": "UEFA", "ENG": "UEFA", "FRA": "UEFA", "GER": "UEFA",
    "NED": "UEFA", "NOR": "UEFA", "POR": "UEFA", "SCO": "UEFA",
    "ESP": "UEFA", "SWE": "UEFA", "SUI": "UEFA", "TUR": "UEFA",
    "UKR": "UEFA",
}

# Initial Elo ratings (based on historical power rankings)
ELO_SEED: dict[str, float] = {
    "ARG": 1825, "BRA": 1840, "FRA": 1850, "GER": 1760, "ENG": 1820,
    "ESP": 1835, "POR": 1750, "NED": 1740, "BEL": 1710, "CRO": 1700,
    "URU": 1680, "COL": 1660, "MAR": 1650, "JPN": 1620, "KOR": 1600,
    "MEX": 1610, "USA": 1600, "CAN": 1520, "SEN": 1640, "EGY": 1580,
    "TUN": 1550, "GHA": 1560, "CIV": 1590, "RSA": 1500, "COD": 1480,
    "CPV": 1450, "ALG": 1600, "IRN": 1580, "IRQ": 1460, "JOR": 1440,
    "QAT": 1500, "UZB": 1470, "AUS": 1550, "NZL": 1420, "CZE": 1600,
    "SWE": 1620, "NOR": 1680, "SUI": 1650, "BIH": 1540, "TUR": 1640,
    "AUT": 1590, "SCO": 1560, "PAR": 1520, "ECU": 1550, "PAN": 1460,
    "HAI": 1400,
}

# FIFA country codes → ISO 3166-1 alpha-2
ISO_MAP: dict[str, str] = {
    "ALG": "DZ", "ARG": "AR", "AUS": "AU", "AUT": "AT",
    "BEL": "BE", "BIH": "BA", "BRA": "BR",
    "CAN": "CA", "CPV": "CV", "CIV": "CI", "COL": "CO",
    "CRC": "CR", "CRO": "HR", "CUR": "CW", "CZE": "CZ",
    "ECU": "EC", "EGY": "EG", "ENG": "GB",
    "FRA": "FR",
    "GER": "DE", "GHA": "GH",
    "HAI": "HT",
    "IRN": "IR", "IRQ": "IQ",
    "JPN": "JP", "JOR": "JO",
    "KOR": "KR",
    "MAR": "MA", "MEX": "MX",
    "NED": "NL", "NZL": "NZ", "NOR": "NO",
    "PAN": "PA", "PAR": "PY", "POR": "PT",
    "QAT": "QA",
    "RSA": "ZA",
    "SCO": "GB-SCT", "SEN": "SN", "ESP": "ES", "SUI": "CH", "SWE": "SE",
    "TUN": "TN", "TUR": "TR",
    "URU": "UY", "USA": "US", "UZB": "UZ",
}

# Group assignment (12 groups × 4 teams, extracted from dongqiudi standings)
GROUP_MAP: dict[str, str] = {
    "MEX": "A", "KOR": "A", "RSA": "A", "CZE": "A",
    "CAN": "B", "SUI": "B", "QAT": "B", "BIH": "B",
    "BRA": "C", "MAR": "C", "SCO": "C", "HAI": "C",
    "USA": "D", "AUS": "D", "PAR": "D", "TUR": "D",
    "GER": "E", "ECU": "E", "CIV": "E", "CUW": "E",
    "NED": "F", "JPN": "F", "TUN": "F", "SWE": "F",
    "BEL": "G", "IRN": "G", "EGY": "G", "NZL": "G",
    "ESP": "H", "URU": "H", "KSA": "H", "CPV": "H",
    "FRA": "I", "SEN": "I", "NOR": "I", "IRQ": "I",
    "ARG": "J", "AUT": "J", "ALG": "J", "JOR": "J",
    "POR": "K", "COL": "K", "UZB": "K", "COD": "K",
    "ENG": "L", "CRO": "L", "PAN": "L", "GHA": "L",
}

# Flag URL pattern (using flagpedia)
FLAG_URL_TEMPLATE = "https://flagpedia.net/{iso}/small.png"

# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


# ── Helpers ────────────────────────────────────────────────────────

def _rate_limit():
    """Sleep with jitter to avoid triggering anti-scrape measures."""
    delay = BASE_DELAY + random.uniform(-DELAY_JITTER, DELAY_JITTER)
    time.sleep(max(0.1, delay))


def _random_headers(referer: str | None = None) -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": referer or "https://pc.dongqiudi.com/",
        "Origin": "https://pc.dongqiudi.com",
    }


def _to_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _parse_position(chinese_pos: str | None) -> str | None:
    """Map Chinese position label to standard abbreviation."""
    if not chinese_pos:
        return None
    for cn, en in POSITION_MAP.items():
        if cn in chinese_pos:
            return en
    return None


# ── Fetch standings → team list ───────────────────────────────────

def fetch_standings_teams(client: httpx.Client) -> list[dict]:
    """Fetch standings page and extract all team entries with group info."""
    resp = client.get(
        STANDINGS_URL,
        headers=_random_headers("https://pc.dongqiudi.com/"),
    )
    resp.raise_for_status()
    html = resp.text

    # Extract team links and group info
    teams: dict[str, dict] = {}

    # Approach 1: try __INITIAL_STATE__ JSON first
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if json_match:
        try:
            import json
            state = json.loads(json_match.group(1))
            standings_data = (
                state.get("standings")
                or state.get("data", {}).get("standings")
                or state.get("pageData", {}).get("standings")
                or []
            )
            if standings_data:
                for group in standings_data:
                    group_name = (
                        group.get("group_name") or group.get("group") or group.get("name", "")
                    ).strip()
                    entries = (
                        group.get("teams") or group.get("table")
                        or group.get("standings") or group.get("entries") or []
                    )
                    for entry in entries:
                        team_name = (
                            entry.get("team_name") or entry.get("name") or entry.get("team") or ""
                        )
                        # Extract team_id from team_url if available
                        team_url = entry.get("team_url") or ""
                        team_id_match = re.search(r'/team/(\d+)', str(team_url))
                        if not team_id_match:
                            continue
                        team_id = team_id_match.group(1)
                        if team_id not in teams:
                            teams[team_id] = {
                                "dongqiudi_team_id": team_id,
                                "name_cn": team_name.strip(),
                                "group": group_name.replace("Group ", "").replace("组", "").strip(),
                            }
            if teams:
                return list(teams.values())
        except (json.JSONDecodeError, AttributeError):
            pass

    # Approach 2: parse HTML for team links with group context
    # Find group sections
    group_sections = re.split(r'<div[^>]*class="[^"]*group[^"]*"[^>]*>', html)[1:]

    for section in group_sections:
        # Extract group letter
        group_m = re.search(r'<span[^>]*>([A-Z])</span>', section)
        group_letter = group_m.group(1) if group_m else ""

        # Extract team links
        for m in re.finditer(r'href=["\'](/team/(\d+))["\'][^>]*>([^<]+)<', section):
            team_id = m.group(2)
            name_cn = m.group(3).strip()
            if team_id not in teams:
                teams[team_id] = {
                    "dongqiudi_team_id": team_id,
                    "name_cn": name_cn,
                    "group": group_letter,
                }

    return list(teams.values())


# ── Fetch member_v2 → squad ───────────────────────────────────────

def fetch_member_v2(team_id: str, client: httpx.Client) -> dict:
    """Fetch national team roster from Dongqiudi member_v2 endpoint."""
    resp = client.get(
        MEMBER_V2_URL.format(team_id=team_id),
        params={"app": "dqd"},
        headers=_random_headers(f"{BASE_URL}/team/{team_id}"),
    )
    resp.raise_for_status()
    return resp.json()


def parse_squad(team_id: str, payload: dict) -> dict:
    """Parse member_v2 response into coaches and players lists."""
    if payload.get("code") != 0:
        raise RuntimeError(f"member_v2 returned error code: {payload.get('code')}")

    groups = payload.get("data", {}).get("list", [])
    result: dict[str, list[dict]] = {"coaches": [], "players": []}

    for group in groups:
        group_type = group.get("type")
        group_title = group.get("title")
        people = group.get("data", []) or []

        for person in people:
            person_id = str(person.get("person_id") or "")
            stats = person.get("statistic") or {}

            # Normalize statistic list to dict
            if isinstance(stats, list):
                stats = {s.get("key", k): s.get("value") for k, s in enumerate(stats) if isinstance(s, dict)}
            if not isinstance(stats, dict):
                stats = {}

            entry = {
                "person_id": person_id,
                "person_name": person.get("person_name"),
                "person_en_name": person.get("person_en_name"),
                "person_logo": person.get("person_logo"),
                "jersey_number": _to_int(person.get("shirtnumber")),
                "age_text": person.get("age"),
                "nationality_name": person.get("nationality_name"),
                "position_group": group_title,
                "position_type": group_type,
                "club_name": person.get("club"),
                "weekly_salary": person.get("weekly_salary"),
                "appearances": _to_int(stats.get("出场")) or 0,
                "goals": _to_int(stats.get("进球")) or 0,
                "assists": _to_int(stats.get("助攻")) or 0,
                "market_value_text": stats.get("身价(欧)"),
                "raw_data": person,
            }

            if group_type == "coach":
                result["coaches"].append(entry)
            else:
                result["players"].append(entry)

    return result


# ── Upsert core Team/Player records ───────────────────────────────

def upsert_team(db: SessionLocal, team_info: dict) -> Team | None:
    """Create or update a Team record from Dongqiudi data."""
    team_id = team_info["dongqiudi_team_id"]
    code = DONGQIUDI_TEAM_ID_TO_CODE.get(team_id)
    if not code:
        print(f"  ⚠ No code mapping for team ID {team_id} ({team_info.get('name_cn')}), skipping")
        return None

    group = team_info.get("group", "")
    conf = CONFEDERATION_MAP.get(code, "")
    iso = ISO_MAP.get(code, "")
    flag_url = FLAG_URL_TEMPLATE.format(iso=iso) if iso else ""

    # Check existing
    team = db.query(Team).filter(Team.code == code).first()
    if team:
        team.group_name = group
        team.confederation = conf
        team.iso = iso
        team.flag_url = flag_url
        if not team.elo_rating or team.elo_rating == 1500.0:
            team.elo_rating = ELO_SEED.get(code, 1500.0)
    else:
        team = Team(
            code=code,
            name=team_info.get("name_cn", code),
            iso=iso,
            confederation=conf,
            group_name=group,
            flag_url=flag_url,
            elo_rating=ELO_SEED.get(code, 1500.0),
            fifa_rank=0,
        )
        db.add(team)

    db.flush()

    if team and not team.name or team.name == code:
        team.name = team_info.get("name_cn", code)

    return team


def upsert_player(db: SessionLocal, team: Team, player_info: dict) -> Player | None:
    """Create or update a Player record from Dongqiudi data. Returns None if no valid name."""
    name = player_info.get("person_en_name") or player_info.get("person_name")
    if not name:
        return None

    jersey = player_info.get("jersey_number")
    position = _parse_position(player_info.get("position_group"))
    club = player_info.get("club_name") or player_info.get("nationality_name") or ""

    # Try to find existing player by team_id + jersey
    player = None
    if jersey is not None:
        player = (
            db.query(Player)
            .filter(Player.team_id == team.id, Player.jersey == jersey)
            .first()
        )

    # Fallback: try by name
    if not player:
        player = (
            db.query(Player)
            .filter(Player.team_id == team.id, Player.name == name)
            .first()
        )

    if player:
        player.name = name
        if jersey is not None:
            player.jersey = jersey
        if position:
            player.position = position
        if club:
            player.club_name = club
    else:
        player = Player(
            team_id=team.id,
            name=name,
            jersey=jersey,
            position=position,
            club_name=club,
            goals=player_info.get("goals", 0),
        )
        db.add(player)

    return player


def update_team_coach(db: SessionLocal, team: Team, coaches: list[dict]):
    """Update coach info on Team record from Dongqiudi coach data."""
    head_coach = None
    for coach in coaches:
        role = coach.get("position_type", "")
        if not head_coach or role == "head_coach":
            head_coach = coach

    if head_coach:
        team.coach_name = head_coach.get("person_name")
        team.coach_country = head_coach.get("nationality_name")


# ── Main seed function ─────────────────────────────────────────────

def seed_from_dongqiudi(dry_run: bool = False) -> dict:
    """Main seed function.

    Args:
        dry_run: If True, only print what would be done without writing to DB.

    Returns:
        dict with statistics about the seeding operation.
    """
    stats: dict = {
        "teams_found": 0,
        "teams_created": 0,
        "teams_updated": 0,
        "players_created": 0,
        "players_updated": 0,
        "errors": [],
    }

    db = SessionLocal()
    init_db()

    with httpx.Client(timeout=15.0) as client:
        # Step 1: Fetch standings → all teams
        print("📡 Fetching standings page...")
        try:
            teams_info = fetch_standings_teams(client)
        except Exception as e:
            print(f"  ⚠ Failed to fetch standings: {e}")
            teams_info = []

        stats["teams_found"] = len(teams_info)
        print(f"  Found {len(teams_info)} teams from standings page")

        # Fallback: use DONGQIUDI_TEAM_ID_TO_CODE + GROUP_MAP directly
        if not teams_info:
            print("  ⚠ Standings page parsing returned no teams, using hardcoded mapping...")
            teams_info = []
            for tid, code in DONGQIUDI_TEAM_ID_TO_CODE.items():
                teams_info.append({
                    "dongqiudi_team_id": tid,
                    "name_cn": "",
                    "group": GROUP_MAP.get(code, ""),
                })
            stats["teams_found"] = len(teams_info)
            print(f"  Using {len(teams_info)} teams from DONGQIUDI_TEAM_ID_TO_CODE")

        if dry_run:
            print("\n⚠ DRY RUN — no data will be written")

        # Step 2: Process each team
        for team_info in teams_info:
            team_id = team_info["dongqiudi_team_id"]
            name_cn = team_info.get("name_cn", "")
            code = DONGQIUDI_TEAM_ID_TO_CODE.get(team_id, "???")

            print(f"\n{'='*50}")
            print(f"📋 {code} ({team_info.get('group', '?')}) — {name_cn} [ID={team_id}]")
            print(f"{'='*50}")

            if code == "???":
                print(f"  ⚠ Unknown team ID {team_id}, skipping")
                stats["errors"].append({"team_id": team_id, "name_cn": name_cn, "error": "unknown_id"})
                continue

            # Fetch squad
            try:
                payload = fetch_member_v2(team_id, client)
                squad = parse_squad(team_id, payload)
            except Exception as e:
                print(f"  ❌ Failed to fetch squad: {e}")
                stats["errors"].append({"team_id": team_id, "name_cn": name_cn, "error": str(e)})
                _rate_limit()
                continue

            print(f"  Players: {len(squad['players'])}, Coaches: {len(squad['coaches'])}")

            if dry_run:
                _rate_limit()
                continue

            # Create/update Team
            team = upsert_team(db, team_info)
            if not team:
                _rate_limit()
                continue

            team_was_created = db.query(Team.id).filter(Team.id == team.id).scalar() == team.id
            # Check if newly created by seeing if it was just added (not committed yet)
            # A simpler approach: track via whether it was an insert vs update
            # We can check if the team was just created by examining the session
            is_new_team = team in db.new
            if is_new_team:
                stats["teams_created"] += 1
            else:
                stats["teams_updated"] += 1

            # Update coach info
            update_team_coach(db, team, squad["coaches"])

            # Create/update players
            for player_info in squad["players"]:
                player = upsert_player(db, team, player_info)
                if player:
                    is_new_player = player in db.new
                    if is_new_player:
                        stats["players_created"] += 1
                    else:
                        stats["players_updated"] += 1

            # Commit team + player changes now so FK constraints are satisfied
            db.commit()
            print(f"  ✅ Team + {len(squad['players'])} players committed")

            _rate_limit()

    # Step 3: Print summary
    print(f"\n{'='*50}")
    print("✅ SEED COMPLETE")
    print(f"{'='*50}")
    print(f"  Teams found:     {stats['teams_found']}")
    print(f"  Teams created:   {stats['teams_created']}")
    print(f"  Teams updated:   {stats['teams_updated']}")
    print(f"  Players created: {stats['players_created']}")
    print(f"  Players updated: {stats['players_updated']}")
    if stats["errors"]:
        print(f"  Errors:          {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"    - [{err.get('team_id')}] {err.get('error')}")

    db.close()
    return stats


# ── Standalone entry point ─────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed Team/Player tables from Dongqiudi")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to DB")
    args = parser.parse_args()

    print("🌍 World Cup 2026 — Seed from Dongqiudi")
    print("=" * 50)
    print(f"  Teams to process: {len(DONGQIUDI_TEAM_ID_TO_CODE)}")
    print(f"  Delay: {BASE_DELAY}s ±{DELAY_JITTER}s (anti-scrape)")
    print(f"  Dry run: {args.dry_run}")
    print()

    seed_from_dongqiudi(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
