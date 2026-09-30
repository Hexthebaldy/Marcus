"""note 相关数据库表与字段。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from marcus.core.security import now
from marcus.models.base import Base


class Note(Base):
    __tablename__ = "notes"
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
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    body_text: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_submission_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"), nullable=True
    )
    first_published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class NoteImage(Base):
    __tablename__ = "note_images"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    note_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    asset_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class NoteDraft(Base):
    __tablename__ = "note_drafts"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    note_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    body_text: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    image_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    edit_version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class NoteSubmission(Base):
    __tablename__ = "note_submissions"
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
    note_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
    )
    submission_no: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    based_on_edit_version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    body_text: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    image_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
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
    review_version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)
