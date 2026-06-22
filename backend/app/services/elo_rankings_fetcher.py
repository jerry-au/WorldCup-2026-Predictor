"""Elo Rankings fetcher from eloratings.net.

Fetches the World.tsv data file which contains Elo ratings for all national teams.
Updates Team.elo_rating and Team.fifa_rank (Elo-based world rank) in the database.

Data source: https://eloratings.net/World.tsv
Format: TSV with columns: local_rank, global_rank, team_code, elo_rating, ...
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from ..models.team import Team

ELO_RATINGS_URL = "https://eloratings.net/World.tsv"

# eloratings.net 2-letter team codes -> our DB 3-letter FIFA codes
# Only for codes that differ between the two systems
CODE_MAP = {
    "EN": "ENG",   # England
    "ES": "ESP",   # Spain
    "FR": "FRA",   # France
    "BR": "BRA",   # Brazil
    "PT": "POR",   # Portugal
    "DE": "GER",   # Germany
    "NL": "NED",   # Netherlands
    "AR": "ARG",   # Argentina
    "IT": "ITA",   # Italy
    "CR": "CRC",   # Costa Rica
    "IR": "IRN",   # Iran
    "SN": "SEN",   # Senegal
    "MA": "MAR",   # Morocco
    "TN": "TUN",   # Tunisia
    "EG": "EGY",   # Egypt
    "CI": "CIV",   # Ivory Coast / Cote d'Ivoire
    "CM": "CMR",   # Cameroon
    "GH": "GHA",   # Ghana
    "NG": "NGA",   # Nigeria
    "CD": "COD",   # DR Congo
    "ZA": "RSA",   # South Africa
    "DZ": "ALG",   # Algeria
    "CF": "CPV",   # Cape Verde
    "US": "USA",   # United States
    "MX": "MEX",   # Mexico
    "CA": "CAN",   # Canada
    "NO": "NOR",   # Norway
    "QA": "QAT",   # Qatar
    "CW": "CUW",   # Curaçao
    "UY": "URU",   # Uruguay
    "BA": "BIH",   # Bosnia and Herzegovina
    "PA": "PAN",   # Panama
    "HT": "HAI",   # Haiti
    "EC": "ECU",   # Ecuador
    "CO": "COL",   # Colombia
    "PE": "PER",   # Peru
    "PY": "PAR",   # Paraguay
    "CL": "CHI",   # Chile
    "JP": "JPN",   # Japan
    "KR": "KOR",   # South Korea
    "AU": "AUS",   # Australia
    "NZ": "NZL",   # New Zealand
    "IQ": "IRQ",   # Iraq
    "SA": "KSA",   # Saudi Arabia
    "JO": "JOR",   # Jordan
    "UZ": "UZB",   # Uzbekistan
    "AT": "AUT",   # Austria
    "BE": "BEL",   # Belgium
    "HR": "CRO",   # Croatia
    "CZ": "CZE",   # Czechia
    "DK": "DEN",   # Denmark
    "HU": "HUN",   # Hungary
    "PL": "POL",   # Poland
    "RU": "RUS",   # Russia
    "RS": "SRB",   # Serbia
    "SK": "SVK",   # Slovakia
    "SE": "SWE",   # Sweden
    "CH": "SUI",   # Switzerland
    "TR": "TUR",   # Turkey
    "UA": "UKR",   # Ukraine
    "SCO": "SCO",  # Scotland
    "BIH": "BIH",  # Bosnia and Herzegovina
    "SQ": "SCO",   # Scotland (eloratings uses SQ for Scotland)
}


def fetch_elo_rankings(client: httpx.Client | None = None) -> list[dict]:
    """Fetch Elo rankings from eloratings.net World.tsv.

    Returns a list of { rank, team_code, elo_rating } dicts.
    The TSV format has columns:
      [0] local_rank  [1] global_rank  [2] team_code  [3] elo_rating  ...
    """
    close_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        resp = client.get(
            ELO_RATINGS_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/tab-separated-values, text/plain",
            },
        )
        resp.raise_for_status()

        entries = []
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) < 4:
                continue

            try:
                rank = int(fields[1])
                code = fields[2].strip()
                rating = float(fields[3])
            except (ValueError, IndexError):
                continue

            if code and rating > 0:
                entries.append({
                    "rank": rank,
                    "team_code": code,
                    "elo_rating": rating,
                })

        return entries
    except Exception as e:
        print(f"[EloRankings] Failed to fetch: {e}")
        return []
    finally:
        if close_client:
            client.close()


def match_team(db: Session, elo_code: str) -> Team | None:
    """Match an eloratings.net 2-letter team code to a Team in our database.

    Uses CODE_MAP for known mappings, then falls back to direct code/name matching.
    """
    # Try code mapping first
    mapped_code = CODE_MAP.get(elo_code.upper())

    if mapped_code:
        team = db.query(Team).filter(Team.code == mapped_code).first()
        if team:
            return team

    # Try direct code match (uppercased 2-letter -> 3-letter may match some)
    team = db.query(Team).filter(Team.code == elo_code.upper()).first()
    if team:
        return team

    return None


def fetch_and_update_elo(db: Session) -> dict:
    """Fetch latest Elo rankings and update Team.elo_rating + Team.fifa_rank.

    The fifa_rank field stores the Elo-based world rank position from eloratings.net,
    giving us a single authoritative ranking source for both values.
    """
    rankings = fetch_elo_rankings()

    if not rankings:
        return {
            "source": "eloratings",
            "status": "error",
            "message": "Could not fetch Elo rankings from eloratings.net/World.tsv",
            "teams_updated": 0,
        }

    updated = 0
    matched_teams: list[str] = []
    unmatched_codes: list[str] = []
    errors: list[dict] = []

    for entry in rankings:
        try:
            team = match_team(db, entry["team_code"])
            if team:
                old_elo = team.elo_rating
                old_rank = team.fifa_rank
                team.elo_rating = entry["elo_rating"]
                team.fifa_rank = entry["rank"]
                matched_teams.append(
                    f"{team.code}(Elo:{entry['elo_rating']},#{entry['rank']})"
                )
                updated += 1
            else:
                unmatched_codes.append(entry["team_code"])
        except Exception as exc:
            errors.append({"code": entry["team_code"], "error": str(exc)})

    if updated > 0:
        db.commit()

    return {
        "source": "eloratings",
        "status": "ok" if not errors else "partial",
        "rankings_found": len(rankings),
        "teams_updated": updated,
        "matched_teams": matched_teams,
        "unmatched_codes": list(set(unmatched_codes))[:20],
        "errors": errors,
    }
