"""Add article metadata tables and export lifecycle columns

Revision ID: 003
Revises: 002
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: Union[str, None] = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "article_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("backend_depth_score", sa.Float(), nullable=True),
        sa.Column("novelty_score", sa.Float(), nullable=True),
        sa.Column("actionability_score", sa.Float(), nullable=True),
        sa.Column("linkedin_potential_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="ck_article_scores_relevance_score",
        ),
        sa.CheckConstraint(
            "backend_depth_score IS NULL OR (backend_depth_score >= 0 AND backend_depth_score <= 1)",
            name="ck_article_scores_backend_depth_score",
        ),
        sa.CheckConstraint(
            "novelty_score IS NULL OR (novelty_score >= 0 AND novelty_score <= 1)",
            name="ck_article_scores_novelty_score",
        ),
        sa.CheckConstraint(
            "actionability_score IS NULL OR (actionability_score >= 0 AND actionability_score <= 1)",
            name="ck_article_scores_actionability_score",
        ),
        sa.CheckConstraint(
            "linkedin_potential_score IS NULL OR (linkedin_potential_score >= 0 AND linkedin_potential_score <= 1)",
            name="ck_article_scores_linkedin_potential_score",
        ),
        sa.CheckConstraint(
            "final_score >= 0 AND final_score <= 1",
            name="ck_article_scores_final_score",
        ),
        sa.CheckConstraint(
            "decision IN ('keep', 'discard')",
            name="ck_article_scores_decision",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", name="uq_article_scores_article_id"),
    )
    op.create_index(
        "ix_article_scores_decision_final_score",
        "article_scores",
        ["decision", "final_score"],
        unique=False,
    )

    op.create_table(
        "article_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("tag_source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "tag_source IN ('ai', 'rule', 'manual')",
            name="ck_article_tags_tag_source",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "article_id",
            "tag",
            "tag_source",
            name="uq_article_tags_article_tag_source",
        ),
    )
    op.create_index("ix_article_tags_tag", "article_tags", ["tag"], unique=False)

    op.create_table(
        "article_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_url_hash", sa.String(length=64), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=True),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('curated', 'low_value', 'duplicate', 'rejected')",
            name="ck_article_decisions_decision",
        ),
        sa.CheckConstraint("seen_count >= 1", name="ck_article_decisions_seen_count"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_url_hash", name="uq_article_decisions_normalized_url_hash"
        ),
    )
    op.create_index(
        "ix_article_decisions_decision_last_seen",
        "article_decisions",
        ["decision", "last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_article_decisions_feed_last_seen",
        "article_decisions",
        ["feed_id", "last_seen_at"],
        unique=False,
    )

    op.add_column(
        "articles",
        sa.Column("obsidian_export_status", sa.String(length=20), nullable=True),
    )
    op.add_column("articles", sa.Column("obsidian_exported_at", sa.DateTime(), nullable=True))
    op.add_column("articles", sa.Column("obsidian_note_path", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_articles_obsidian_export_status",
        "articles",
        "obsidian_export_status IN ('pending', 'exported', 'failed')",
    )

    op.create_index(
        "ix_articles_curated_pending_export_queue",
        "articles",
        ["fetched_at", "id"],
        unique=False,
        postgresql_where=sa.text(
            "is_curated = true AND obsidian_export_status = 'pending'"
        ),
    )
    op.create_index(
        "ix_articles_curated_export_status",
        "articles",
        ["obsidian_export_status", "fetched_at"],
        unique=False,
        postgresql_where=sa.text("is_curated = true"),
    )

    op.execute(
        """
        UPDATE articles
        SET obsidian_export_status = 'pending'
        WHERE is_curated = true AND obsidian_export_status IS NULL
        """
    )

    op.execute(
        """
        INSERT INTO article_decisions (
            normalized_url_hash,
            feed_id,
            article_id,
            decision,
            reason_code,
            first_seen_at,
            last_seen_at,
            seen_count
        )
        SELECT
            md5(lower(url)) AS normalized_url_hash,
            feed_id,
            id,
            CASE
                WHEN is_curated = true THEN 'curated'
                WHEN is_rejected = true THEN 'rejected'
                ELSE 'low_value'
            END AS decision,
            'migration_backfill' AS reason_code,
            COALESCE(fetched_at, NOW()) AS first_seen_at,
            COALESCE(fetched_at, NOW()) AS last_seen_at,
            1 AS seen_count
        FROM articles
        WHERE url IS NOT NULL AND url <> ''
        ON CONFLICT (normalized_url_hash) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_articles_curated_export_status", table_name="articles")
    op.drop_index("ix_articles_curated_pending_export_queue", table_name="articles")
    op.drop_constraint("ck_articles_obsidian_export_status", "articles", type_="check")
    op.drop_column("articles", "obsidian_note_path")
    op.drop_column("articles", "obsidian_exported_at")
    op.drop_column("articles", "obsidian_export_status")

    op.drop_index("ix_article_decisions_feed_last_seen", table_name="article_decisions")
    op.drop_index(
        "ix_article_decisions_decision_last_seen", table_name="article_decisions"
    )
    op.drop_table("article_decisions")

    op.drop_index("ix_article_tags_tag", table_name="article_tags")
    op.drop_table("article_tags")

    op.drop_index("ix_article_scores_decision_final_score", table_name="article_scores")
    op.drop_table("article_scores")
