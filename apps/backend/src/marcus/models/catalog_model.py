"""catalog 相关数据库表与字段。"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME, DECIMAL, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from marcus.core.security import now
from marcus.models.base import Base


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
