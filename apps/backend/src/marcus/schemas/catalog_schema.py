"""catalog 请求数据及字段校验。"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator, model_validator

from marcus.schemas.base import ID, Input, Omittable, VersionInput


class PlaceInput(Input):
    city_id: ID
    district_id: ID
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(default="", max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    summary: str = Field(default="", max_length=500)
    opening_hours_text: str = Field(default="", max_length=1000)
    transport_notes: str = Field(default="", max_length=1000)
    cover_asset_id: ID | None = None
    source_url: str | None = Field(None, max_length=2048)
    status: Literal["draft", "active", "closed"] = "draft"
    confirm_verified: bool = False


class PlacePatch(Input):
    expected_version: int = Field(ge=1)
    district_id: Omittable[ID] = None
    name: Omittable[str] = Field(default=None, min_length=1, max_length=200)
    address: Omittable[str] = Field(default=None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    summary: Omittable[str] = Field(default=None, max_length=500)
    opening_hours_text: Omittable[str] = Field(default=None, max_length=1000)
    transport_notes: Omittable[str] = Field(default=None, max_length=1000)
    cover_asset_id: ID | None = None
    source_url: str | None = Field(None, max_length=2048)
    status: Omittable[Literal["draft", "active", "closed"]] = None
    confirm_verified: bool = False


class EventInput(Input):
    city_id: ID
    place_id: ID | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    organizer: str | None = Field(None, max_length=200)
    booking_url: str | None = Field(None, max_length=2048)
    source_url: str | None = Field(None, max_length=2048)
    price_status: Literal["free", "known", "unknown"] = "unknown"
    price_min_fen: int | None = Field(None, ge=0)
    price_max_fen: int | None = Field(None, ge=0)
    currency: Literal["CNY"] = "CNY"
    status: Literal["draft", "published", "cancelled", "ended"] = "draft"
    confirm_verified: bool = False


class EventPatch(Input):
    expected_version: int = Field(ge=1)
    place_id: ID | None = None
    title: Omittable[str] = Field(default=None, min_length=1, max_length=200)
    description: Omittable[str] = Field(default=None, max_length=20000)
    organizer: str | None = Field(None, max_length=200)
    booking_url: str | None = Field(None, max_length=2048)
    source_url: str | None = Field(None, max_length=2048)
    price_status: Omittable[Literal["free", "known", "unknown"]] = None
    price_min_fen: int | None = Field(None, ge=0)
    price_max_fen: int | None = Field(None, ge=0)
    currency: Literal["CNY"] = "CNY"
    status: Omittable[Literal["draft", "published", "cancelled", "ended"]] = None
    confirm_verified: bool = False


class SessionInput(Input):
    starts_at: datetime
    ends_at: datetime
    entry_note: str = Field(default="", max_length=500)
    status: Literal["scheduled", "cancelled", "sold_out"] = "scheduled"

    @field_validator("starts_at", "ends_at")
    @classmethod
    def utc(cls, v):
        if v.tzinfo is None:
            raise ValueError("timezone required")
        return v.astimezone(timezone.utc).replace(tzinfo=None)

    @model_validator(mode="after")
    def duration(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must follow starts_at")
        return self


class SessionPatch(SessionInput):
    expected_version: int = Field(ge=1)


class ImagesInput(VersionInput):
    asset_ids: list[ID] = Field(max_length=20)


class TagInput(Input):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=40)
    category: str = Field(default="general", max_length=30)
    enabled: bool = True


class TagPatch(Input):
    name: Omittable[str] = Field(default=None, min_length=1, max_length=40)
    category: Omittable[str] = Field(default=None, max_length=30)
    enabled: Omittable[bool] = None
