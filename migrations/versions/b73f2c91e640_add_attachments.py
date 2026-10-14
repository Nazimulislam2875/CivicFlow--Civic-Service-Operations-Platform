
"""Add attachment metadata table."""

import sqlalchemy as sa

from alembic import op

revision = "b73f2c91e640"
down_revision = "a91c7e42d650"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "service_request_id",
            sa.Integer(),
            sa.ForeignKey("service_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("object_key", name="uq_attachments_object_key"),
        sa.CheckConstraint(
            "size_bytes > 0",
            name="ck_attachments_size_positive",
        ),
    )

    op.create_index(
        "ix_attachments_id",
        "attachments",
        ["id"],
    )
    op.create_index(
        "ix_attachments_service_request_id",
        "attachments",
        ["service_request_id"],
    )
    op.create_index(
        "ix_attachments_uploaded_by_id",
        "attachments",
        ["uploaded_by_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attachments_uploaded_by_id",
        table_name="attachments",
    )
    op.drop_index(
        "ix_attachments_service_request_id",
        table_name="attachments",
    )
    op.drop_index(
        "ix_attachments_id",
        table_name="attachments",
    )
    op.drop_table("attachments")
