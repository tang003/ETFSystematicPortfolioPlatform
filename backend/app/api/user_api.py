from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user_schema import UserCreate, UserRead, UserUpdate
from app.services.user_service import create_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_app_users(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[UserRead]:
    return [UserRead.model_validate(row) for row in list_users(db, limit=limit)]


@router.post("", response_model=UserRead)
def create_app_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    try:
        row = create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserRead.model_validate(row)


@router.patch("/{username}", response_model=UserRead)
def update_app_user(username: str, payload: UserUpdate, db: Session = Depends(get_db)) -> UserRead:
    try:
        row = update_user(db, username, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserRead.model_validate(row)
