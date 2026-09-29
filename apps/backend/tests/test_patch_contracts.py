"""PATCH omission must remain distinct from explicitly clearing a field."""

from uuid import uuid4

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize(
    "model_name,field,value,base",
    [
        ("ProfileInput", "display_name", "读者", {}),
        ("NoteDraftInput", "body_text", "散步笔记", {"expected_version": 1}),
        ("EditorialDraftInput", "document", {"type": "doc"}, {"expected_version": 1}),
        ("PlacePatch", "status", "active", {"expected_version": 1}),
        ("EventPatch", "price_status", "free", {"expected_version": 1}),
    ],
)
def test_patch_non_nullable_fields_can_be_omitted_but_not_cleared(model_name, field, value, base):
    from marcus.contracts import schemas

    model = getattr(schemas, model_name)
    assert field not in model.model_validate(base).model_dump(exclude_unset=True)
    assert model.model_validate({**base, field: value}).model_dump(exclude_unset=True)[field] == value
    with pytest.raises(ValidationError):
        model.model_validate({**base, field: None})


@pytest.mark.parametrize(
    "model_name,field,maximum", [("NoteDraftInput", "image_ids", 9), ("EditorialDraftInput", "tag_ids", 10)]
)
def test_patch_lists_preserve_size_limits_and_clear_with_empty_array(model_name, field, maximum):
    from marcus.contracts import schemas

    model = getattr(schemas, model_name)
    base = {"expected_version": 1}
    assert field not in model.model_validate(base).model_dump(exclude_unset=True)
    assert model.model_validate({**base, field: []}).model_dump(exclude_unset=True)[field] == []
    ids = [str(uuid4()) for _ in range(maximum)]
    model.model_validate({**base, field: ids})
    for invalid in [None, ids + [str(uuid4())], [ids[0], ids[0]]]:
        with pytest.raises(ValidationError):
            model.model_validate({**base, field: invalid})
    public_schema = model.model_json_schema()["properties"][field]
    assert public_schema["type"] == "array"
    assert public_schema["maxItems"] == maximum


def test_patch_nullable_field_can_be_explicitly_cleared():
    from marcus.contracts.schemas import ProfileInput

    assert "avatar_asset_id" not in ProfileInput().model_dump(exclude_unset=True)
    assert ProfileInput(avatar_asset_id=None).model_dump(exclude_unset=True) == {"avatar_asset_id": None}
