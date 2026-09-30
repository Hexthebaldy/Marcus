"""auth 请求数据及字段校验。"""

from typing import Literal

from pydantic import EmailStr, Field, model_validator

from marcus.schemas.base import ID, Input, Omittable


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
