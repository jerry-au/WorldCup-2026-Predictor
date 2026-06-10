"""Prediction engine: combines Elo ratings with Dixon-Coles Poisson model."""

from sqlalchemy.orm import Session

from ..models.team import Team
from ..config import settings
from .elo import composite_rating, expected_score
from .poisson import expected_goals, match_probabilities


class PredictionEngine:
    """Main prediction engine for single match predictions."""

    def __init__(self, rho: float = -0.10, avg_goals: float = 2.5, delta: float = 0.20):
        self.rho = rho
        self.avg_goals = avg_goals
        self.delta = delta

    def predict(
        self, team_a: Team, team_b: Team, match_type: str = "group"
    ) -> dict:
        """Predict outcome probabilities for a match between two teams.

        Args:
            team_a: Home/team A
            team_b: Away/team B
            match_type: 'group' or 'knockout'

        Returns:
            dict with probabilities, breakdown, and confidence
        """
        composite_a = composite_rating(
            elo=team_a.elo_rating,
            fifa_rank=team_a.fifa_rank,
        )
        composite_b = composite_rating(
            elo=team_b.elo_rating,
            fifa_rank=team_b.fifa_rank,
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
                "name": team_a.name,
                "code": team_a.code,
                "flag": team_a.flag_url,
                "elo": round(team_a.elo_rating),
                "fifa_rank": team_a.fifa_rank,
            },
            "team_b": {
                "name": team_b.name,
                "code": team_b.code,
                "flag": team_b.flag_url,
                "elo": round(team_b.elo_rating),
                "fifa_rank": team_b.fifa_rank,
            },
            "probabilities": probs,
            "breakdown": {
                "elo_expected_a": round(elo_expected, 4),
                "expected_goals_a": round(lambda_a, 2),
                "expected_goals_b": round(lambda_b, 2),
            },
            "system_confidence": confidence,
            "match_type": match_type,
        }

        return result
