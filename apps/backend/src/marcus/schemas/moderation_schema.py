"""moderation 请求数据及字段校验。"""

from typing import Literal

from pydantic import Field, model_validator

from marcus.schemas.base import Input, VersionInput


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


class HideInput(VersionInput):
    reason: str = Field(min_length=1, max_length=1000)


class ResolutionInput(Input):
    status: Literal["resolved", "dismissed"]
    resolution_note: str = Field(min_length=1, max_length=5000)


class SuspendInput(Input):
    reason: str = Field(min_length=1, max_length=1000)
