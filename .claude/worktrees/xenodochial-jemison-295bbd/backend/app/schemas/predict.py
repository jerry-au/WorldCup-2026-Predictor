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


# ── Tournament Simulation ──────────────────────────────────────────


class TournamentResponse(BaseModel):
    task_id: str
    status: str


class TeamProbabilityOut(BaseModel):
    team_code: str
    team_name: str
    round_32: float
    round_16: float
    quarter: float
    semi: float
    final_: float
    champion: float


class KnockoutMatchOut(BaseModel):
    round_name: str
    position: int
    team_a: str | None
    team_b: str | None
    prob_a: float | None
    prob_b: float | None


class TaskProgressResponse(BaseModel):
    status: str   # running / completed / failed
    progress: float = 0.0
    result: dict | None = None
    error: str | None = None
