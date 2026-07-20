from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="viewer", index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
