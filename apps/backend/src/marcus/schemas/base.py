from typing import Annotated, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
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


class CreateContent(Input):
    city_id: ID


class VersionInput(Input):
    expected_version: int = Field(ge=1)


class PublishInput(Input):
    expected_edit_version: int = Field(ge=1)
