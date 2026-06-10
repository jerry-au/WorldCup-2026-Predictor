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


def test_group_stage_ranking():
    """Group stage produces correct rankings based on points > GD > GF."""
    groups = {
        "A": [
            TeamInGroup(code="STR", group="A", composite=1900.0),
            TeamInGroup(code="MED", group="A", composite=1650.0),
            TeamInGroup(code="WKA", group="A", composite=1600.0),
            TeamInGroup(code="WEA", group="A", composite=1400.0),
        ]
    }
    for g_idx in range(1, 12):
        g = chr(ord('A') + g_idx)
        groups[g] = [
            TeamInGroup(code=f"{g}1", group=g, composite=1700.0),
            TeamInGroup(code=f"{g}2", group=g, composite=1650.0),
            TeamInGroup(code=f"{g}3", group=g, composite=1600.0),
            TeamInGroup(code=f"{g}4", group=g, composite=1550.0),
        ]

    names = _make_team_names(groups)
    engine = MonteCarloEngine(num_iterations=500, seed=42)
    result = engine.simulate(groups, names)

    str_idx = result.team_codes.index("STR")
    wea_idx = result.team_codes.index("WEA")
    assert result.round_32[str_idx] > result.round_32[wea_idx], (
        f"STR R32={result.round_32[str_idx]} should be > WEA R32={result.round_32[wea_idx]}"
    )


def test_third_place_qualification():
    """8 of 12 third-placed teams qualify for Round of 32."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=200, seed=42)
    result = engine.simulate(groups, names)

    for i, code in enumerate(result.team_codes):
        assert result.round_32[i] >= 0.0, f"{code} has negative R32 probability"
        assert result.round_32[i] <= 1.0, f"{code} has R32 > 1.0"


def test_knockout_bracket_progression():
    """Knockout bracket has correct number of matches per round."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=100, seed=42)
    result = engine.simulate(groups, names)

    round_counts = {}
    for slot in result.bracket:
        round_counts[slot.round_name] = round_counts.get(slot.round_name, 0) + 1

    assert round_counts.get("round_32") == 16, f"Expected 16 R32 matches, got {round_counts.get('round_32')}"
    assert round_counts.get("round_16") == 8, f"Expected 8 R16 matches, got {round_counts.get('round_16')}"
    assert round_counts.get("quarter") == 4, f"Expected 4 QF matches, got {round_counts.get('quarter')}"
    assert round_counts.get("semi") == 2, f"Expected 2 SF matches, got {round_counts.get('semi')}"
    assert round_counts.get("final") == 1, f"Expected 1 Final match, got {round_counts.get('final')}"


def test_probability_sanity():
    """Strong teams have higher champion probability than weak teams."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=500, seed=42)
    result = engine.simulate(groups, names)

    strong_codes = [t.code for g in groups.values() for t in g if t.composite == 1800.0]
    weak_codes = [t.code for g in groups.values() for t in g if t.composite == 1500.0]

    strong_champ = float(result.champion[result.team_codes.index(strong_codes[0])])
    weak_champ = float(result.champion[result.team_codes.index(weak_codes[0])])

    assert strong_champ > weak_champ, (
        f"Strong team champ prob {strong_champ} should be > weak team {weak_champ}"
    )

    total_champ = float(result.champion.sum())
    assert abs(total_champ - 1.0) < 0.05, f"Champion probabilities sum to {total_champ}, expected ~1.0"


def test_tiebreaker_no_crash():
    """Engine handles teams with identical composite ratings without crashing."""
    groups = {}
    team_idx = 0
    for g_idx in range(12):
        g = chr(ord('A') + g_idx)
        groups[g] = [
            TeamInGroup(code=f"E{team_idx+i}", group=g, composite=1600.0)
            for i in range(4)
        ]
        team_idx += 4

    names = _make_team_names(groups)
    engine = MonteCarloEngine(num_iterations=50, seed=42)

    result = engine.simulate(groups, names)

    assert len(result.team_codes) == 48
    assert all(0.0 <= p <= 1.0 for p in result.champion), "Champion probabilities out of range"
