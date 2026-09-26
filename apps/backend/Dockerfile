FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev
RUN useradd --create-home marcus && chown -R marcus:marcus /app
USER marcus
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "marcus.main:app", "--host", "0.0.0.0", "--port", "8000"]
