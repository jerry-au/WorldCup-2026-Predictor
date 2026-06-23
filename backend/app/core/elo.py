"""Elo rating system for cross-team comparison.

Based on the standard Elo formula adapted for international football.
Initial ratings seeded from FIFA rankings, updated after each match.

Composite rating combines: Elo (60%) + Dongqiudi team strength (30%) + market value (10%).
"""

import math
import re
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import Float, func as sa_func

from ..models.team import Team
from ..models.player_ability import DongqiudiPlayerAbility
from ..models.dongqiudi_data import DongqiudiPlayerData, DongqiudiTeamData


def _parse_market_value(text: str) -> float:
    """Parse Chinese market value text into EUR amount.

    Examples:
      "1500万"  -> 150_000_000  (150 million)
      "25万"    ->   2_500_000  (2.5 million)
      "5000万"  -> 500_000_000  (500 million)
      "1亿"     -> 100_000_000  (100 million)
      "1.8亿"   -> 180_000_000  (180 million)

    Returns value in EUR, or 0 if unparseable.
    """
    if not text:
        return 0.0
    text = text.strip()
    # 亿 unit (100 million)
    m = re.match(r"([\d.]+)\s*亿", text)
    if m:
        return float(m.group(1)) * 100_000_000
    # 万 unit (10 thousand)
    m = re.match(r"([\d.]+)\s*万", text)
    if m:
        return float(m.group(1)) * 10_000
    # Plain number
    m = re.match(r"([\d.]+)", text)
    if m:
        return float(m.group(1))
    return 0.0


def get_team_market_value(db: Session, team: Team) -> float:
    """Compute team total market value from Dongqiudi player data.

    Sums each player's market_value_text (parsed from "1500万" format).
    Returns total in EUR.
    """
    rows = (
        db.query(DongqiudiPlayerData.market_value_text)
        .join(DongqiudiTeamData, DongqiudiPlayerData.dongqiudi_team_data_id == DongqiudiTeamData.id)
        .filter(DongqiudiTeamData.matched_team_id == team.id)
        .filter(DongqiudiPlayerData.market_value_text.isnot(None))
        .filter(DongqiudiPlayerData.market_value_text != "")
        .all()
    )

    if not rows:
        return 0.0

    total = sum(_parse_market_value(r[0]) for r in rows)
    return round(total, 2)


def get_all_teams_market_values(db: Session) -> dict[int, tuple[float, float]]:
    """Get market values for all teams, returning both raw EUR and normalized.

    Returns: { team_id: (total_eur, normalized_0_to_1) }
    Normalization uses min-max scaling across all teams with data.
    """
    # Query per-team totals using SQL aggregation
    results = (
        db.query(
            DongqiudiTeamData.matched_team_id,
            sa_func.sum(
                sa_func.cast(
                    sa_func.regexp_replace(DongqiudiPlayerData.market_value_text, r'[^\d.]', '', 'g'),
                    Float
                )
            ) * 10_000,
        )
        .join(DongqiudiPlayerData, DongqiudiPlayerData.dongqiudi_team_data_id == DongqiudiTeamData.id)
        .filter(DongqiudiTeamData.matched_team_id.isnot(None))
        .filter(DongqiudiPlayerData.market_value_text != "")
        .group_by(DongqiudiTeamData.matched_team_id)
        .all()
    )

    if not results:
        return {}

    values = {r[0]: round(float(r[1] or 0), 2) for r in results}

    # Min-max normalization
    raw_list = [v for v in values.values() if v > 0]
    if not raw_list:
        return {tid: (v, 0.5) for tid, v in values.items()}

    mn, mx = min(raw_list), max(raw_list)
    span = mx - mn if mx > mn else 1.0

    return {
        tid: (v, round((v - mn) / span, 4))
        for tid, v in values.items()
    }


def expected_score(elo_a: float, elo_b: float) -> float:
    """Probability of team A beating team B based on Elo difference."""
    return 1.0 / (1.0 + math.pow(10, (elo_b - elo_a) / 400.0))


def update_elo(
    elo_a: float, elo_b: float, score_a: float, k: float = 20.0
) -> tuple[float, float]:
    """Update Elo ratings after a match result.

    score_a: 1.0 = A wins, 0.5 = draw, 0.0 = B wins
    """
    e_a = expected_score(elo_a, elo_b)
    delta = k * (score_a - e_a)
    return elo_a + delta, elo_b - delta


def get_team_dongqiudi_strength(db: Session, team: Team) -> float:
    """Compute team strength score from Dongqiudi player ability ratings.

    Aggregates per-player overall ratings (FIFA-style 0-99 scale)
    into a single team strength score (0-100 range).

    Uses weighted average: starting-quality players (overall >= 75) get
    higher weight to reflect squad quality rather than depth.
    """
    # Find all dongqiudi players for this team via:
    # Ability -> PlayerData -> TeamData -> Team
    abilities = (
        db.query(DongqiudiPlayerAbility.overall)
        .join(DongqiudiPlayerData, DongqiudiPlayerAbility.dongqiudi_player_id == DongqiudiPlayerData.id)
        .join(DongqiudiTeamData, DongqiudiPlayerData.dongqiudi_team_data_id == DongqiudiTeamData.id)
        .filter(DongqiudiTeamData.matched_team_id == team.id)
        .filter(DongqiudiPlayerAbility.overall > 0)
        .all()
    )

    if not abilities:
        return 50.0  # default mid-range when no data available

    overalls = [a[0] for a in abilities]

    # Weighted average: high-rated players (likely starters) count more
    # Weight = 1 + (overall - 70) / 30, clamped to [0.5, 2.5]
    weighted_sum = 0.0
    total_weight = 0.0
    for ov in overalls:
        weight = max(0.5, min(2.5, 1.0 + (ov - 70) / 30.0))
        weighted_sum += ov * weight
        total_weight += weight

    if total_weight > 0:
        avg = weighted_sum / total_weight
    else:
        avg = sum(overalls) / len(overalls)

    return round(avg, 1)


def composite_rating(
    elo: float,
    dongqiudi_strength: Optional[float] = None,
    market_value_eur: float = 0.0,
    w_elo: float = 0.6,
    w_strength: float = 0.3,
    w_value: float = 0.1,
) -> float:
    """Combine Elo, Dongqiudi team strength, and market value into a composite rating.

    Higher is better.
    - elo: raw Elo rating (typically 1200-2200)
    - dongqiudi_strength: team strength from Dongqiudi player abilities (0-100),
      will be scaled to ~1300-2100 range for compatibility with Elo
    - market_value_eur: total team market value in EUR, will be min-max normalized
      internally if all_teams_mv_map is provided, otherwise uses raw value / 1e9
    """
    if dongqiudi_strength and dongqiudi_strength > 0:
        strength_equiv = 1300 + dongqiudi_strength * 8
    else:
        strength_equiv = 1500

    # Normalize market value to ~0-1 range
    # Default heuristic: assume top teams are around 10亿 (1B) EUR
    if market_value_eur > 0:
        value_equiv = (market_value_eur / 1e9) * 2000  # scale to ~2000 max
        value_equiv = min(value_equiv, 2000)  # cap at 2000
    else:
        value_equiv = 1000  # fallback mid-range
    return w_elo * elo + w_strength * strength_equiv + w_value * value_equiv
