"""Elo rating system for cross-team comparison.

Based on the standard Elo formula adapted for international football.
Initial ratings seeded from FIFA rankings, updated after each match.
"""

import math


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


def composite_rating(
    elo: float,
    fifa_rank: int,
    market_value_norm: float = 0.5,
    w_elo: float = 0.6,
    w_fifa: float = 0.3,
    w_value: float = 0.1,
) -> float:
    """Combine Elo, FIFA rank, and market value into a composite rating.

    Higher is better. fifa_rank is converted so that rank=1 → ~2000.
    market_value_norm should be normalized to 0-1 range across all teams.
    """
    fifa_equiv = max(0, 2500 - (fifa_rank - 1) * 10) if fifa_rank else 1500
    value_equiv = market_value_norm * 2000 if market_value_norm else 1000
    return w_elo * elo + w_fifa * fifa_equiv + w_value * value_equiv
