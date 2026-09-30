"""统一导出模型，并在模型全部注册后加载跨表约束。"""

# 保持表的注册顺序；所有表齐备后才加载约束。
# isort: off
from .base import Base
from .auth_model import User, UserRole, AuthSendLimit, AuthChallenge, AuthSession, RefreshToken
from .catalog_model import City, District, Place, PlaceAsset, Event, EventSession, Tag
from .media_model import MediaVariant, MediaAsset
from .editorial_model import (
    EditorArticle,
    EditorDraft,
    EditorRevision,
    EditorRevisionTag,
    EditorRevisionAsset,
    EditorReview,
)
from .note_model import Note, NoteImage, NoteDraft, NoteSubmission
from .engagement_model import (
    NoteReaction,
    EditorArticleReaction,
    EventParticipation,
    UserBlock,
    NoteReport,
    EditorArticleReport,
)
from .job_model import Job, IdempotencyRecord, AuditLog
from . import constraints as constraints
# isort: on

__all__ = [
    "Base",
    "User",
    "UserRole",
    "AuthSendLimit",
    "AuthChallenge",
    "AuthSession",
    "RefreshToken",
    "City",
    "District",
    "Place",
    "PlaceAsset",
    "Event",
    "EventSession",
    "Tag",
    "MediaVariant",
    "MediaAsset",
    "EditorArticle",
    "EditorDraft",
    "EditorRevision",
    "EditorRevisionTag",
    "EditorRevisionAsset",
    "EditorReview",
    "Note",
    "NoteImage",
    "NoteDraft",
    "NoteSubmission",
    "NoteReaction",
    "EditorArticleReaction",
    "EventParticipation",
    "UserBlock",
    "NoteReport",
    "EditorArticleReport",
    "Job",
    "IdempotencyRecord",
    "AuditLog",
]
