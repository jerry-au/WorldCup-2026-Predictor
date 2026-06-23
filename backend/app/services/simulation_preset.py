import json
import uuid
from copy import deepcopy

from sqlalchemy.orm import Session

from ..models.simulation_preset import SimulationPreset
from ..schemas.simulation_preset import (
    SimulationPresetCreate,
    SimulationPresetOut,
    SimulationPresetParameters,
    SimulationPresetUpdate,
)

CONSERVATIVE_PARAMETERS = {
    "motivation": {
        "qualified_rotation_multiplier": 0.88,
        "eliminated_morale_multiplier": 0.82,
        "top_spot_motivation_multiplier": 1.06,
        "honor_match_randomness_multiplier": 1.10,
        "motivation_min_cap": 0.80,
        "motivation_max_cap": 1.15,
    },
    "collusion": {
        "mutual_draw_boost": 1.12,
        "opponent_selection_loss_multiplier": 0.94,
    },
    "environment": {
        "home_advantage_multiplier": 1.05,
        "travel_fatigue_multiplier": 0.97,
        "weather_adaptation_multiplier": 0.96,
        "jet_lag_multiplier": 0.97,
        "context_min_cap": 0.85,
        "context_max_cap": 1.10,
    },
    "discipline": {
        "yellow_card_caution_multiplier": 0.96,
        "key_player_suspension_multiplier": 0.90,
    },
}

STANDARD_PARAMETERS = {
    "motivation": {
        "qualified_rotation_multiplier": 0.84,
        "eliminated_morale_multiplier": 0.78,
        "top_spot_motivation_multiplier": 1.08,
        "honor_match_randomness_multiplier": 1.14,
        "motivation_min_cap": 0.76,
        "motivation_max_cap": 1.18,
    },
    "collusion": {
        "mutual_draw_boost": 1.16,
        "opponent_selection_loss_multiplier": 0.92,
    },
    "environment": {
        "home_advantage_multiplier": 1.07,
        "travel_fatigue_multiplier": 0.95,
        "weather_adaptation_multiplier": 0.94,
        "jet_lag_multiplier": 0.95,
        "context_min_cap": 0.82,
        "context_max_cap": 1.12,
    },
    "discipline": {
        "yellow_card_caution_multiplier": 0.94,
        "key_player_suspension_multiplier": 0.87,
    },
}

AGGRESSIVE_PARAMETERS = {
    "motivation": {
        "qualified_rotation_multiplier": 0.80,
        "eliminated_morale_multiplier": 0.72,
        "top_spot_motivation_multiplier": 1.12,
        "honor_match_randomness_multiplier": 1.20,
        "motivation_min_cap": 0.70,
        "motivation_max_cap": 1.25,
    },
    "collusion": {
        "mutual_draw_boost": 1.24,
        "opponent_selection_loss_multiplier": 0.88,
    },
    "environment": {
        "home_advantage_multiplier": 1.10,
        "travel_fatigue_multiplier": 0.92,
        "weather_adaptation_multiplier": 0.91,
        "jet_lag_multiplier": 0.92,
        "context_min_cap": 0.78,
        "context_max_cap": 1.15,
    },
    "discipline": {
        "yellow_card_caution_multiplier": 0.92,
        "key_player_suspension_multiplier": 0.84,
    },
}


def get_builtin_presets() -> dict[str, dict]:
    return {
        "保守": {
            "description": "保守场外因素修正，不盖过 Elo/Poisson 主模型。",
            "is_default": True,
            "parameters": deepcopy(CONSERVATIVE_PARAMETERS),
        },
        "标准": {
            "description": "适度增强战意、默契球和环境因素影响。",
            "is_default": False,
            "parameters": deepcopy(STANDARD_PARAMETERS),
        },
        "激进": {
            "description": "用于探索场外因素影响上限，不建议默认使用。",
            "is_default": False,
            "parameters": deepcopy(AGGRESSIVE_PARAMETERS),
        },
    }


