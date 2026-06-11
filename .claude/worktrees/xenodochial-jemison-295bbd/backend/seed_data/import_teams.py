"""Import teams from Zafronix WC API data into the database."""

import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db, SessionLocal
from app.models.team import Team
from app.models.player import Player


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def import_teams(data_path: str = "../data/teams_2026.json"):
    """Load team data from Zafronix JSON and insert into the database."""
    with open(data_path, encoding="utf-8") as f:
        teams_data = json.load(f)

    session = SessionLocal()

    # Ensure tables exist
    init_db()

    # Assign initial Elo ratings based on traditional power rankings
    elo_seed = {
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

    imported = 0
    for t in teams_data:
        code = t["code"]
        group = t.get("groupStage", {}).get("group", "")

        team = Team(
            code=code,
            name=t["name"],
            iso=t.get("iso", ""),
            confederation=t.get("confederation", ""),
            group_name=group,
            flag_url=t.get("flag", {}).get("flagUrl", ""),
            coach_name=t.get("coach", {}).get("name", ""),
            coach_country=t.get("coach", {}).get("country", ""),
            elo_rating=elo_seed.get(code, 1500.0),
            fifa_rank=0,
        )
        session.add(team)
        session.flush()  # Get team.id

        # Import players
        for p in t.get("squad", []):
            player = Player(
                team_id=team.id,
                name=p["name"],
                jersey=p.get("jersey"),
                position=p.get("position"),
                age_at_tournament=p.get("ageAtTournament"),
                club_name=p.get("club", {}).get("name", ""),
                birth_date=parse_date(p.get("born")),
                club_country=p.get("club", {}).get("country", ""),
                is_captain=("captain" in p.get("name", "").lower()),
                goals=p.get("goals", 0),
            )
            session.add(player)

        imported += 1
        print(f"  [{code}] {t['name']} ({len(t.get('squad', []))} players)")

    session.commit()
    session.close()
    print(f"\nImported {imported} teams with squads.")


if __name__ == "__main__":
    import_teams()
