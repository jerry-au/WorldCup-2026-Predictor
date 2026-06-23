import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.simulation_preset import SimulationPreset
from app.services.simulation_preset import (
    ensure_default_presets,
    get_default_preset,
    parse_preset_parameters,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_ensure_default_presets_creates_builtin_presets(db_session):
    ensure_default_presets(db_session)

    presets = db_session.query(SimulationPreset).order_by(SimulationPreset.name).all()

    assert {preset.name for preset in presets} == {"保守", "标准", "激进"}
    assert all(preset.is_builtin for preset in presets)
    assert sum(1 for preset in presets if preset.is_default) == 1
    assert get_default_preset(db_session).name == "保守"


def test_default_preset_contains_conservative_parameters(db_session):
    ensure_default_presets(db_session)

    default_preset = get_default_preset(db_session)
    parameters = parse_preset_parameters(default_preset)

    assert parameters["motivation"]["qualified_rotation_multiplier"] == 0.88
    assert parameters["motivation"]["eliminated_morale_multiplier"] == 0.82
    assert parameters["motivation"]["top_spot_motivation_multiplier"] == 1.06
    assert parameters["motivation"]["honor_match_randomness_multiplier"] == 1.10
    assert parameters["motivation"]["motivation_min_cap"] == 0.80
    assert parameters["motivation"]["motivation_max_cap"] == 1.15
    assert parameters["collusion"]["mutual_draw_boost"] == 1.12
    assert parameters["collusion"]["opponent_selection_loss_multiplier"] == 0.94
    assert parameters["environment"]["home_advantage_multiplier"] == 1.05
    assert parameters["environment"]["travel_fatigue_multiplier"] == 0.97
    assert parameters["environment"]["weather_adaptation_multiplier"] == 0.96
    assert parameters["environment"]["jet_lag_multiplier"] == 0.97
    assert parameters["environment"]["context_min_cap"] == 0.85
    assert parameters["environment"]["context_max_cap"] == 1.10
    assert parameters["discipline"]["yellow_card_caution_multiplier"] == 0.96
    assert parameters["discipline"]["key_player_suspension_multiplier"] == 0.90


def test_ensure_default_presets_is_idempotent(db_session):
    ensure_default_presets(db_session)
    ensure_default_presets(db_session)

    presets = db_session.query(SimulationPreset).all()

    assert len(presets) == 3
    assert sum(1 for preset in presets if preset.is_default) == 1
