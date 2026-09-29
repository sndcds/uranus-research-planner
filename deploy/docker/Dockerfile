FROM ghcr.io/astral-sh/uv:0.12.5 AS uv
FROM python:3.13.15-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
USER 65532:65532
EXPOSE 8090
CMD ["/app/.venv/bin/uvicorn", "research_planner.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8090", "--workers", "1", "--no-access-log"]
