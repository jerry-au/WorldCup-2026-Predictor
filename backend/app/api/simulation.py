from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.simulation_preset import (
    SimulationPresetCreate,
    SimulationPresetDuplicateRequest,
    SimulationPresetOut,
    SimulationPresetUpdate,
)
from ..services.simulation_preset import (
    create_preset,
    duplicate_preset,
    ensure_default_presets,
    get_default_preset,
    parse_preset_parameters,
    list_presets,
    reset_builtin_preset,
    set_default_preset,
    update_preset,
)

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


def _preset_out(preset) -> SimulationPresetOut:
    return SimulationPresetOut(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        is_default=bool(preset.is_default),
        is_builtin=bool(preset.is_builtin),
        parameters=parse_preset_parameters(preset),
    )


@router.get("/presets", response_model=list[SimulationPresetOut])
def get_simulation_presets(db: Session = Depends(get_db)):
    return list_presets(db)


@router.get("/presets/default", response_model=SimulationPresetOut)
def get_default_simulation_preset(db: Session = Depends(get_db)):
    ensure_default_presets(db)
    return _preset_out(get_default_preset(db))


@router.post("/presets", response_model=SimulationPresetOut)
def create_simulation_preset(body: SimulationPresetCreate, db: Session = Depends(get_db)):
    try:
        return _preset_out(create_preset(db, body))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/presets/{preset_id}", response_model=SimulationPresetOut)
def update_simulation_preset(
    preset_id: str,
    body: SimulationPresetUpdate,
    db: Session = Depends(get_db),
):
    try:
        return _preset_out(update_preset(db, preset_id, body))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/presets/{preset_id}/set-default", response_model=SimulationPresetOut)
def set_default_simulation_preset(preset_id: str, db: Session = Depends(get_db)):
    try:
        return _preset_out(set_default_preset(db, preset_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/presets/{preset_id}/duplicate", response_model=SimulationPresetOut)
def duplicate_simulation_preset(
    preset_id: str,
    body: SimulationPresetDuplicateRequest,
    db: Session = Depends(get_db),
):
    try:
        return _preset_out(duplicate_preset(db, preset_id, body.name))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/presets/{preset_id}/reset", response_model=SimulationPresetOut)
def reset_simulation_preset(preset_id: str, db: Session = Depends(get_db)):
    try:
        return _preset_out(reset_builtin_preset(db, preset_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
