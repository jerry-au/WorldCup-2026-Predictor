"""Tests for the Monte Carlo tournament simulation engine."""

import numpy as np
import pytest

from app.core.simulation import MonteCarloEngine, TeamInGroup, SimulationResults
from app.core.elo import composite_rating


def _make_teams_by_group(
    strong: int = 2, medium: int = 1, weak: int = 1
) -> dict[str, list[TeamInGroup]]:
    """Build 12 groups x 4 teams with configurable strength distribution.

    strong: composite ~1800, medium: ~1650, weak: ~1500
    """
    groups = {}
    team_idx = 0
    for g_idx in range(12):
        g = chr(ord('A') + g_idx)
        teams = []
        for i in range(strong):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1800.0))
            team_idx += 1
        for i in range(medium):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1650.0))
            team_idx += 1
        for i in range(weak):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1500.0))
            team_idx += 1
        groups[g] = teams
    return groups


def _make_team_names(groups: dict[str, list[TeamInGroup]]) -> dict[str, str]:
    """Generate display names for all teams."""
    names = {}
    for g, teams in groups.items():
        for t in teams:
            names[t.code] = f"Team {t.code}"
    return names


def test_deterministic_with_seed():
    """Same seed produces identical results across two runs."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine1 = MonteCarloEngine(num_iterations=100, seed=42)
    result1 = engine1.simulate(groups, names)

    engine2 = MonteCarloEngine(num_iterations=100, seed=42)
    result2 = engine2.simulate(groups, names)

    np.testing.assert_array_equal(result1.champion, result2.champion)
    np.testing.assert_array_equal(result1.round_32, result2.round_32)
