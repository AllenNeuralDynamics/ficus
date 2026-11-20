FROM python:3.12-slim

# Install uv (pinned, so a build is reproducible).
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Dependencies first, in their own layer: a code change doesn't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# Then the application.
COPY . /app
RUN uv sync --frozen --no-dev --no-cache

# Place executables in the environment
ENV PATH="/app/.venv/bin:$PATH"

# Settings come from the environment at run time: see .env.example.
CMD ["fastapi", "run", "/app/src/ficus/main.py", "--port", "8000", "--host", "0.0.0.0"]
