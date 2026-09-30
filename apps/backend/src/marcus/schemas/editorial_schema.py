"""editorial 请求数据及字段校验。"""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from marcus.schemas.base import ID, CreateContent, Omittable, VersionInput


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


class ArticleSettingsInput(VersionInput):
    editorial_rank: int = Field(ge=-100000, le=100000)


class CreateEditorial(CreateContent):
    district_id: ID | None = None
