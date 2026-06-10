from pydantic import BaseModel


class PlayerOut(BaseModel):
    name: str
    jersey: int | None
    position: str | None
    club_name: str | None
    age_at_tournament: int | None

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

    model_config = {"from_attributes": True}
