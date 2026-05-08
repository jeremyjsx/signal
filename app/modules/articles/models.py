from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint(
            "obsidian_export_status IN ('pending', 'exported', 'failed')",
            name="ck_articles_obsidian_export_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    ai_relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_curated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    obsidian_export_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    obsidian_exported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    obsidian_note_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ArticleScore(Base):
    __tablename__ = "article_scores"
    __table_args__ = (
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="ck_article_scores_relevance_score",
        ),
        CheckConstraint(
            "backend_depth_score IS NULL OR (backend_depth_score >= 0 AND backend_depth_score <= 1)",
            name="ck_article_scores_backend_depth_score",
        ),
        CheckConstraint(
            "novelty_score IS NULL OR (novelty_score >= 0 AND novelty_score <= 1)",
            name="ck_article_scores_novelty_score",
        ),
        CheckConstraint(
            "actionability_score IS NULL OR (actionability_score >= 0 AND actionability_score <= 1)",
            name="ck_article_scores_actionability_score",
        ),
        CheckConstraint(
            "linkedin_potential_score IS NULL OR (linkedin_potential_score >= 0 AND linkedin_potential_score <= 1)",
            name="ck_article_scores_linkedin_potential_score",
        ),
        CheckConstraint(
            "final_score >= 0 AND final_score <= 1",
            name="ck_article_scores_final_score",
        ),
        CheckConstraint(
            "decision IN ('keep', 'discard')",
            name="ck_article_scores_decision",
        ),
        UniqueConstraint("article_id", name="uq_article_scores_article_id"),
        Index(
            "ix_article_scores_decision_final_score",
            "decision",
            "final_score",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    backend_depth_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    novelty_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actionability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    linkedin_potential_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reasoning_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class ArticleTag(Base):
    __tablename__ = "article_tags"
    __table_args__ = (
        CheckConstraint(
            "tag_source IN ('ai', 'rule', 'manual')",
            name="ck_article_tags_tag_source",
        ),
        UniqueConstraint(
            "article_id",
            "tag",
            "tag_source",
            name="uq_article_tags_article_tag_source",
        ),
        Index("ix_article_tags_tag", "tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_source: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ArticleDecision(Base):
    __tablename__ = "article_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('curated', 'low_value', 'duplicate', 'rejected')",
            name="ck_article_decisions_decision",
        ),
        CheckConstraint(
            "seen_count >= 1",
            name="ck_article_decisions_seen_count",
        ),
        UniqueConstraint(
            "normalized_url_hash", name="uq_article_decisions_normalized_url_hash"
        ),
        Index("ix_article_decisions_decision_last_seen", "decision", "last_seen_at"),
        Index("ix_article_decisions_feed_last_seen", "feed_id", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    normalized_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feed_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("feeds.id", ondelete="SET NULL"), nullable=True
    )
    article_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    seen_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
