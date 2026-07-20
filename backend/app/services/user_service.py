from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import AppUser
from app.schemas.user_schema import UserCreate, UserUpdate

VALID_ROLES = {"admin", "researcher", "viewer"}


def get_user_by_username(db: Session, username: str) -> AppUser | None:
    return db.scalar(select(AppUser).where(AppUser.username == username.strip()))


def list_users(db: Session, *, limit: int = 100) -> list[AppUser]:
    return list(db.scalars(select(AppUser).order_by(AppUser.created_at.desc(), AppUser.id.desc()).limit(limit)))


def create_user(db: Session, payload: UserCreate) -> AppUser:
    username = payload.username.strip()
    if payload.role not in VALID_ROLES:
        raise ValueError("Invalid role")
    if get_user_by_username(db, username):
        raise ValueError("Username already exists")
    row = AppUser(
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        display_name=payload.display_name,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_user(db: Session, username: str, payload: UserUpdate) -> AppUser:
    row = get_user_by_username(db, username)
    if row is None:
        raise ValueError("User not found")
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise ValueError("Invalid role")
        row.role = payload.role
    if payload.display_name is not None:
        row.display_name = payload.display_name
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.password:
        row.password_hash = hash_password(payload.password)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def authenticate_database_user(db: Session, username: str, password: str) -> AppUser | None:
    row = get_user_by_username(db, username)
    if row is None or not row.is_active:
        return None
    if not verify_password(password, row.password_hash):
        return None
    row.last_login_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
