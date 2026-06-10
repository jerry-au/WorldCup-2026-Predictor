from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    team_a_code: str = Field(..., min_length=3, max_length=3)
    team_b_code: str = Field(..., min_length=3, max_length=3)
    match_type: str = Field(default="group", pattern="^(group|knockout)$")


class BettingRec(BaseModel):
    outcome: str
    odds: float
    ev: float
    rating: str
    system_prob: float
    market_prob: float


class OddsComparison(BaseModel):
    provider_count: int
    market_avg: dict[str, float]
    best_odds: dict[str, dict]
    market_implied: dict[str, float]


class Discrepancy(BaseModel):
    detected: bool
    max_delta: float | None = None
    system_confidence: float | None = None
    detail: str | None = None


class PredictResponse(BaseModel):
    team_a: dict
    team_b: dict
    probabilities: dict[str, float]
    breakdown: dict
    system_confidence: float
    match_type: str
    betting: dict
