"""media 请求数据及字段校验。"""

from typing import Literal

from pydantic import Field, model_validator

from marcus.schemas.base import Input


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
