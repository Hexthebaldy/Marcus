"""note 请求数据及字段校验。"""

from typing import Annotated

from pydantic import Field, field_validator

from marcus.schemas.base import ID, Omittable, VersionInput


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
