from datetime import datetime

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    id: int
    username: str
    role: str
    display_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.@-]+$")
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(default="viewer", pattern=r"^(admin|researcher|viewer)$")
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=12, max_length=256)
    role: str | None = Field(default=None, pattern=r"^(admin|researcher|viewer)$")
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
