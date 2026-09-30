"""engagement 请求数据及字段校验。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from marcus.schemas.base import ID, Input


class ParticipationInput(Input):
    state: Literal["interested", "attended"]
    session_id: ID | None = None
    attended_at: datetime | None = None


class ReportInput(Input):
    reason: Literal["spam", "abuse", "inaccurate", "other"]
    description: str = Field(default="", max_length=1000)


class NoteReportInput(ReportInput):
    submission_id: ID


class EditorialReportInput(ReportInput):
    revision_id: ID
