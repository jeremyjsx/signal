"""Add job_runs table and article indexes

Revision ID: 002
Revises: 001
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: Union[str, None] = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("new_articles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"], unique=False)
    op.create_index("ix_job_runs_status", "job_runs", ["status"], unique=False)

    op.create_index(
        "ix_articles_fetched_at",
        "articles",
        ["fetched_at"],
        unique=False,
    )
    op.create_index(
        "ix_articles_is_curated_fetched_at",
        "articles",
        ["is_curated", "fetched_at"],
        unique=False,
    )
    op.create_index(
        "ix_articles_feed_id_fetched_at",
        "articles",
        ["feed_id", "fetched_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_articles_feed_id_fetched_at", table_name="articles")
    op.drop_index("ix_articles_is_curated_fetched_at", table_name="articles")
    op.drop_index("ix_articles_fetched_at", table_name="articles")

    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_job_runs_job_name", table_name="job_runs")
    op.drop_table("job_runs")
