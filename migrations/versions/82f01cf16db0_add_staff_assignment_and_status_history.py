
"""Add staff assignment and status history.

Revision ID: 82f01cf16db0
Revises: 7f8eb0b24619
Create Date: 2026-10-12 08:59:42.087152
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers used by Alembic.
revision: str = "82f01cf16db0"
down_revision: str | Sequence[str] | None = "7f8eb0b24619"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add staff assignment and request status history."""
    op.create_table(
        "service_request_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["service_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_service_request_status_history_changed_by_id"),
        "service_request_status_history",
        ["changed_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_service_request_status_history_request_id"),
        "service_request_status_history",
        ["request_id"],
        unique=False,
    )

    op.add_column(
        "service_requests",
        sa.Column("assigned_staff_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_service_requests_assigned_staff_id"),
        "service_requests",
        ["assigned_staff_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_service_requests_assigned_staff_id_users",
        "service_requests",
        "users",
        ["assigned_staff_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Remove staff assignment and request status history."""
    op.drop_constraint(
        "fk_service_requests_assigned_staff_id_users",
        "service_requests",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_service_requests_assigned_staff_id"),
        table_name="service_requests",
    )
    op.drop_column("service_requests", "assigned_staff_id")

    op.drop_index(
        op.f("ix_service_request_status_history_request_id"),
        table_name="service_request_status_history",
    )
    op.drop_index(
        op.f("ix_service_request_status_history_changed_by_id"),
        table_name="service_request_status_history",
    )
    op.drop_table("service_request_status_history")
