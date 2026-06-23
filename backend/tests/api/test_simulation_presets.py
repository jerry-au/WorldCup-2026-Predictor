import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.simulation_preset import SimulationPreset
from app.schemas.simulation_preset import SimulationPresetUpdate
from app.services.simulation_preset import (
    duplicate_preset,
    ensure_default_presets,
    get_default_preset,
    parse_preset_parameters,
    reset_builtin_preset,
    set_default_preset,
    update_preset,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


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


def test_update_preset_persists_parameters(db_session):
    ensure_default_presets(db_session)
    preset = get_default_preset(db_session)
    parameters = parse_preset_parameters(preset)
    parameters["motivation"]["qualified_rotation_multiplier"] = 0.91

    updated = update_preset(
        db_session,
        preset.id,
        SimulationPresetUpdate(parameters=parameters),
    )

    assert parse_preset_parameters(updated)["motivation"]["qualified_rotation_multiplier"] == 0.91


def test_set_default_preset_clears_other_defaults(db_session):
    ensure_default_presets(db_session)
    standard = db_session.query(SimulationPreset).filter(SimulationPreset.name == "标准").one()

    set_default_preset(db_session, standard.id)

    presets = db_session.query(SimulationPreset).all()
    assert get_default_preset(db_session).id == standard.id
    assert sum(1 for preset in presets if preset.is_default) == 1


def test_duplicate_builtin_preset_creates_custom_copy(db_session):
    ensure_default_presets(db_session)
    conservative = get_default_preset(db_session)

    duplicate = duplicate_preset(db_session, conservative.id, "我的保守预设")

    assert duplicate.name == "我的保守预设"
    assert duplicate.is_builtin is False
    assert duplicate.is_default is False
    assert parse_preset_parameters(duplicate) == parse_preset_parameters(conservative)


def test_reset_builtin_preset_restores_original_parameters(db_session):
    ensure_default_presets(db_session)
    conservative = get_default_preset(db_session)
    parameters = parse_preset_parameters(conservative)
    parameters["collusion"]["mutual_draw_boost"] = 1.30
    update_preset(db_session, conservative.id, SimulationPresetUpdate(parameters=parameters))

    reset = reset_builtin_preset(db_session, conservative.id)

    assert parse_preset_parameters(reset)["collusion"]["mutual_draw_boost"] == 1.12


def test_invalid_parameters_are_rejected(db_session):
    ensure_default_presets(db_session)
    conservative = get_default_preset(db_session)
    parameters = parse_preset_parameters(conservative)
    parameters["motivation"]["qualified_rotation_multiplier"] = 2.0

    with pytest.raises(ValueError):
        update_preset(db_session, conservative.id, SimulationPresetUpdate(parameters=parameters))


def test_list_presets_endpoint_returns_builtin_presets(api_client):
    response = api_client.get("/api/v1/simulation/presets")

    assert response.status_code == 200
    data = response.json()
    assert {preset["name"] for preset in data} == {"保守", "标准", "激进"}
    assert all("parameters" in preset for preset in data)
    assert sum(1 for preset in data if preset["is_default"]) == 1


def test_default_preset_endpoint_returns_default(api_client):
    response = api_client.get("/api/v1/simulation/presets/default")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "保守"
    assert data["is_default"] is True
    assert data["parameters"]["collusion"]["mutual_draw_boost"] == 1.12


def test_create_update_default_duplicate_and_reset_endpoints(api_client):
    default_response = api_client.get("/api/v1/simulation/presets/default")
    parameters = default_response.json()["parameters"]

    create_response = api_client.post("/api/v1/simulation/presets", json={
        "name": "自定义",
        "description": "测试预设",
        "parameters": parameters,
    })
    assert create_response.status_code == 200
    custom = create_response.json()
    assert custom["name"] == "自定义"
    assert custom["is_builtin"] is False

    parameters["motivation"]["qualified_rotation_multiplier"] = 0.93
    update_response = api_client.put(f"/api/v1/simulation/presets/{custom['id']}", json={
        "parameters": parameters,
    })
    assert update_response.status_code == 200
    assert update_response.json()["parameters"]["motivation"]["qualified_rotation_multiplier"] == 0.93

    default_set_response = api_client.post(f"/api/v1/simulation/presets/{custom['id']}/set-default")
    assert default_set_response.status_code == 200
    assert default_set_response.json()["is_default"] is True

    duplicate_response = api_client.post(f"/api/v1/simulation/presets/{custom['id']}/duplicate", json={
        "name": "自定义副本",
    })
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["name"] == "自定义副本"

    builtin_id = default_response.json()["id"]
    reset_response = api_client.post(f"/api/v1/simulation/presets/{builtin_id}/reset")
    assert reset_response.status_code == 200
    assert reset_response.json()["parameters"]["collusion"]["mutual_draw_boost"] == 1.12
