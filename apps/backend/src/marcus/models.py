"""Explicit SQLAlchemy models for the MySQL 8.4 schema."""

from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR, DATETIME, DECIMAL, INTEGER, MEDIUMTEXT, SMALLINT
from sqlalchemy.orm import DeclarativeBase

from .security import now


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
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email_lookup_hash = Column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=True)
    email_ciphertext = Column(Text(), nullable=True)
    email_verified_at = Column(DATETIME(fsp=6), nullable=True)
    display_name = Column(String(40), nullable=False)
    bio = Column(String(300), nullable=False, default="")
    avatar_asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="active")
    terms_version = Column(String(40), nullable=False)
    terms_accepted_at = Column(DATETIME(fsp=6), nullable=False)
    deleted_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    role = Column(String(20), nullable=False, primary_key=True)
    granted_by = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthSendLimit(Base):
    __tablename__ = "auth_send_limits"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    email_lookup_hash = Column(
        CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False, primary_key=True
    )
    purpose = Column(String(30), nullable=False, primary_key=True)
    next_allowed_at = Column(DATETIME(fsp=6), nullable=False)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email_lookup_hash = Column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    email_ciphertext = Column(Text(), nullable=False)
    purpose = Column(String(30), nullable=False)
    code_hmac = Column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    delivery_code_ciphertext = Column(Text(), nullable=True)
    expires_at = Column(DATETIME(fsp=6), nullable=False)
    attempts = Column(SMALLINT(unsigned=True), nullable=False, default=0)
    max_attempts = Column(SMALLINT(unsigned=True), nullable=False, default=5)
    consumed_at = Column(DATETIME(fsp=6), nullable=True)
    delivery_status = Column(String(20), nullable=False, default="pending")
    terms_version = Column(String(40), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    client_type = Column(String(20), nullable=False)
    device_label = Column(String(100), nullable=False)
    last_seen_at = Column(DATETIME(fsp=6), nullable=False)
    absolute_expires_at = Column(DATETIME(fsp=6), nullable=False)
    revoked_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    session_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("auth_sessions.id", use_alter=True),
        nullable=False,
    )
    token_hash = Column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    parent_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("refresh_tokens.id", use_alter=True),
        nullable=True,
    )
    expires_at = Column(DATETIME(fsp=6), nullable=False)
    used_at = Column(DATETIME(fsp=6), nullable=True)
    revoked_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class City(Base):
    __tablename__ = "cities"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    code = Column(String(32), nullable=False)
    name = Column(String(80), nullable=False)
    country_code = Column(CHAR(2, charset="ascii", collation="ascii_bin"), nullable=False)
    timezone = Column(String(64), nullable=False)
    enabled = Column(Boolean(create_constraint=True), nullable=False, default=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class District(Base):
    __tablename__ = "districts"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    code = Column(String(32), nullable=False)
    name = Column(String(80), nullable=False)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Place(Base):
    __tablename__ = "places"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    district_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("districts.id", use_alter=True),
        nullable=False,
    )
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False, default="")
    latitude = Column(DECIMAL(9, 6), nullable=True)
    longitude = Column(DECIMAL(9, 6), nullable=True)
    summary = Column(String(500), nullable=False, default="")
    opening_hours_text = Column(String(1000), nullable=False, default="")
    transport_notes = Column(String(1000), nullable=False, default="")
    cover_asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    source_url = Column(String(2048), nullable=True)
    verified_at = Column(DATETIME(fsp=6), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class PlaceAsset(Base):
    __tablename__ = "place_assets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    position = Column(INTEGER(unsigned=True), nullable=False)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    title = Column(String(200), nullable=False, default="")
    description = Column(Text(), nullable=False, default="")
    organizer = Column(String(200), nullable=True)
    booking_url = Column(String(2048), nullable=True)
    price_status = Column(String(20), nullable=False)
    price_min_fen = Column(INTEGER(unsigned=True), nullable=True)
    price_max_fen = Column(INTEGER(unsigned=True), nullable=True)
    currency = Column(CHAR(3, charset="ascii", collation="ascii_bin"), nullable=False, default="CNY")
    source_url = Column(String(2048), nullable=True)
    verified_at = Column(DATETIME(fsp=6), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EventSession(Base):
    __tablename__ = "event_sessions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=False,
    )
    starts_at = Column(DATETIME(fsp=6), nullable=False)
    ends_at = Column(DATETIME(fsp=6), nullable=False)
    entry_note = Column(String(500), nullable=False, default="")
    status = Column(String(20), nullable=False, default="scheduled")
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    slug = Column(String(64), nullable=False)
    name = Column(String(40), nullable=False)
    category = Column(String(30), nullable=False)
    enabled = Column(Boolean(create_constraint=True), nullable=False, default=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    kind = Column(String(20), nullable=False)
    purpose = Column(String(30), nullable=False)
    storage_key = Column(String(255), nullable=False)
    verified_mime = Column(String(80), nullable=True)
    size_bytes = Column(BIGINT(unsigned=True), nullable=True)
    width = Column(INTEGER(unsigned=True), nullable=True)
    height = Column(INTEGER(unsigned=True), nullable=True)
    duration_ms = Column(BIGINT(unsigned=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    visibility = Column(String(20), nullable=False, default="private")
    variants = Column(JSON(), nullable=False, default=dict)
    rejection_code = Column(String(80), nullable=True)
    upload_expires_at = Column(DATETIME(fsp=6), nullable=False)
    deleted_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorArticle(Base):
    __tablename__ = "editor_articles"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    author_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    district_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("districts.id", use_alter=True),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="draft")
    published_revision_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=True)
    first_published_at = Column(DATETIME(fsp=6), nullable=True)
    published_at = Column(DATETIME(fsp=6), nullable=True)
    editorial_rank = Column(INTEGER(), nullable=False, default=0)
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    deleted_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorDraft(Base):
    __tablename__ = "editor_drafts"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    article_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    title = Column(String(150), nullable=False, default="")
    subtitle = Column(String(200), nullable=False, default="")
    summary = Column(String(500), nullable=False, default="")
    focus_type = Column(String(20), nullable=True)
    primary_place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    primary_event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    document = Column(JSON(), nullable=False, default=lambda: {"type": "doc", "content": []})
    document_schema_version = Column(SMALLINT(unsigned=True), nullable=False, default=1)
    cover_asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    tag_ids = Column(JSON(), nullable=False, default=list)
    edit_version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    last_edited_by = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorRevision(Base):
    __tablename__ = "editor_revisions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    article_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
    )
    revision_no = Column(INTEGER(unsigned=True), nullable=False)
    based_on_edit_version = Column(INTEGER(unsigned=True), nullable=False)
    title = Column(String(150), nullable=False, default="")
    subtitle = Column(String(200), nullable=False, default="")
    summary = Column(String(500), nullable=False, default="")
    focus_type = Column(String(20), nullable=False)
    primary_place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    primary_event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    document = Column(JSON(), nullable=False, default=lambda: {"type": "doc", "content": []})
    document_schema_version = Column(SMALLINT(unsigned=True), nullable=False, default=1)
    plain_text = Column(MEDIUMTEXT(), nullable=False)
    cover_asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=True,
    )
    submitted_by = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class EditorRevisionTag(Base):
    __tablename__ = "editor_revision_tags"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    revision_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    tag_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("tags.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class EditorRevisionAsset(Base):
    __tablename__ = "editor_revision_assets"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    revision_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    role = Column(String(20), nullable=False, primary_key=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class EditorReview(Base):
    __tablename__ = "editor_reviews"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    revision_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="pending")
    reviewer_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    reason_code = Column(String(80), nullable=True)
    reviewer_note = Column(Text(), nullable=True)
    automated_findings = Column(JSON(), nullable=False, default=dict)
    reviewed_at = Column(DATETIME(fsp=6), nullable=True)
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    author_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    city_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("cities.id", use_alter=True),
        nullable=False,
    )
    title = Column(String(100), nullable=False, default="")
    body_text = Column(Text(), nullable=False, default="")
    place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="draft")
    published_submission_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=True)
    first_published_at = Column(DATETIME(fsp=6), nullable=True)
    published_at = Column(DATETIME(fsp=6), nullable=True)
    version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    deleted_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class NoteImage(Base):
    __tablename__ = "note_images"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    note_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    asset_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("media_assets.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    position = Column(INTEGER(unsigned=True), nullable=False)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class NoteDraft(Base):
    __tablename__ = "note_drafts"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    note_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    title = Column(String(100), nullable=False, default="")
    body_text = Column(Text(), nullable=False, default="")
    image_ids = Column(JSON(), nullable=False, default=list)
    place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    edit_version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class NoteSubmission(Base):
    __tablename__ = "note_submissions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    note_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
    )
    submission_no = Column(INTEGER(unsigned=True), nullable=False)
    based_on_edit_version = Column(INTEGER(unsigned=True), nullable=False)
    title = Column(String(100), nullable=False, default="")
    body_text = Column(Text(), nullable=False, default="")
    image_ids = Column(JSON(), nullable=False, default=list)
    place_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("places.id", use_alter=True),
        nullable=True,
    )
    event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="pending")
    reviewer_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    reason_code = Column(String(80), nullable=True)
    reviewer_note = Column(Text(), nullable=True)
    automated_findings = Column(JSON(), nullable=False, default=dict)
    reviewed_at = Column(DATETIME(fsp=6), nullable=True)
    review_version = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class NoteReaction(Base):
    __tablename__ = "note_reactions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    note_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    kind = Column(String(20), nullable=False, primary_key=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class EditorArticleReaction(Base):
    __tablename__ = "editor_article_reactions"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    article_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    kind = Column(String(20), nullable=False, primary_key=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class EventParticipation(Base):
    __tablename__ = "event_participations"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    event_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("events.id", use_alter=True),
        nullable=False,
    )
    session_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("event_sessions.id", use_alter=True),
        nullable=True,
    )
    state = Column(String(20), nullable=False)
    attended_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    blocked_user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
        primary_key=True,
    )
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class NoteReport(Base):
    __tablename__ = "note_reports"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    reporter_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    note_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("notes.id", use_alter=True),
        nullable=False,
    )
    submission_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("note_submissions.id", use_alter=True),
        nullable=False,
    )
    reason = Column(String(30), nullable=False)
    description = Column(String(1000), nullable=False, default="")
    status = Column(String(20), nullable=False, default="open")
    resolved_by = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    resolution_note = Column(Text(), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class EditorArticleReport(Base):
    __tablename__ = "editor_article_reports"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    reporter_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    article_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_articles.id", use_alter=True),
        nullable=False,
    )
    revision_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("editor_revisions.id", use_alter=True),
        nullable=False,
    )
    reason = Column(String(30), nullable=False)
    description = Column(String(1000), nullable=False, default="")
    status = Column(String(20), nullable=False, default="open")
    resolved_by = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    resolution_note = Column(Text(), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    kind = Column(String(30), nullable=False)
    target_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    dedupe_key = Column(String(191), nullable=False)
    payload = Column(JSON(), nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="queued")
    attempts = Column(INTEGER(unsigned=True), nullable=False, default=0)
    max_attempts = Column(INTEGER(unsigned=True), nullable=False, default=3)
    available_at = Column(DATETIME(fsp=6), nullable=False)
    lease_owner = Column(String(100), nullable=True)
    lease_until = Column(DATETIME(fsp=6), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    finished_at = Column(DATETIME(fsp=6), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)
    updated_at = Column(DATETIME(fsp=6), nullable=False, default=now, onupdate=now)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=False,
    )
    operation = Column(String(80), nullable=False)
    request_key = Column(String(100), nullable=False)
    request_hash = Column(CHAR(64, charset="ascii", collation="ascii_bin"), nullable=False)
    resource_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    response_status = Column(SMALLINT(unsigned=True), nullable=False)
    expires_at = Column(DATETIME(fsp=6), nullable=False)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
    id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(
        CHAR(36, charset="ascii", collation="ascii_bin"),
        ForeignKey("users.id", use_alter=True),
        nullable=True,
    )
    action = Column(String(80), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    before_summary = Column(JSON(), nullable=True)
    after_summary = Column(JSON(), nullable=True)
    request_id = Column(CHAR(36, charset="ascii", collation="ascii_bin"), nullable=False)
    reason = Column(Text(), nullable=True)
    created_at = Column(DATETIME(fsp=6), nullable=False, default=now)


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
