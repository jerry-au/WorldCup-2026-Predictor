"""Apply manual coach matching rules.

Usage:
    1. Edit coach_matches.csv (remove # for confirmed lines)
    2. Run: python3 seed_data/apply_coach_matches.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, init_db
from app.models.dongqiudi_data import DongqiudiTeamData, DongqiudiCoachData
from app.models.team import Team


def apply():
    init_db()
    db = SessionLocal()
    path = os.path.join(os.path.dirname(__file__), "coach_matches.csv")
    applied = 0

    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 3:
                continue

            cn_name, en_name, team_code = [c.strip() for c in row]

            dqd_team = db.query(DongqiudiTeamData).filter(
                DongqiudiTeamData.matched_team_code == team_code
            ).first()
            if not dqd_team:
                print(f"  SKIP: Dongqiudi team {team_code} not found")
                continue

            coach = db.query(DongqiudiCoachData).filter(
                DongqiudiCoachData.dongqiudi_team_data_id == dqd_team.id,
                DongqiudiCoachData.person_name == cn_name,
                DongqiudiCoachData.role_type == "主教练",
            ).first()

            if not coach:
                print(f"  SKIP: Coach \"{cn_name}\" not found in {team_code}")
                continue

            coach.match_method = "manual"
            coach.matched_coach_name = en_name
            db.commit()
            applied += 1
            print(f"  OK: [{team_code}] {cn_name} -> {en_name}")

    db.close()
    print(f"\nApplied {applied} coach matches.")


if __name__ == "__main__":
    apply()
