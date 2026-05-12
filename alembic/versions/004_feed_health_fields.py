"""Add feed health fields for auto-disable

Revision ID: 004
Revises: 003
Create Date: 2026-05-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: Union[str, None] = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feeds", sa.Column("last_success_at", sa.DateTime(), nullable=True))
    op.add_column("feeds", sa.Column("last_error_at", sa.DateTime(), nullable=True))
    op.add_column("feeds", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column("feeds", sa.Column("auto_disabled_at", sa.DateTime(), nullable=True))
    op.add_column(
        "feeds",
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("feeds", "consecutive_failures")
    op.drop_column("feeds", "auto_disabled_at")
    op.drop_column("feeds", "last_error_message")
    op.drop_column("feeds", "last_error_at")
    op.drop_column("feeds", "last_success_at")
