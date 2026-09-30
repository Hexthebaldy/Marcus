"""engagement 相关数据库表与字段。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from marcus.core.security import now
from marcus.models.base import Base


class NoteReaction(Base):
    __tablename__ = "note_reactions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    note_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class EditorArticleReaction(Base):
    __tablename__ = "editor_article_reactions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    article_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class EventParticipation(Base):
    __tablename__ = "event_participations"
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
    user_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("event_sessions.id", use_alter=True),
        nullable=True,
    )
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    attended_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    blocked_user_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class NoteReport(Base):
    __tablename__ = "note_reports"
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
    reporter_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    note_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
    )
    submission_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("note_submissions.id", use_alter=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolved_by: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorArticleReport(Base):
    __tablename__ = "editor_article_reports"
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
    reporter_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    article_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolved_by: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)
