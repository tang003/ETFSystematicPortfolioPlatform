from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.schemas.settings_schema import (
    DataSourceConfigCreate,
    DataSourceConfigUpdate,
    DataSourceProviderRead,
    DataSourceSettingsRead,
    MaintenanceStatusRead,
)
from app.schemas.workflow_schema import WorkflowTaskCreateResponse
from app.services.daily_maintenance_service import get_daily_maintenance_status
from app.services.settings_service import (
    build_provider_read,
    create_data_source_config,
    list_data_source_settings,
    update_data_source_config,
)
from app.services.workflow_service import create_daily_maintenance_task

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/data-sources", response_model=DataSourceSettingsRead)
def get_data_sources(db: Session = Depends(get_db)) -> DataSourceSettingsRead:
    return list_data_source_settings(db)


@router.get("/maintenance", response_model=MaintenanceStatusRead)
def get_maintenance_status() -> MaintenanceStatusRead:
    return MaintenanceStatusRead.model_validate(get_daily_maintenance_status(get_settings()))


@router.post("/maintenance/run", response_model=WorkflowTaskCreateResponse)
def run_maintenance_now(db: Session = Depends(get_db)) -> WorkflowTaskCreateResponse:
    task = create_daily_maintenance_task(db)
    return WorkflowTaskCreateResponse(task_id=task.id, status=task.status)


@router.post("/data-sources", response_model=DataSourceProviderRead)
def create_data_source_endpoint(
    request: DataSourceConfigCreate,
    db: Session = Depends(get_db),
) -> DataSourceProviderRead:
    try:
        row = create_data_source_config(db, request.model_dump())
        return build_provider_read(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/data-sources/{provider_code}", response_model=DataSourceProviderRead)
def update_data_source_endpoint(
    provider_code: str,
    request: DataSourceConfigUpdate,
    db: Session = Depends(get_db),
) -> DataSourceProviderRead:
    try:
        row = update_data_source_config(db, provider_code, request.model_dump(exclude_unset=True))
        return build_provider_read(row)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
