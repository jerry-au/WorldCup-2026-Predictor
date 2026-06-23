from pydantic import BaseModel, Field, model_validator


class MotivationParameters(BaseModel):
    qualified_rotation_multiplier: float = Field(..., ge=0.5, le=1.5)
    eliminated_morale_multiplier: float = Field(..., ge=0.5, le=1.5)
    top_spot_motivation_multiplier: float = Field(..., ge=0.5, le=1.5)
    honor_match_randomness_multiplier: float = Field(..., ge=0.5, le=1.5)
    motivation_min_cap: float = Field(..., ge=0.5, le=1.5)
    motivation_max_cap: float = Field(..., ge=0.5, le=1.5)

    @model_validator(mode="after")
    def validate_caps(self):
        if self.motivation_min_cap >= self.motivation_max_cap:
            raise ValueError("motivation_min_cap must be lower than motivation_max_cap")
        return self


class CollusionParameters(BaseModel):
    mutual_draw_boost: float = Field(..., ge=1.0, le=1.5)
    opponent_selection_loss_multiplier: float = Field(..., ge=0.5, le=1.5)


class EnvironmentParameters(BaseModel):
    home_advantage_multiplier: float = Field(..., ge=0.5, le=1.5)
    travel_fatigue_multiplier: float = Field(..., ge=0.5, le=1.5)
    weather_adaptation_multiplier: float = Field(..., ge=0.5, le=1.5)
    jet_lag_multiplier: float = Field(..., ge=0.5, le=1.5)
    context_min_cap: float = Field(..., ge=0.5, le=1.5)
    context_max_cap: float = Field(..., ge=0.5, le=1.5)

    @model_validator(mode="after")
    def validate_caps(self):
        if self.context_min_cap >= self.context_max_cap:
            raise ValueError("context_min_cap must be lower than context_max_cap")
        return self


class DisciplineParameters(BaseModel):
    yellow_card_caution_multiplier: float = Field(..., ge=0.5, le=1.5)
    key_player_suspension_multiplier: float = Field(..., ge=0.5, le=1.5)


class SimulationPresetParameters(BaseModel):
    motivation: MotivationParameters
    collusion: CollusionParameters
    environment: EnvironmentParameters
    discipline: DisciplineParameters


class SimulationPresetOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_default: bool
    is_builtin: bool
    parameters: SimulationPresetParameters


class SimulationPresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str | None = None
    parameters: SimulationPresetParameters


class SimulationPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    parameters: SimulationPresetParameters | dict | None = None


class SimulationPresetDuplicateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
