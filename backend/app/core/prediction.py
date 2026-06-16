"""Prediction engine: combines Elo ratings with Dixon-Coles Poisson model."""

from sqlalchemy.orm import Session

from ..models.team import Team
from ..config import settings
from .elo import composite_rating, expected_score, get_team_dongqiudi_strength, get_team_market_value
from .poisson import expected_goals, match_probabilities


class PredictionEngine:
    """Main prediction engine for single match predictions."""

    def __init__(self, rho: float = -0.10, avg_goals: float = 2.5, delta: float = 0.20):
        self.rho = rho
        self.avg_goals = avg_goals
        self.delta = delta

    def predict(
        self,
        team_a: Team,
        team_b: Team,
        db: Session | None = None,
        match_type: str = "group",
    ) -> dict:
        """Predict outcome probabilities for a match between two teams.

        Args:
            team_a: Home/team A
            team_b: Away/team B
            db: database session for fetching Dongqiudi team strength (optional)
            match_type: 'group' or 'knockout'

        Returns:
            dict with probabilities, breakdown, and confidence
        """
        # Get Dongqiudi team strength scores if db session available
        strength_a = get_team_dongqiudi_strength(db, team_a) if db else None
        strength_b = get_team_dongqiudi_strength(db, team_b) if db else None

        # Get market value from player data
        mv_a = get_team_market_value(db, team_a) if db else 0.0
        mv_b = get_team_market_value(db, team_b) if db else 0.0

        composite_a = composite_rating(
            elo=team_a.elo_rating,
            dongqiudi_strength=strength_a,
            market_value_eur=mv_a,
        )
        composite_b = composite_rating(
            elo=team_b.elo_rating,
            dongqiudi_strength=strength_b,
            market_value_eur=mv_b,
        )

        # Elo expected score as baseline
        elo_expected = expected_score(composite_a, composite_b)

        # Poisson goal expectations
        lambda_a, lambda_b = expected_goals(
            composite_a, composite_b,
            avg_goals=self.avg_goals,
            delta=self.delta,
        )

        probs = match_probabilities(lambda_a, lambda_b, rho=self.rho)

        # Confidence based on Elo gap stability
        elo_gap = abs(composite_a - composite_b)
        confidence = round(min(0.95, 0.50 + elo_gap / 800), 2)

        result = {
            "team_a": {
                "name": team_a.name_cn or team_a.name,
                "code": team_a.code,
                "flag": team_a.flag_url,
                "elo": round(team_a.elo_rating),
                "dongqiudi_strength": strength_a,
                "market_value_eur": round(mv_a / 1e6, 1) if mv_a else None,  # in millions
            },
            "team_b": {
                "name": team_b.name_cn or team_b.name,
                "code": team_b.code,
                "flag": team_b.flag_url,
                "elo": round(team_b.elo_rating),
                "dongqiudi_strength": strength_b,
                "market_value_eur": round(mv_b / 1e6, 1) if mv_b else None,
            },
            "probabilities": probs,
            "breakdown": {
                "elo_expected_a": round(elo_expected, 4),
                "expected_goals_a": round(lambda_a, 2),
                "expected_goals_b": round(lambda_b, 2),
                "strength_a": strength_a,
                "strength_b": strength_b,
                "market_value_a_m": round(mv_a / 1e6, 1) if mv_a else None,
                "market_value_b_m": round(mv_b / 1e6, 1) if mv_b else None,
            },
            "system_confidence": confidence,
            "match_type": match_type,
        }

        return result
