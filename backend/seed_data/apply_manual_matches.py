"""Apply manual matching rules to fix remaining unmatched Dongqiudi players.

Usage:
    1. Edit manual_matches.csv to confirm mappings (remove # for confirmed)
    2. Run: python3 seed_data/apply_manual_matches.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.team import Team
from app.models.player import Player
from app.models.dongqiudi_data import DongqiudiTeamData, DongqiudiPlayerData


def apply():
    db = SessionLocal()
    path = os.path.join(os.path.dirname(__file__), "manual_matches.csv")
    applied = 0

    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            # Skip comments and empty lines
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 5:
                continue

            en_name, cn_name, jersey, team_code, zaf_name = [c.strip() for c in row]

            # Find the Zafronix player
            team = db.query(Team).filter(Team.code == team_code).first()
            if not team:
                print(f"  SKIP: Team {team_code} not found")
                continue

            player = db.query(Player).filter(
                Player.team_id == team.id, Player.name == zaf_name
            ).first()
            if not player:
                print(f"  SKIP: Zaf player \"{zaf_name}\" not found in {team_code}")
                continue

            # Find Dongqiudi player
            dqd_team = db.query(DongqiudiTeamData).filter(
                DongqiudiTeamData.matched_team_id == team.id
            ).first()
            if not dqd_team:
                print(f"  SKIP: Dongqiudi team not found for {team_code}")
                continue

            dqd_player = db.query(DongqiudiPlayerData).filter(
                DongqiudiPlayerData.dongqiudi_team_data_id == dqd_team.id,
                DongqiudiPlayerData.person_name == cn_name,
            ).first()

            if not dqd_player:
                # Try matching by English name
                dqd_player = db.query(DongqiudiPlayerData).filter(
                    DongqiudiPlayerData.dongqiudi_team_data_id == dqd_team.id,
                    DongqiudiPlayerData.person_en_name == en_name,
                ).first()

            if not dqd_player:
                print(f"  SKIP: DQD player \"{cn_name}\" not found in {team_code}")
                continue

            dqd_player.matched_player_id = player.id
            dqd_player.match_method = "manual"
            dqd_player.match_confidence = 1.0
            db.commit()
            applied += 1
            print(f"  OK: [{team_code}] {cn_name} (#{jersey}) -> {zaf_name}")

    db.close()
    print(f"\nApplied {applied} manual matches.")


if __name__ == "__main__":
    apply()
