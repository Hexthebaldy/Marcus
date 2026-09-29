from datetime import datetime, timezone
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

ID = Annotated[
    str, Field(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
]


T = TypeVar("T")


def reject_null(value: object) -> object:
    if value is None:
        raise ValueError("null is not allowed")
    return value


# PATCH fields may be omitted (represented by None), but an explicit null is invalid.
# Exclude that internal default from the public schema; validation rejects supplied nulls.
Omittable = Annotated[T | SkipJsonSchema[None], BeforeValidator(reject_null)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChallengeInput(Input):
    email: EmailStr
    purpose: Literal["login", "delete_account"] = "login"
    terms_version: str | None = Field(None, max_length=40)

    @model_validator(mode="after")
    def terms(self):
        if self.purpose == "login" and not self.terms_version:
            raise ValueError("terms_version required")
        return self


class VerifyInput(Input):
    challenge_id: ID
    code: str = Field(pattern=r"^\d{6}$")
    device_label: str = Field(min_length=1, max_length=100)
    client_type: Literal["mobile", "editor_web"]


class RefreshInput(Input):
    refresh_token: str | None = Field(None, max_length=200)


class DeleteAccountInput(Input):
    challenge_id: ID
    code: str = Field(pattern=r"^\d{6}$")


class ProfileInput(Input):
    display_name: Omittable[str] = Field(default=None, min_length=1, max_length=40)
    bio: Omittable[str] = Field(default=None, max_length=300)
    avatar_asset_id: ID | None = None
    city_id: ID | None = None


class CreateContent(Input):
    city_id: ID


class VersionInput(Input):
    expected_version: int = Field(ge=1)


class PublishInput(Input):
    expected_edit_version: int = Field(ge=1)


class NoteDraftInput(VersionInput):
    title: Omittable[str] = Field(default=None, max_length=100)
    body_text: Omittable[str] = Field(default=None, max_length=5000)
    image_ids: Omittable[Annotated[list[ID], Field(max_length=9)]] = None
    place_id: ID | None = None
    event_id: ID | None = None

    @field_validator("image_ids")
    @classmethod
    def unique(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("duplicate image")
        return v


class EditorialDraftInput(VersionInput):
    title: Omittable[str] = Field(default=None, max_length=150)
    subtitle: Omittable[str] = Field(default=None, max_length=200)
    summary: Omittable[str] = Field(default=None, max_length=500)
    focus_type: Literal["place", "event"] | None = None
    primary_place_id: ID | None = None
    primary_event_id: ID | None = None
    document: Omittable[dict[str, Any]] = None
    document_schema_version: Literal[1] = 1
    cover_asset_id: ID | None = None
    tag_ids: Omittable[Annotated[list[ID], Field(max_length=10)]] = None

    @model_validator(mode="after")
    def focus_group(self):
        group = {"focus_type", "primary_place_id", "primary_event_id"}
        if self.model_fields_set & group and not group <= self.model_fields_set:
            raise ValueError("send focus_type and both primary IDs together")
        if self.tag_ids is not None and len(self.tag_ids) != len(set(self.tag_ids)):
            raise ValueError("duplicate tag")
        return self


class DecisionInput(Input):
    decision: Literal["approve", "reject"]
    expected_review_version: int = Field(ge=1)
    reason_code: str | None = Field(None, max_length=80)
    note: str | None = Field(None, max_length=5000)

    @model_validator(mode="after")
    def reason(self):
        if self.decision == "reject" and not self.reason_code:
            raise ValueError("reason_code required")
        return self


class UploadInput(Input):
    kind: Literal["image", "video"]
    purpose: Literal["note_image", "editorial_media", "place_image", "avatar"]
    file_name: str = Field(min_length=1, max_length=200)
    mime_type: str = Field(max_length=80)
    size_bytes: int = Field(gt=0, le=200 * 1024 * 1024)

    @model_validator(mode="after")
    def media(self):
        if self.kind == "video":
            if self.purpose != "editorial_media" or self.mime_type not in ["video/mp4", "video/quicktime"]:
                raise ValueError("unsupported video")
        elif self.size_bytes > 20 * 1024 * 1024 or self.mime_type not in [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]:
            raise ValueError("unsupported image")
        return self


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


class ParticipationInput(Input):
    state: Literal["interested", "attended"]
    session_id: ID | None = None
    attended_at: datetime | None = None


class HideInput(VersionInput):
    reason: str = Field(min_length=1, max_length=1000)


class ReportInput(Input):
    reason: Literal["spam", "abuse", "inaccurate", "other"]
    description: str = Field(default="", max_length=1000)


class NoteReportInput(ReportInput):
    submission_id: ID


class EditorialReportInput(ReportInput):
    revision_id: ID


class ResolutionInput(Input):
    status: Literal["resolved", "dismissed"]
    resolution_note: str = Field(min_length=1, max_length=5000)


class SuspendInput(Input):
    reason: str = Field(min_length=1, max_length=1000)


class ArticleSettingsInput(VersionInput):
    editorial_rank: int = Field(ge=-100000, le=100000)


class CreateEditorial(CreateContent):
    district_id: ID | None = None