def ensure_default_presets(db: Session) -> None:
    builtins = get_builtin_presets()
    existing = {
        preset.name: preset
        for preset in db.query(SimulationPreset).filter(SimulationPreset.name.in_(builtins.keys())).all()
    }

    for name, config in builtins.items():
        if name in existing:
            continue
        db.add(SimulationPreset(
            id=str(uuid.uuid4()),
            name=name,
            description=config["description"],
            is_default=config["is_default"],
            is_builtin=True,
            parameters_json=json.dumps(config["parameters"], ensure_ascii=False),
        ))

    db.flush()

    default_count = db.query(SimulationPreset).filter(SimulationPreset.is_default.is_(True)).count()
    if default_count != 1:
        db.query(SimulationPreset).update({SimulationPreset.is_default: False})
        conservative = db.query(SimulationPreset).filter(SimulationPreset.name == "保守").first()
        if conservative:
            conservative.is_default = True

    db.commit()


def get_default_preset(db: Session) -> SimulationPreset:
    preset = db.query(SimulationPreset).filter(SimulationPreset.is_default.is_(True)).first()
    if preset is None:
        ensure_default_presets(db)
        preset = db.query(SimulationPreset).filter(SimulationPreset.is_default.is_(True)).first()
    return preset


def parse_preset_parameters(preset: SimulationPreset) -> dict:
    return json.loads(preset.parameters_json)


def _validated_parameters(parameters: SimulationPresetParameters | dict) -> dict:
    if isinstance(parameters, SimulationPresetParameters):
        return parameters.model_dump()
    return SimulationPresetParameters.model_validate(parameters).model_dump()


def _to_out(preset: SimulationPreset) -> SimulationPresetOut:
    return SimulationPresetOut(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        is_default=bool(preset.is_default),
        is_builtin=bool(preset.is_builtin),
        parameters=_validated_parameters(parse_preset_parameters(preset)),
    )


def list_presets(db: Session) -> list[SimulationPresetOut]:
    ensure_default_presets(db)
    return [
        _to_out(preset)
        for preset in db.query(SimulationPreset).order_by(SimulationPreset.is_builtin.desc(), SimulationPreset.name).all()
    ]


def create_preset(db: Session, body: SimulationPresetCreate) -> SimulationPreset:
    preset = SimulationPreset(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        is_default=False,
        is_builtin=False,
        parameters_json=json.dumps(body.parameters.model_dump(), ensure_ascii=False),
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


def update_preset(db: Session, preset_id: str, body: SimulationPresetUpdate) -> SimulationPreset:
    preset = db.query(SimulationPreset).filter(SimulationPreset.id == preset_id).first()
    if preset is None:
        raise ValueError("Preset not found")
    if body.name is not None:
        preset.name = body.name
    if body.description is not None:
        preset.description = body.description
    if body.parameters is not None:
        preset.parameters_json = json.dumps(_validated_parameters(body.parameters), ensure_ascii=False)
    db.commit()
    db.refresh(preset)
    return preset


def set_default_preset(db: Session, preset_id: str) -> SimulationPreset:
    preset = db.query(SimulationPreset).filter(SimulationPreset.id == preset_id).first()
    if preset is None:
        raise ValueError("Preset not found")
    db.query(SimulationPreset).update({SimulationPreset.is_default: False})
    preset.is_default = True
    db.commit()
    db.refresh(preset)
    return preset


def duplicate_preset(db: Session, preset_id: str, name: str) -> SimulationPreset:
    preset = db.query(SimulationPreset).filter(SimulationPreset.id == preset_id).first()
    if preset is None:
        raise ValueError("Preset not found")
    duplicate = SimulationPreset(
        id=str(uuid.uuid4()),
        name=name,
        description=preset.description,
        is_default=False,
        is_builtin=False,
        parameters_json=preset.parameters_json,
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


def reset_builtin_preset(db: Session, preset_id: str) -> SimulationPreset:
    preset = db.query(SimulationPreset).filter(SimulationPreset.id == preset_id).first()
    if preset is None:
        raise ValueError("Preset not found")
    if not preset.is_builtin:
        raise ValueError("Only builtin presets can be reset")
    builtin = get_builtin_presets().get(preset.name)
    if builtin is None:
        raise ValueError("Unknown builtin preset")
    preset.description = builtin["description"]
    preset.parameters_json = json.dumps(builtin["parameters"], ensure_ascii=False)
    db.commit()
    db.refresh(preset)
    return preset
