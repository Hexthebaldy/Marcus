"""media 相关数据库表与字段。"""

from datetime import datetime
from typing import TypedDict
from uuid import uuid4

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR, DATETIME, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from marcus.core.security import now
from marcus.models.base import Base


class MediaVariant(TypedDict):
    storage_key: str
    width: int
    height: int
    mime_type: str


class MediaAsset(Base):
    __tablename__ = "media_assets"
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
    owner_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_mime: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BIGINT(unsigned=True), nullable=True)
    width: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    height: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BIGINT(unsigned=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    variants: Mapped[dict[str, MediaVariant]] = mapped_column(JSON(), nullable=False, default=dict)
    rejection_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    upload_expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)
