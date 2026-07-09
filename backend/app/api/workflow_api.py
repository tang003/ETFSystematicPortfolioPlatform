from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow_schema import WorkflowRunRequest, WorkflowTaskCreateResponse, WorkflowTaskRead
from app.services.workflow_service import create_workflow_task, get_workflow_task, list_workflow_tasks, run_workflow_task

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/run", response_model=WorkflowTaskCreateResponse)
def create_full_workflow(
    request: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> WorkflowTaskCreateResponse:
    task = create_workflow_task(db, request)
    background_tasks.add_task(run_workflow_task, task.id)
    return WorkflowTaskCreateResponse(task_id=task.id, status=task.status)


@router.get("", response_model=list[WorkflowTaskRead])
def list_workflows(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[WorkflowTaskRead]:
    items = []
    for task in list_workflow_tasks(db, limit=limit):
        _, steps = get_workflow_task(db, task.id)
        items.append(WorkflowTaskRead.model_validate({**task.__dict__, "steps": steps}))
    return items


@router.get("/{task_id}", response_model=WorkflowTaskRead)
def get_workflow(task_id: int, db: Session = Depends(get_db)) -> WorkflowTaskRead:
    task, steps = get_workflow_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Workflow task not found")
    return WorkflowTaskRead.model_validate({**task.__dict__, "steps": steps})
