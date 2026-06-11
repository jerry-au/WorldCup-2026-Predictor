"""Dixon-Coles bivariate Poisson model for match score prediction.

Reference: Dixon & Coles (1998) "Modelling Association Football Scores"
"""

import math
from typing import Tuple

import numpy as np
from scipy.stats import poisson


def expected_goals(
    elo_a: float,
    elo_b: float,
    avg_goals: float = 2.5,
    delta: float = 0.15,
    home_advantage: float = 0.08,
) -> tuple[float, float]:
    """Map Elo differences to expected goals using exponential scaling.

    The stronger team's expected goals increase, the weaker team's decrease.
    """
    elo_diff = elo_a - elo_b
    ratio = math.exp(delta * elo_diff / 400.0)
    lambda_a = avg_goals * ratio * (1.0 + home_advantage)
    lambda_b = avg_goals / ratio
    return lambda_a, lambda_b


def dc_probability(
    x: int,
    y: int,
    lambda_a: float,
    lambda_b: float,
    rho: float = 0.0,
) -> float:
    """Dixon-Coles joint probability of (x goals, y goals).

    rho: association parameter (typically -0.05 to -0.15).
         Negative rho increases probability of low-scoring draws.
    """
    p_indep = poisson.pmf(x, lambda_a) * poisson.pmf(y, lambda_b)

    if x == 0 and y == 0:
        tau = 1.0 - rho * lambda_a * lambda_b
    elif x == 0 and y == 1:
        tau = 1.0 + rho * lambda_a
    elif x == 1 and y == 0:
        tau = 1.0 + rho * lambda_b
    else:
        tau = 1.0

    return tau * p_indep


def match_probabilities(
    lambda_a: float, lambda_b: float, rho: float = -0.10, max_goals: int = 10
) -> dict[str, float]:
    """Compute win/draw/lose probabilities for team A.

    Returns dict with keys: win, draw, lose, and the expected goals used.
    """
    p_win = 0.0
    p_draw = 0.0
    p_lose = 0.0

    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            p = dc_probability(x, y, lambda_a, lambda_b, rho)
            if x > y:
                p_win += p
            elif x == y:
                p_draw += p
            else:
                p_lose += p

    total = p_win + p_draw + p_lose
    if total:
        p_win /= total
        p_draw /= total
        p_lose /= total

    return {"win": round(p_win, 4), "draw": round(p_draw, 4), "lose": round(p_lose, 4)}
