"""Keep business operations usable without HTTP request and response objects."""

import ast
from pathlib import Path
from uuid import uuid4

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "marcus"


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            yield module
            yield from (f"{module}.{alias.name}" for alias in node.names)


def test_business_and_worker_modules_do_not_depend_on_http_controllers():
    paths = set(SOURCE.rglob("*service.py"))
    paths.update(
        SOURCE / name
        for name in [
            "core/common.py",
            "core/auth.py",
            "core/errors.py",
            "jobs/worker.py",
            "community/content_common.py",
        ]
    )
    assert paths
    for path in sorted(paths):
        for module in imported_modules(ast.parse(path.read_text())):
            assert module.split(".")[0] not in {"fastapi", "starlette"}, (path, module)
            assert not any(part in {"api", "dependencies"} for part in module.split(".")), (path, module)


def test_controllers_delegate_instead_of_querying_or_writing_database():
    persistence_methods = {
        "add",
        "add_all",
        "execute",
        "scalar",
        "scalars",
        "flush",
        "commit",
        "rollback",
        "merge",
    }
    controllers = []
    for path in SOURCE.rglob("*.py"):
        tree = ast.parse(path.read_text())
        if not any(module == "fastapi.APIRouter" for module in imported_modules(tree)):
            continue
        controllers.append(path)
        for module in imported_modules(tree):
            assert not module.startswith(("sqlalchemy", "marcus.database")), (path, module)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in persistence_methods, (path, node.lineno, node.func.attr)
    assert len(controllers) >= 8


def test_worker_uses_business_services_for_validation_and_publication():
    modules = set(imported_modules(ast.parse((SOURCE / "jobs/worker.py").read_text())))
    assert "marcus.notes.service" in modules
    assert "marcus.editorials.service" in modules
    assert "marcus.moderation.service" in modules


async def test_note_service_create_retry_save_and_conflict_without_http_objects(api, db, location):
    from marcus.contracts.schemas import CreateContent, NoteDraftInput
    from marcus.core.db import SessionFactory
    from marcus.core.errors import ServiceError
    from marcus.database.models import User
    from marcus.notes import service

    actor = await api.login()
    key = str(uuid4())
    async with SessionFactory.begin() as session:
        user = await session.get(User, actor.id)
        assert user is not None
        first = await service.create(CreateContent(city_id=location["city_id"]), user, session, key)
        repeated = await service.create(CreateContent(city_id=location["city_id"]), user, session, key)
        assert first["note_id"] == repeated["note_id"]
        saved = await service.save(
            first["note_id"],
            NoteDraftInput(expected_version=first["edit_version"], body_text="服务层直接保存"),
            user,
            session,
        )
        assert saved["body_text"] == "服务层直接保存"
        with pytest.raises(ServiceError) as conflict:
            await service.save(
                first["note_id"],
                NoteDraftInput(expected_version=first["edit_version"], body_text="过期修改"),
                user,
                session,
            )
        assert conflict.value.status_code == 409
        assert conflict.value.code == "version_conflict"
    assert await db.scalar("SELECT COUNT(*) FROM notes WHERE author_id=:id", {"id": actor.id}) == 1
    assert (
        await db.scalar("SELECT body_text FROM note_drafts WHERE note_id=:id", {"id": first["note_id"]})
        == "服务层直接保存"
    )
