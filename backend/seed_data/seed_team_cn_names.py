"""Seed Chinese names (name_cn) for all 48 World Cup teams.

Usage:
    cd backend
    python seed_data/seed_team_cn_names.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.team import Team

# Chinese name mapping for all 48 teams (code → Chinese name)
CN_NAMES: dict[str, str] = {
    # Group A
    "MEX": "墨西哥", "KOR": "韩国", "RSA": "南非", "CZE": "捷克",
    # Group B
    "CAN": "加拿大", "SUI": "瑞士", "QAT": "卡塔尔", "BIH": "波黑",
    # Group C
    "BRA": "巴西", "MAR": "摩洛哥", "SCO": "苏格兰", "HAI": "海地",
    # Group D
    "USA": "美国", "AUS": "澳大利亚", "PAR": "巴拉圭", "TUR": "土耳其",
    # Group E
    "GER": "德国", "ECU": "厄瓜多尔", "CIV": "科特迪瓦", "CUW": "库拉索",
    # Group F
    "NED": "荷兰", "JPN": "日本", "TUN": "突尼斯", "SWE": "瑞典",
    # Group G
    "BEL": "比利时", "IRN": "伊朗", "EGY": "埃及", "NZL": "新西兰",
    # Group H
    "ESP": "西班牙", "URU": "乌拉圭", "KSA": "沙特阿拉伯", "CPV": "佛得角",
    # Group I
    "FRA": "法国", "SEN": "塞内加尔", "NOR": "挪威", "IRQ": "伊拉克",
    # Group J
    "ARG": "阿根廷", "AUT": "奥地利", "ALG": "阿尔及利亚", "JOR": "约旦",
    # Group K
    "POR": "葡萄牙", "COL": "哥伦比亚", "UZB": "乌兹别克斯坦", "COD": "刚果(金)",
    # Group L
    "ENG": "英格兰", "CRO": "克罗地亚", "PAN": "巴拿马", "GHA": "加纳",
}


def seed_cn_names():
    db = SessionLocal()
    try:
        teams = db.query(Team).all()
        updated = 0
        skipped = 0

        for team in teams:
            cn = CN_NAMES.get(team.code)
            if cn:
                team.name_cn = cn
                updated += 1
            else:
                skipped += 1
                print(f"  ⚠ No CN name for {team.code} ({team.name})")

        db.commit()
        print(f"\n✅ Updated {updated} teams with Chinese names")
        if skipped:
            print(f"  ⚠ {skipped} teams skipped (no mapping)")

    finally:
        db.close()


def main():
    print("🌍 Seeding Chinese team names...")
    print("=" * 40)
    seed_cn_names()


if __name__ == "__main__":
    main()
