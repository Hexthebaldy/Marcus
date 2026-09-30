"""所有模型注册完成后添加跨表约束和索引；模块首次导入时执行一次。"""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)

from marcus.models.auth_model import AuthChallenge, AuthSession, RefreshToken, User, UserRole
from marcus.models.catalog_model import City, District, Event, EventSession, Place, PlaceAsset, Tag
from marcus.models.editorial_model import EditorArticle, EditorDraft, EditorReview, EditorRevision
from marcus.models.engagement_model import (
    EditorArticleReaction,
    EditorArticleReport,
    EventParticipation,
    NoteReaction,
    NoteReport,
    UserBlock,
)
from marcus.models.job_model import AuditLog, IdempotencyRecord, Job
from marcus.models.media_model import MediaAsset
from marcus.models.note_model import Note, NoteImage, NoteSubmission


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
