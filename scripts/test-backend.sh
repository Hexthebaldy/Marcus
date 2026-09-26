#!/usr/bin/env bash
set -euo pipefail

: "${MARCUS_TEST_DATABASE_URL:?Set a dedicated MySQL URL whose database name ends in _test}"
task_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${task_repo_root}/apps/backend"

# Validate the destructive test target before running migrations or pytest.
uv run python - <<'PY'
import os
from sqlalchemy.engine import make_url

url = make_url(os.environ['MARCUS_TEST_DATABASE_URL'])
if url.get_backend_name() != 'mysql' or not (url.database or '').endswith('_test'):
    raise SystemExit('Refusing to test against anything other than a dedicated MySQL *_test database')
PY

MARCUS_DATABASE_URL="${MARCUS_TEST_DATABASE_URL}" uv run alembic upgrade head
uv run pytest "$@"
