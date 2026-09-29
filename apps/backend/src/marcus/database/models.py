"""Explicit SQLAlchemy models for the MySQL 8.4 schema."""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR, DATETIME, DECIMAL, INTEGER, MEDIUMTEXT, SMALLINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from marcus.core.security import now


class MediaVariant(TypedDict):
    storage_key: str
    width: int
    height: int
    mime_type: str


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
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
    email_lookup_hash: Mapped[str | None] = mapped_column(
        CHAR(64, charset="ascii", collation="ascii_bin"), nullable=True
    )
    email_ciphertext: Mapped[str | None] = mapped_column(Text(), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    bio: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    avatar_asset_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    city_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    terms_version: Mapped[str] = mapped_column(String(40), nullable=False)
    terms_accepted_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class UserRole(Base):
    __tablename__ = "user_roles"
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
    role: Mapped[str] = mapped_column(String(20), nullable=False, primary_key=True)
    granted_by: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthSendLimit(Base):
    __tablename__ = "auth_send_limits"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    email_lookup_hash: Mapped[str] = mapped_column(
        CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False, primary_key=True
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False, primary_key=True)
    next_allowed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
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
    email_lookup_hash: Mapped[str] = mapped_column(
        CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False
    )
    email_ciphertext: Mapped[str] = mapped_column(Text(), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    code_hmac: Mapped[str] = mapped_column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    delivery_code_ciphertext: Mapped[str | None] = mapped_column(Text(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    attempts: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=5)
    consumed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    terms_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
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
    client_type: Mapped[str] = mapped_column(String(20), nullable=False)
    device_label: Mapped[str] = mapped_column(String(100), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
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
    session_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("auth_sessions.id", use_alter=True),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("refresh_tokens.id", use_alter=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class City(Base):
    __tablename__ = "cities"
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
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    country_code: Mapped[str] = mapped_column(CHAR(2, charset="ascii", collation="ascii_bin"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean(create_constraint=True), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class District(Base):
    __tablename__ = "districts"
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
    city_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Place(Base):
    __tablename__ = "places"
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
    city_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    district_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("districts.id", use_alter=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    latitude: Mapped[Decimal | None] = mapped_column(DECIMAL(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(DECIMAL(9, 6), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    opening_hours_text: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    transport_notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    cover_asset_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class PlaceAsset(Base):
    __tablename__ = "place_assets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    place_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
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


class Event(Base):
    __tablename__ = "events"
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
    city_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    place_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text(), nullable=False, default="")
    organizer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    booking_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    price_status: Mapped[str] = mapped_column(String(20), nullable=False)
    price_min_fen: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    price_max_fen: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    currency: Mapped[str] = mapped_column(
        CHAR(3, charset="ascii", collation="ascii_bin"), nullable=False, default="CNY"
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EventSession(Base):
    __tablename__ = "event_sessions"
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
    event_id: Mapped[str] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    entry_note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    version: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Tag(Base):
    __tablename__ = "tags"
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
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean(create_constraint=True), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


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


class Job(Base):
    __tablename__ = "jobs"
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
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(191), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
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
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    request_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(
        CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False
    )
    resource_id: Mapped[str] = mapped_column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    response_status: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
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
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    before_summary: Mapped[dict[str, object] | None] = mapped_column(JSON(), nullable=True)
    after_summary: Mapped[dict[str, object] | None] = mapped_column(JSON(), nullable=True)
    request_id: Mapped[str] = mapped_column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False, default=now)


# Relational invariants are enforced in MySQL as well as the API.
def uq(table, *cols):
    table.__table__.append_constraint(
        UniqueConstraint(*cols, name="uq_" + table.__tablename__ + "_" + "_".join(cols))
    )


def ck(table, name, sql):
    table.__table__.append_constraint(CheckConstraint(sql, name="ck_" + table.__tablename__ + "_" + name))


def composite(table, local, remote, name):
    table.__table__.append_constraint(ForeignKeyConstraint(local, remote, name=name, use_alter=True))


for model, cols in [
    (User, ("email_lookup_hash",)),
    (RefreshToken, ("token_hash",)),
    (RefreshToken, ("parent_id",)),
    (City, ("code",)),
    (District, ("city_id", "code")),
    (District, ("id", "city_id")),
    (Place, ("id", "city_id")),
    (Tag, ("slug",)),
    (MediaAsset, ("storage_key",)),
    (PlaceAsset, ("place_id", "position")),
    (EventSession, ("id", "event_id")),
    (EventSession, ("event_id", "starts_at", "ends_at")),
    (EditorRevision, ("article_id", "revision_no")),
    (EditorRevision, ("article_id", "based_on_edit_version")),
    (EditorRevision, ("id", "article_id")),
    (EditorReview, ("revision_id",)),
    (NoteSubmission, ("note_id", "submission_no")),
    (NoteSubmission, ("note_id", "based_on_edit_version")),
    (NoteSubmission, ("id", "note_id")),
    (NoteImage, ("note_id", "position")),
    (EventParticipation, ("user_id", "event_id")),
    (Job, ("dedupe_key",)),
    (IdempotencyRecord, ("user_id", "operation", "request_key")),
]:
    uq(model, *cols)
composite(Place, ["district_id", "city_id"], ["districts.id", "districts.city_id"], "fk_place_district_city")
composite(Event, ["place_id", "city_id"], ["places.id", "places.city_id"], "fk_event_place_city")
composite(
    EditorArticle,
    ["district_id", "city_id"],
    ["districts.id", "districts.city_id"],
    "fk_article_district_city",
)
composite(
    EditorArticle,
    ["published_revision_id", "id"],
    ["editor_revisions.id", "editor_revisions.article_id"],
    "fk_article_own_revision",
)
composite(
    Note,
    ["published_submission_id", "id"],
    ["note_submissions.id", "note_submissions.note_id"],
    "fk_note_own_submission",
)
composite(
    NoteReport,
    ["submission_id", "note_id"],
    ["note_submissions.id", "note_submissions.note_id"],
    "fk_report_note_submission",
)
composite(
    EditorArticleReport,
    ["revision_id", "article_id"],
    ["editor_revisions.id", "editor_revisions.article_id"],
    "fk_report_article_revision",
)
composite(
    EventParticipation,
    ["session_id", "event_id"],
    ["event_sessions.id", "event_sessions.event_id"],
    "fk_participation_session_event",
)
ck(
    User,
    "email",
    "(status='deleted' AND email_lookup_hash IS NULL AND email_ciphertext IS NULL AND email_verified_at IS NULL) OR (status IN ('active','suspended') AND email_lookup_hash IS NOT NULL AND email_ciphertext IS NOT NULL AND email_verified_at IS NOT NULL)",
)
ck(UserRole, "role", "role IN ('editor','moderator','admin')")
ck(AuthChallenge, "purpose", "purpose IN ('login','delete_account')")
ck(AuthSession, "client_type", "client_type IN ('mobile','editor_web')")
ck(
    Place,
    "coords",
    "(latitude IS NULL AND longitude IS NULL) OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
)
ck(EventSession, "time", "ends_at > starts_at")
ck(
    Event,
    "price",
    "(price_status='unknown' AND price_min_fen IS NULL AND price_max_fen IS NULL) OR (price_status='free' AND price_min_fen=0 AND price_max_fen=0) OR (price_status='known' AND price_min_fen IS NOT NULL AND price_max_fen IS NOT NULL AND price_min_fen<=price_max_fen)",
)
ck(
    EditorDraft,
    "focus",
    "(focus_type IS NULL AND primary_place_id IS NULL AND primary_event_id IS NULL) OR (focus_type='place' AND primary_event_id IS NULL) OR (focus_type='event' AND primary_place_id IS NULL)",
)
ck(
    EditorRevision,
    "focus",
    "(focus_type='place' AND primary_place_id IS NOT NULL AND primary_event_id IS NULL) OR (focus_type='event' AND primary_event_id IS NOT NULL AND primary_place_id IS NULL)",
)
ck(UserBlock, "self", "user_id <> blocked_user_id")
ck(NoteImage, "position", "position <= 8")
ck(MediaAsset, "kind", "kind IN ('image','video') AND (kind <> 'video' OR purpose='editorial_media')")
ck(MediaAsset, "purpose", "purpose IN ('note_image','editorial_media','place_image','avatar')")
for model in (NoteReaction, EditorArticleReaction):
    ck(model, "kind", "kind IN ('like','bookmark')")
for model in (NoteSubmission, EditorReview):
    ck(
        model,
        "review",
        "(status='pending' AND reviewed_at IS NULL) OR (status='approved' AND reviewed_at IS NOT NULL) OR (status='rejected' AND reviewed_at IS NOT NULL AND reason_code IS NOT NULL)",
    )
ck(EditorReview, "reviewer", "status='pending' OR reviewer_id IS NOT NULL")
ck(
    EventParticipation,
    "state",
    "(state='interested' AND attended_at IS NULL) OR (state='attended' AND attended_at IS NOT NULL)",
)
for model, ptr in [(Note, "published_submission_id"), (EditorArticle, "published_revision_id")]:
    ck(
        model,
        "published",
        f"status <> 'published' OR ({ptr} IS NOT NULL AND first_published_at IS NOT NULL AND published_at IS NOT NULL)",
    )
for model, cols in [
    (AuthChallenge, ("email_lookup_hash", "purpose", "created_at")),
    (AuthSession, ("user_id", "revoked_at")),
    (Place, ("city_id", "district_id", "status")),
    (Event, ("city_id", "status")),
    (EventSession, ("event_id", "status", "starts_at")),
    (MediaAsset, ("owner_id", "status")),
    (EditorArticle, ("city_id", "district_id", "status", "editorial_rank", "first_published_at", "id")),
    (Note, ("city_id", "status", "first_published_at", "id")),
    (Note, ("author_id", "created_at")),
    (NoteSubmission, ("status", "created_at")),
    (EditorReview, ("status", "created_at")),
    (Job, ("status", "available_at", "id")),
    (Job, ("status", "lease_until")),
    (AuditLog, ("target_type", "target_id", "created_at")),
]:
    Index(
        ("ix_" + model.__tablename__ + "_" + "_".join(cols))[:48]
        + "_"
        + __import__("hashlib").sha256("_".join(cols).encode()).hexdigest()[:8],
        *[model.__table__.c[c] for c in cols],
    )
