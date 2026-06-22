"""Monte Carlo tournament simulation engine.

2026 WC format: 12 groups × 4 teams → top 2 + 8 best 3rd → Round of 32 → knockout.
Uses numpy vectorization for performance (~1-2s for 10,000 iterations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from .poisson import expected_goals


@dataclass
class TeamInGroup:
    """Team within its group context for simulation."""
    code: str
    group: str
    composite: float


@dataclass
class CompletedMatch:
    """A completed group-stage match with known final score.

    Used to seed the simulation with real-world results so that
    only the remaining matches are randomly sampled.
    """
    team_a_code: str
    team_b_code: str
    score_a: int
    score_b: int
    group_name: str


@dataclass
class BracketSlot:
    """A single match slot in the most-likely knockout bracket."""
    round_name: str
    position: int
    team_a: str
    team_b: str
    prob_a: float
    prob_b: float


@dataclass
class SimulationResults:
    """Aggregated simulation results across all iterations."""
    team_codes: List[str]
    team_names: List[str]
    round_32: np.ndarray
    round_16: np.ndarray
    quarter: np.ndarray
    semi: np.ndarray
    final_: np.ndarray
    champion: np.ndarray
    bracket: List[BracketSlot] = field(default_factory=list)


class MonteCarloEngine:
    """Main simulation engine.

    Performs N iterations of full tournament simulation:
      group stage → 3rd-place ranking → Round of 32 → Round of 16 → QF → SF → Final

    All match outcomes are sampled using the Dixon-Coles bivariate Poisson model
    (via expected_goals), with extra time / penalties for knockout draws.
    """

    GROUP_MATCHES = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
    GROUP_NAMES = [chr(ord('A') + i) for i in range(12)]

    # Bracket structure for Round of 32.
    # Groups split into 4 sections of 3: (A,B,C), (D,E,F), (G,H,I), (J,K,L)
    # ("W", G) = group G winner, ("R", G) = group G runner-up,
    # ("3", k) = k-th best third-placed (0-indexed)
    R32_CONFIG = [
        # Section 1
        ("round_32", 0, ("W", "A"), ("R", "B")),
        ("round_32", 1, ("W", "C"), ("3", 0)),
        ("round_32", 2, ("W", "B"), ("R", "A")),
        ("round_32", 3, ("R", "C"), ("3", 1)),
        # Section 2
        ("round_32", 4, ("W", "D"), ("R", "E")),
        ("round_32", 5, ("W", "F"), ("3", 2)),
        ("round_32", 6, ("W", "E"), ("R", "D")),
        ("round_32", 7, ("R", "F"), ("3", 3)),
        # Section 3
        ("round_32", 8, ("W", "G"), ("R", "H")),
        ("round_32", 9, ("W", "I"), ("3", 4)),
        ("round_32", 10, ("W", "H"), ("R", "G")),
        ("round_32", 11, ("R", "I"), ("3", 5)),
        # Section 4
        ("round_32", 12, ("W", "J"), ("R", "K")),
        ("round_32", 13, ("W", "L"), ("3", 6)),
        ("round_32", 14, ("W", "K"), ("R", "J")),
        ("round_32", 15, ("R", "L"), ("3", 7)),
    ]

    R16_CONFIG = [
        ("round_16", i, ("M", i * 2), ("M", i * 2 + 1))
        for i in range(8)
    ]

    QF_CONFIG = [
        ("quarter", i, ("M", i * 2), ("M", i * 2 + 1))
        for i in range(4)
    ]

    SF_CONFIG = [
        ("semi", i, ("M", i * 2), ("M", i * 2 + 1))
        for i in range(2)
    ]

    FINAL_CONFIG = [("final", 0, ("M", 0), ("M", 1))]

    # Lambda for home advantage multiplier in knockout
    HOME_ADV = 1.08

    def __init__(self, num_iterations: int = 10_000, seed: int = 42):
        self.N = num_iterations
        self.rng = np.random.default_rng(seed)
        # Cache params from expected_goals defaults
        self._avg_goals = 2.5
        self._delta = 0.20

    # ── Public API ────────────────────────────────────────────────

    def simulate(
        self,
        teams_by_group: Dict[str, List[TeamInGroup]],
        team_names: Dict[str, str],
        completed_matches: List[CompletedMatch] | None = None,
    ) -> SimulationResults:
        """Run full tournament simulation.

        Args:
            teams_by_group: {group_letter: [TeamInGroup, ...]} for all 12 groups
            team_names: {team_code: display_name}
            completed_matches: list of already-played group stage matches.
                If provided, group stage simulation starts from these real
                results and only simulates the remaining matches.

        Returns:
            SimulationResults with per-team advancement probabilities (0.0 - 1.0)
        """
        # Build flat team index
        all_codes: List[str] = []
        all_comps: np.ndarray  # [n_teams]
        group_team_indices: Dict[str, List[int]] = {}

        comp_list: List[float] = []
        for g in self.GROUP_NAMES:
            group_teams = teams_by_group.get(g, [])
            # Sort within group so indices are stable
            group_teams_sorted = sorted(
                group_teams, key=lambda t: t.composite, reverse=True
            )[:4]
            group_team_indices[g] = []
            for t in group_teams_sorted:
                group_team_indices[g].append(len(all_codes))
                all_codes.append(t.code)
                comp_list.append(t.composite)
                team_names[t.code] = team_names.get(t.code, t.code)

        n_teams = len(all_codes)
        all_comps = np.array(comp_list, dtype=np.float64)
        names = [team_names.get(c, c) for c in all_codes]

        # ── Phase 1: Group stage ──
        group_rankings, third_ranked = self._simulate_group_stage(
            group_team_indices, all_comps, all_codes, completed_matches
        )

        # ── Phase 2: Determine qualified third-placed teams ──
        qualified_thirds = self._rank_third_placed(third_ranked)

        # ── Phase 3: Knockout bracket ──
        furthest, bracket_slots = self._simulate_knockout(
            group_rankings, qualified_thirds, n_teams, all_comps, all_codes
        )

        # ── Aggregate results ──
        return SimulationResults(
            team_codes=all_codes,
            team_names=names,
            round_32=np.round((furthest >= 1).mean(axis=0).astype(float), 4),
            round_16=np.round((furthest >= 2).mean(axis=0).astype(float), 4),
            quarter=np.round((furthest >= 3).mean(axis=0).astype(float), 4),
            semi=np.round((furthest >= 4).mean(axis=0).astype(float), 4),
            final_=np.round((furthest >= 5).mean(axis=0).astype(float), 4),
            champion=np.round((furthest >= 6).mean(axis=0).astype(float), 4),
            bracket=bracket_slots,
        )

    # ── Group Stage ───────────────────────────────────────────────

    def _simulate_group_stage(
        self,
        group_team_indices: Dict[str, List[int]],
        all_comps: np.ndarray,
        all_codes: List[str],
        completed_matches: List[CompletedMatch] | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate group stage for all 12 groups.

        If completed_matches is provided, those matches are applied as fixed
        real-world results and only the remaining matches are sampled randomly.

        Returns:
            group_rankings: [N, 12, 4] — global team index per iteration, group, position
            third_ranked: [N, 12, 3] — (points, gd, gf) of 3rd-placed team per group
        """
        n_groups = 12
        group_rankings = np.zeros((self.N, n_groups, 4), dtype=np.int32)
        third_ranked = np.zeros((self.N, n_groups, 3), dtype=np.int32)

        n_range = np.arange(self.N)

        # Build lookup: group_name -> list of completed matches in that group
        completed_by_group: Dict[str, List[CompletedMatch]] = {}
        if completed_matches:
            for m in completed_matches:
                completed_by_group.setdefault(m.group_name, []).append(m)

        for gi, g in enumerate(self.GROUP_NAMES):
            idxs = group_team_indices.get(g, [])
            if len(idxs) < 4:
                continue

            comps = all_comps[idxs]  # [4]

            points = np.zeros((self.N, 4), dtype=np.int32)
            gd_arr = np.zeros((self.N, 4), dtype=np.int32)
            gf_arr = np.zeros((self.N, 4), dtype=np.int32)

            # Map team_code -> group-internal index (0-3) for this group
            code_to_internal = {all_codes[idx]: pos for pos, idx in enumerate(idxs)}

            # Collect which matchups are already completed
            group_completed = completed_by_group.get(g, [])
            completed_pairs: set[tuple[int, int]] = set()

            # Apply completed match results (fixed across all iterations)
            for cm in group_completed:
                i_pos = code_to_internal.get(cm.team_a_code)
                j_pos = code_to_internal.get(cm.team_b_code)
                if i_pos is None or j_pos is None:
                    continue

                g_i = cm.score_a
                g_j = cm.score_b

                if g_i > g_j:
                    points[:, i_pos] += 3
                elif g_i == g_j:
                    points[:, i_pos] += 1
                    points[:, j_pos] += 1
                else:
                    points[:, j_pos] += 3

                gd_arr[:, i_pos] += g_i - g_j
                gd_arr[:, j_pos] += g_j - g_i
                gf_arr[:, i_pos] += g_i
                gf_arr[:, j_pos] += g_j

                # Mark this pair as completed (store sorted tuple)
                completed_pairs.add(
                    (min(i_pos, j_pos), max(i_pos, j_pos))
                )

            # Simulate remaining (not yet completed) matches
            for i, j in self.GROUP_MATCHES:
                pair = (min(i, j), max(i, j))
                if pair in completed_pairs:
                    continue  # already played, skip

                λ_i, λ_j = expected_goals(
                    comps[i], comps[j],
                    avg_goals=self._avg_goals,
                    delta=self._delta,
                )
                g_i = self.rng.poisson(λ_i, self.N)
                g_j = self.rng.poisson(λ_j, self.N)

                win_i = (g_i > g_j).astype(np.int32)
                win_j = (g_j > g_i).astype(np.int32)
                draw = (g_i == g_j).astype(np.int32)

                points[:, i] += win_i * 3 + draw * 1
                points[:, j] += win_j * 3 + draw * 1
                gd_arr[:, i] += g_i - g_j
                gd_arr[:, j] += g_j - g_i
                gf_arr[:, i] += g_i
                gf_arr[:, j] += g_j

            # Rank: points > gd > gf
            rank_score = (
                points.astype(np.int64) * 1_000_000
                + gd_arr.astype(np.int64) * 1_000
                + gf_arr.astype(np.int64)
            )
            order = np.argsort(-rank_score, axis=1)  # [N, 4]

            for pos in range(4):
                group_rankings[:, gi, pos] = idxs[0] + order[:, pos]

            # Save 3rd-placed stats for cross-group ranking
            third_ranked[:, gi, 0] = points[n_range, order[:, 2]]
            third_ranked[:, gi, 1] = gd_arr[n_range, order[:, 2]]
            third_ranked[:, gi, 2] = gf_arr[n_range, order[:, 2]]

        return group_rankings, third_ranked

    # ── Third-Place Ranking ───────────────────────────────────────

    def _rank_third_placed(
        self, third_ranked: np.ndarray
    ) -> np.ndarray:
        """Rank third-placed teams across groups and return top 8.

        Args:
            third_ranked: [N, 12, 3] — (points, gd, gf) per group

        Returns:
            qualified_thirds: [N, 8] — group indices (0-11) of top 8, in order
        """
        score = (
            third_ranked[:, :, 0].astype(np.int64) * 1_000_000
            + third_ranked[:, :, 1].astype(np.int64) * 1_000
            + third_ranked[:, :, 2].astype(np.int64)
        )
        order = np.argsort(-score, axis=1)  # [N, 12]
        return order[:, :8]  # [N, 8]

    # ── Knockout Stage ────────────────────────────────────────────

    def _simulate_knockout(
        self,
        group_rankings: np.ndarray,
        qualified_thirds: np.ndarray,
        n_teams: int,
        all_comps: np.ndarray,
        all_codes: List[str],
    ) -> Tuple[np.ndarray, List[BracketSlot]]:
        """Simulate full knockout bracket.

        Returns:
            furthest: [N, n_teams] — highest round reached:
                0=group, 1=R32, 2=R16, 3=QF, 4=SF, 5=final, 6=champion
            bracket_slots: List[BracketSlot] — most likely matchup per position
        """
        furthest = np.zeros((self.N, n_teams), dtype=np.int32)
        n_range = np.arange(self.N)

        # Populate R32 bracket teams
        r32_teams = np.zeros((self.N, 16, 2), dtype=np.int32)  # [N, match, side]

        for mi, (_, _, src_a, src_b) in enumerate(self.R32_CONFIG):
            r32_teams[:, mi, 0] = self._resolve_source(
                src_a, group_rankings, qualified_thirds
            )
            r32_teams[:, mi, 1] = self._resolve_source(
                src_b, group_rankings, qualified_thirds
            )

        # Mark all R32 participants (round 1)
        for mi in range(16):
            for side in (0, 1):
                idxs = r32_teams[:, mi, side]
                furthest[n_range, idxs] = np.maximum(furthest[n_range, idxs], 1)

        # Simulate R32 → winners
        r32_w = np.zeros((self.N, 16), dtype=np.int32)
        for mi in range(16):
            r32_w[:, mi] = self._sample_knockout_match(
                r32_teams[:, mi, 0], r32_teams[:, mi, 1], all_comps
            )
        # Mark R32 winners as reaching R16 (round 2)
        for mi in range(16):
            furthest[n_range, r32_w[:, mi]] = np.maximum(
                furthest[n_range, r32_w[:, mi]], 2
            )

        # Simulate R16
        r16_w = self._simulate_round(self.R16_CONFIG, r32_w, all_comps, furthest, 3)

        # Simulate QF
        qf_w = self._simulate_round(self.QF_CONFIG, r16_w, all_comps, furthest, 4)

        # Simulate SF
        sf_w = self._simulate_round(self.SF_CONFIG, qf_w, all_comps, furthest, 5)

        # Simulate Final — handle champion separately
        # Both finalists reach level 5 (final appearance), then champion gets level 6
        final_participants = sf_w[:, :2]  # [N, 2]
        furthest[n_range, final_participants[:, 0]] = np.maximum(
            furthest[n_range, final_participants[:, 0]], 5
        )
        furthest[n_range, final_participants[:, 1]] = np.maximum(
            furthest[n_range, final_participants[:, 1]], 5
        )

        champion_idx = self._sample_knockout_match(
            final_participants[:, 0], final_participants[:, 1], all_comps
        )
        furthest[n_range, champion_idx] = 6

        # ── Compute most likely bracket ──
        bracket_slots = self._compute_bracket_slots(
            all_codes, all_comps, r32_teams, r32_w, r16_w, qf_w, sf_w
        )

        return furthest, bracket_slots

    def _simulate_round(
        self,
        config: List[Tuple],
        prev_winners: np.ndarray,
        all_comps: np.ndarray,
        furthest: np.ndarray,
        round_level: int,
    ) -> np.ndarray:
        """Simulate a knockout round given previous round's winners.

        Args:
            config: [(round_name, position, src_a, src_b), ...]
            prev_winners: [N, n_prev_matches] — team indices from previous round
            all_comps: [n_teams]
            furthest: [N, n_teams] — updated in-place for participants
            round_level: round number to mark (3=R16, 4=QF, 5=SF, 6=final)

        Returns:
            winners: [N, n_matches] — winner team indices for this round
        """
        n_range = np.arange(self.N)
        n_matches = len(config)
        winners = np.zeros((self.N, n_matches), dtype=np.int32)

        for mi, (_, _, src_a, src_b) in enumerate(config):
            # Resolve match source references
            a = self._resolve_match_source(src_a, prev_winners)
            b = self._resolve_match_source(src_b, prev_winners)
            w = self._sample_knockout_match(a, b, all_comps)
            winners[:, mi] = w

            # Mark participants as reaching this round
            for side_arr in (a, b):
                furthest[n_range, side_arr] = np.maximum(
                    furthest[n_range, side_arr], round_level
                )

        return winners

    # ── Source Resolution ─────────────────────────────────────────

    def _resolve_source(
        self,
        source: Tuple[str, str | int],
        group_rankings: np.ndarray,
        qualified_thirds: np.ndarray,
    ) -> np.ndarray:
        """Map a bracket source to team indices [N].

        Source types:
            ("W", "A") = group A winner
            ("R", "C") = group C runner-up
            ("3", k)   = k-th best third-placed (0-indexed)
        """
        stype, sval = source
        if stype == "W":
            gi = self.GROUP_NAMES.index(sval)
            return group_rankings[:, gi, 0].copy()
        elif stype == "R":
            gi = self.GROUP_NAMES.index(sval)
            return group_rankings[:, gi, 1].copy()
        elif stype == "3":
            slot = int(sval)
            n_range = np.arange(self.N)
            g_idxs = qualified_thirds[:, slot]  # [N] — group indices
            return group_rankings[n_range, g_idxs, 2]
        raise ValueError(f"Unknown source type: {stype}")

    def _resolve_match_source(
        self,
        source: Tuple[str, int],
        prev_winners: np.ndarray,
    ) -> np.ndarray:
        """Resolve ("M", match_idx) → prev_winners[:, match_idx]"""
        _, match_idx = source
        return prev_winners[:, match_idx].copy()

    # ── Match Sampling ────────────────────────────────────────────

    def _sample_knockout_match(
        self,
        team_a_idx: np.ndarray,
        team_b_idx: np.ndarray,
        all_comps: np.ndarray,
    ) -> np.ndarray:
        """Sample knockout match outcomes for N iterations.

        Uses Poisson goals; draws resolved by extra time (reduced λ)
        then penalty coin-flip.

        Returns:
            [N] — team index of winner per iteration
        """
        comp_a = all_comps[team_a_idx]
        comp_b = all_comps[team_b_idx]

        elo_diff = comp_a - comp_b
        ratio = np.exp(self._delta * elo_diff / 400.0)
        λ_a = self._avg_goals * ratio * self.HOME_ADV
        λ_b = self._avg_goals / ratio

        g_a = self.rng.poisson(λ_a)
        g_b = self.rng.poisson(λ_b)

        # Extra time / penalties for draws
        tied = g_a == g_b
        if tied.any():
            n_tied = int(tied.sum())
            λ_a_et = λ_a[tied] * 0.3
            λ_b_et = λ_b[tied] * 0.3
            et_a = self.rng.poisson(λ_a_et)
            et_b = self.rng.poisson(λ_b_et)

            still_tied = et_a == et_b
            if still_tied.any():
                pens = self.rng.random(int(still_tied.sum())) >= 0.5
                et_a[still_tied] = pens.astype(np.int32)
                et_b[still_tied] = (~pens).astype(np.int32)

            g_a[tied] += et_a
            g_b[tied] += et_b

        return np.where(g_a > g_b, team_a_idx, team_b_idx)

    # ── Bracket Computation ───────────────────────────────────────────

    def _compute_bracket_slots(
        self,
        all_codes: List[str],
        all_comps: np.ndarray,
        r32_teams: np.ndarray,
        r32_w: np.ndarray,
        r16_w: np.ndarray,
        qf_w: np.ndarray,
        sf_w: np.ndarray,
    ) -> List[BracketSlot]:
        """Compute the most likely bracket from simulation results.

        For each bracket slot, finds the most frequent team across all N
        iterations and computes their head-to-head win probability.
        Teams are de-duplicated within each round so no team appears twice.
        """
        bracket: List[BracketSlot] = []

        def _mode(arr: np.ndarray) -> int:
            values, counts = np.unique(arr, return_counts=True)
            return values[int(np.argmax(counts))]

        def _mode_unique(arr: np.ndarray, used: set[int]) -> int:
            """Most frequent team in arr, excluding already-used teams."""
            values, counts = np.unique(arr, return_counts=True)
            order = np.argsort(-counts)
            for idx in order:
                v = int(values[idx])
                if v not in used:
                    return v
            return _mode(arr)

        def _h2h(ta: int, tb: int) -> Tuple[float, float]:
            return self._h2h_prob(float(all_comps[ta]), float(all_comps[tb]))

        # R32: direct from group-based slot assignments, enforce uniqueness
        r32_used: set[int] = set()
        for mi in range(16):
            ta = _mode_unique(r32_teams[:, mi, 0], r32_used)
            r32_used.add(ta)
            tb = _mode_unique(r32_teams[:, mi, 1], r32_used)
            r32_used.add(tb)
            pa, pb = _h2h(ta, tb)
            bracket.append(BracketSlot("round_32", mi, all_codes[ta], all_codes[tb], pa, pb))

        # R16: most common winners advance from adjacent R32 matches
        r16_used: set[int] = set()
        for mi in range(8):
            ta = _mode_unique(r32_w[:, mi * 2], r16_used)
            r16_used.add(ta)
            tb = _mode_unique(r32_w[:, mi * 2 + 1], r16_used)
            r16_used.add(tb)
            pa, pb = _h2h(ta, tb)
            bracket.append(BracketSlot("round_16", mi, all_codes[ta], all_codes[tb], pa, pb))

        # QF
        qf_used: set[int] = set()
        for mi in range(4):
            ta = _mode_unique(r16_w[:, mi * 2], qf_used)
            qf_used.add(ta)
            tb = _mode_unique(r16_w[:, mi * 2 + 1], qf_used)
            qf_used.add(tb)
            pa, pb = _h2h(ta, tb)
            bracket.append(BracketSlot("quarter", mi, all_codes[ta], all_codes[tb], pa, pb))

        # SF
        sf_used: set[int] = set()
        for mi in range(2):
            ta = _mode_unique(qf_w[:, mi * 2], sf_used)
            sf_used.add(ta)
            tb = _mode_unique(qf_w[:, mi * 2 + 1], sf_used)
            sf_used.add(tb)
            pa, pb = _h2h(ta, tb)
            bracket.append(BracketSlot("semi", mi, all_codes[ta], all_codes[tb], pa, pb))

        # Final
        final_used: set[int] = set()
        ta = _mode_unique(sf_w[:, 0], final_used)
        final_used.add(ta)
        tb = _mode_unique(sf_w[:, 1], final_used)
        final_used.add(tb)
        pa, pb = _h2h(ta, tb)
        bracket.append(BracketSlot("final", 0, all_codes[ta], all_codes[tb], pa, pb))

        return bracket

    def _h2h_prob(self, comp_a: float, comp_b: float) -> Tuple[float, float]:
        """Head-to-head win probability for a knockout match using Poisson model."""
        elo_diff = comp_a - comp_b
        ratio = np.exp(self._delta * elo_diff / 400.0)
        λ_a = self._avg_goals * ratio * self.HOME_ADV
        λ_b = self._avg_goals / ratio

        n = 100_000
        g_a = self.rng.poisson(λ_a, n)
        g_b = self.rng.poisson(λ_b, n)

        win_a = float((g_a > g_b).mean())
        draw = float((g_a == g_b).mean())
        win_a += draw * 0.5
        win_b = 1.0 - win_a

        return round(win_a, 4), round(win_b, 4)

def run_simulation(
    teams_by_group: Dict[str, List[TeamInGroup]],
    team_names: Dict[str, str],
    num_iterations: int = 10_000,
    seed: int = 42,
    completed_matches: List[CompletedMatch] | None = None,
) -> SimulationResults:
    """Run full tournament simulation with default engine."""
    engine = MonteCarloEngine(num_iterations=num_iterations, seed=seed)
    return engine.simulate(teams_by_group, team_names, completed_matches)
