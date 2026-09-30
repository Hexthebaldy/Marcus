"""editorial 相关数据库表与字段。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME, INTEGER, MEDIUMTEXT, SMALLINT
from sqlalchemy.orm import Mapped, mapped_column

from marcus.core.security import now
from marcus.models.base import Base


class EditorArticle(Base):
    __tablename__ = "editor_articles"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    author_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    city_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    district_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("districts.id", use_alter=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_revision_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"), nullable=True
    )
    first_published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    editorial_rank: Mapped[int] = mapped_column(INTEGER(), nullable=False, default=0)
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorDraft(Base):
    __tablename__ = "editor_drafts"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    article_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    subtitle: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    focus_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    primary_place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    primary_event_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    document: Mapped[dict[str, object]] = mapped_column(
        JSON(), nullable=False, default=lambda: {"type": "doc", "content": []}
    )
    document_schema_version: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=1)
    cover_asset_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    tag_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    edit_version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    last_edited_by: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorRevision(Base):
    __tablename__ = "editor_revisions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    article_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    based_on_edit_version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    subtitle: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    focus_type: Mapped[str] = mapped_column(String(20), nullable=False)
    primary_place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    primary_event_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    document: Mapped[dict[str, object]] = mapped_column(
        JSON(), nullable=False, default=lambda: {"type": "doc", "content": []}
    )
    document_schema_version: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=1)
    plain_text: Mapped[str] = mapped_column(MEDIUMTEXT(), nullable=False)
    cover_asset_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    submitted_by: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class EditorRevisionTag(Base):
    __tablename__ = "editor_revision_tags"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    revision_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("tags.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class EditorRevisionAsset(Base):
    __tablename__ = "editor_revision_assets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    revision_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    asset_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class EditorReview(Base):
    __tablename__ = "editor_reviews"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    revision_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewer_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    automated_findings: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    reviewed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)
