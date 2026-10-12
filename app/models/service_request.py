
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    STATUSES: ClassVar[tuple[str, ...]] = (
        "SUBMITTED",
        "IN_PROGRESS",
        "RESOLVED",
        "REJECTED",
    )
    PRIORITIES: ClassVar[tuple[str, ...]] = ("LOW", "MEDIUM", "HIGH")

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="SUBMITTED",
        server_default="SUBMITTED",
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default="MEDIUM",
        server_default="MEDIUM",
        nullable=False,
    )

    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(String(300))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
