"""以法国队为例，完整展示球队实力分的计算过程。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.team import Team
from app.models.dongqiudi_data import DongqiudiTeamData, DongqiudiPlayerData
from app.models.player_ability import DongqiudiPlayerAbility
from app.core.elo import composite_rating

db = SessionLocal()

# 1. 查找法国队
fra = db.query(Team).filter(Team.code == "FRA").first()
print("=" * 70)
print(f"球队: {fra.name_cn} ({fra.code})")
print(f"Elo 评分: {fra.elo_rating}")
print(f"FIFA 排名: {fra.fifa_rank}")
print(f"身价: {fra.market_value_eur / 1e6:.0f}M EUR")
print()

# 2. 找到法国队在懂球帝中的数据
dqd_team = db.query(DongqiudiTeamData).filter(DongqiudiTeamData.matched_team_id == fra.id).first()
print(f"懂球帝匹配: {dqd_team.name_cn} (team_id={dqd_team.id})")

# 3. 获取该队所有球员
players = (
    db.query(DongqiudiPlayerData)
    .filter(DongqiudiPlayerData.dongqiudi_team_data_id == dqd_team.id)
    .all()
)
print(f"\n懂球帝球员数: {len(players)}")

# 4. 获取球员能力数据
abilities = (
    db.query(DongqiudiPlayerAbility)
    .join(DongqiudiPlayerData, DongqiudiPlayerAbility.dongqiudi_player_id == DongqiudiPlayerData.id)
    .filter(DongqiudiPlayerData.dongqiudi_team_data_id == dqd_team.id)
    .filter(DongqiudiPlayerAbility.overall > 0)
    .all()
)
print(f"有能力数据的球员: {len(abilities)}")

if abilities:
    print(f"\n{'='*70}")
    print("步骤一: 收集每名球员的 overall 能力评分 (FIFA 风格 0-99)")
    print(f"{'='*70}")
    print(f"\n{'序号':>4s} {'姓名':<20s} {'位置':<6s} {'Overall':>8s} {'权重':>8s} {'加权值':>10s}")
    print("-" * 65)

    weighted_sum = 0.0
    total_weight = 0.0
    for i, a in enumerate(abilities):
        pd = a.dongqiudi_player
        name = pd.person_name or "?"
        pos = a.registered_position or "-"
        ov = a.overall

        # 权重公式: weight = max(0.5, min(2.5, 1.0 + (overall - 70) / 30))
        raw_weight = 1.0 + (ov - 70) / 30.0
        weight = max(0.5, min(2.5, raw_weight))
        weighted_val = ov * weight

        weighted_sum += weighted_val
        total_weight += weight

        print(f"{i+1:>4d} {name:<20s} {pos:<6s} {ov:>8d} {weight:>8.2f} {weighted_val:>10.1f}")

    avg_strength = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

    print(f"\n{'='*70}")
    print("步骤二: 加权平均计算球队实力分")
    print(f"{'='*70}")
    print(f"  加权总和 = {weighted_sum:.1f}")
    print(f"  权重总和 = {total_weight:.2f}")
    print(f"  球队实力分 = {weighted_sum:.1f} / {total_weight:.2f} = **{avg_strength}**")
    print()

    # 5. 计算 composite rating
    print(f"{'='*70}")
    print("步骤三: 综合实力评分 composite_rating")
    print(f"{'='*70}")

    # Elo 部分
    elo_part = 0.6 * fra.elo_rating
    print(f"\n  [1] Elo 评分 (权重 60%)")
    print(f"      Elo = {fra.elo_rating}")
    print(f"      0.60 × {fra.elo_rating} = {elo_part:.1f}")

    # 懂球帝实力分部分
    strength_equiv = 1300 + avg_strength * 8
    strength_part = 0.3 * strength_equiv
    print(f"\n  [2] 懂球帝球队实力分 (权重 30%)")
    print(f"      实力分 = {avg_strength}")
    print(f"      缩放到 Elo 量级: 1300 + {avg_strength} × 8 = {strength_equiv:.1f}")
    print(f"      0.30 × {strength_equiv:.1f} = {strength_part:.1f}")

    # 身价部分
    mv_norm = fra.market_value_norm if hasattr(fra, 'market_value_norm') else 0.5
    value_equiv = mv_norm * 2000 if mv_norm else 1000
    value_part = 0.1 * value_equiv
    print(f"\n  [3] 球队身价 (权重 10%)")
    print(f"      身价归一化 ≈ {mv_norm}")
    print(f"      身价等效值 = {value_equiv:.1f}")
    print(f"      0.10 × {value_equiv:.1f} = {value_part:.1f}")

    composite = composite_rating(elo=fra.elo_rating, dongqiudi_strength=avg_strength, market_value_norm=mv_norm)

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  综合实力分 Composite = {composite:.1f}     │")
    print(f"  │  = {elo_part:.1f} + {strength_part:.1f} + {value_part:.1f}        │")
    print(f"  └─────────────────────────────────────┘")

else:
    print("\n⚠️ 法国队暂无球员能力数据 (DongqiudiPlayerAbility 表为空)")
    print(f"\n  fallback 实力分 = 50.0 (默认中等水平)")

    composite_fallback = composite_rating(elo=fra.elo_rating, dongqiudi_strength=None)
    print(f"\n  综合实力分 (fallback) = {composite_fallback:.1f}")
    print(f"  = 0.60×{fra.elo_rating} + 0.30×1500 + 0.10×1000")

db.close()
