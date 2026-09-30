"""Public response contracts, separate from SQLAlchemy rows and private working state."""

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_serializer


class Output(BaseModel):
    @field_serializer("*", when_used="json")
    def public_time(self, value: Any):
        if isinstance(value, datetime):
            aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
            return aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


T = TypeVar("T")


class Page(Output, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class City(Output):
    id: str
    code: str
    name: str
    timezone: str


class District(Output):
    id: str
    city_id: str
    name: str
    code: str


class Tag(Output):
    id: str
    slug: str
    name: str
    category: str
    enabled: bool


class MediaVariant(Output):
    url: str
    expires_at: datetime | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    duration_ms: int | None = None


class MediaAsset(Output):
    id: str
    kind: Literal["image", "video"]
    status: Literal["pending", "processing", "ready", "rejected", "deleted"]
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    variants: dict[str, MediaVariant] = Field(default_factory=dict)
    playback: MediaVariant | None = None
    poster: MediaVariant | None = None
    error_code: str | None = None


class Author(Output):
    id: str
    display_name: str
    avatar: MediaAsset | None = None


class User(Author):
    bio: str
    city: City | None = None
    roles: list[str]


class Reactions(Output):
    like_count: int
    bookmark_count: int
    liked: bool
    bookmarked: bool


class Coordinates(Output):
    latitude: float
    longitude: float


class Place(Output):
    id: str
    name: str
    city: City
    district: District
    address: str
    coordinates: Coordinates | None = None
    summary: str
    opening_hours_text: str
    transport_notes: str
    cover: MediaAsset | None = None
    gallery: list[MediaAsset]
    status: str
    verified_at: datetime | None = None
    version: int


class EventSession(Output):
    id: str
    event_id: str
    starts_at: datetime
    ends_at: datetime
    entry_note: str
    status: str
    version: int


class Price(Output):
    status: Literal["unknown", "free", "known"]
    min_fen: int | None = None
    max_fen: int | None = None
    currency: str


class Event(Output):
    id: str
    city: City
    title: str
    description: str
    organizer: str | None = None
    place: Place | None = None
    price: Price
    booking_url: str | None = None
    status: str
    verified_at: datetime | None = None
    upcoming_sessions: list[EventSession]
    version: int


class Note(Output):
    id: str
    kind: Literal["note"]
    title: str
    body_text: str
    images: list[MediaAsset]
    cover: MediaAsset | None = None
    place: Place | None = None
    event: Event | None = None
    author: Author
    city: City
    first_published_at: datetime
    published_at: datetime
    published_submission_id: str
    version: int
    reactions: Reactions


class Editorial(Output):
    id: str
    kind: Literal["editorial"]
    revision_id: str
    title: str
    subtitle: str
    summary: str
    focus_type: Literal["place", "event"]
    document: dict[str, Any]
    document_schema_version: Literal[1]
    media: list[MediaAsset]
    cover: MediaAsset | None = None
    place: Place | None = None
    event: Event | None = None
    tags: list[Tag]
    editor: Author
    city: City
    district: District | None = None
    first_published_at: datetime
    published_at: datetime
    reactions: Reactions


class NoteDraft(Output):
    note_id: str
    version: int
    edit_version: int
    title: str
    body_text: str
    image_ids: list[str]
    place_id: str | None = None
    event_id: str | None = None
    updated_at: datetime
    latest_submission: dict[str, Any] | None = None
    media: list[MediaAsset]


class AuthResult(Output):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    session_id: str
    user: User


class Challenge(Output):
    challenge_id: str
    expires_in_seconds: int
    resend_after_seconds: int


class Publication(Output):
    submission_id: str | None = None
    review_status: Literal["pending", "approved", "rejected"] | None = None
    is_current_published: bool
    reason_code: str | None = None
