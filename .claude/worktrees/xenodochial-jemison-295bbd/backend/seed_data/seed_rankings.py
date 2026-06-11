"""Seed FIFA rankings and estimated market values for all 48 teams.

Runs as a one-time data migration. Replaces placeholder values (fifa_rank=0).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.team import Team
from app.models.player import Player

# Approximate FIFA World Rankings (May 2026, pre-World Cup)
# Higher = better, 1 is best
FIFA_RANKINGS = {
    "ARG": 1,   "FRA": 2,   "ESP": 3,   "ENG": 4,   "BRA": 5,
    "BEL": 6,   "POR": 7,   "NED": 8,   "GER": 9,   "CRO": 10,
    "URU": 11,  "COL": 12,  "MAR": 13,  "JPN": 14,  "SEN": 15,
    "SUI": 16,  "MEX": 17,  "USA": 18,  "IRN": 19,  "KOR": 20,
    "TUR": 21,  "SWE": 22,  "NOR": 23,  "ECU": 24,  "AUS": 25,
    "EGY": 26,  "TUN": 27,  "CIV": 28,  "UKR": 29,  "ALG": 30,
    "CZE": 31,  "AUT": 32,  "SCO": 33,  "GHA": 34,  "PAR": 35,
    "BIH": 36,  "PAN": 37,  "COD": 38,  "IRQ": 39,  "RSA": 40,
    "UZB": 41,  "JOR": 42,  "CAN": 43,  "CPV": 44,  "HAI": 45,
    "QAT": 46,  "NZL": 47,  "CUR": 48,  "KSA": 49,
}

# Estimated squad market values (EUR, in millions)
# Based on Transfermarkt estimates for 2026 WC squads
# Higher = more valuable squad
MARKET_VALUE_MEUR = {
    "ENG": 1520, "FRA": 1250, "ESP": 1120, "POR": 1050, "BRA": 980,
    "GER": 920,  "NED": 850,  "ARG": 820,  "BEL": 780,  "CRO": 650,
    "TUR": 620,  "NOR": 580,  "URU": 550,  "SCO": 520,  "COL": 500,
    "AUT": 480,  "SUI": 470,  "SWE": 450,  "MAR": 430,  "USA": 420,
    "SEN": 400,  "JPN": 380,  "EGY": 360,  "CZE": 350,  "MEX": 340,
    "KOR": 320,  "ECU": 310,  "IRN": 290,  "GHA": 280,  "AUS": 270,
    "TUN": 260,  "CIV": 250,  "PAR": 230,  "ALG": 220,  "BIH": 210,
    "CAN": 200,  "QAT": 190,  "RSA": 180,  "PAN": 160,  "COD": 150,
    "UZB": 140,  "JOR": 130,  "CPV": 110,  "IRQ": 100,  "HAI": 90,
    "NZL": 80,   "CUR": 65,  "KSA": 55,
}


def seed():
    db = SessionLocal()
    teams = db.query(Team).all()
    updated = 0
    for t in teams:
        rank = FIFA_RANKINGS.get(t.code)
        value = MARKET_VALUE_MEUR.get(t.code)
        if rank:
            t.fifa_rank = rank
        if value:
            t.market_value_eur = value
        updated += 1
    db.commit()
    db.close()
    print(f"Seeded rankings & values for {updated} teams.")


if __name__ == "__main__":
    seed()
