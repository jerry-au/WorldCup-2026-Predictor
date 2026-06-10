from pydantic import BaseModel


class PlayerSeasonStatsOut(BaseModel):
    competition_code: str
    competition_name: str | None = None
    goals: int = 0
    assists: int = 0
    appearances: int = 0
    minutes_played: int = 0

    model_config = {"from_attributes": True}


class PlayerOut(BaseModel):
    name: str
    jersey: int | None
    position: str | None
    club_name: str | None
    age_at_tournament: int | None
    season_stats: list[PlayerSeasonStatsOut] = []
    best_position: str | None = None

    model_config = {"from_attributes": True}


class TeamListOut(BaseModel):
    code: str
    name: str
    iso: str
    confederation: str
    group_name: str
    flag_url: str | None
    elo_rating: float
    fifa_rank: int

    model_config = {"from_attributes": True}


class TeamDetailOut(BaseModel):
    code: str
    name: str
    iso: str
    confederation: str
    group_name: str
    flag_url: str | None
    elo_rating: float
    fifa_rank: int
    market_value_eur: float
    coach_name: str | None
    coach_country: str | None
    players: list[PlayerOut]
    starting_xi: list[PlayerOut] | None = None

    model_config = {"from_attributes": True}
