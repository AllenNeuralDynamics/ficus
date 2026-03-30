FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Place executables in the environment 
ENV PATH="/app/.venv/bin:$PATH"
ENV API_NAME="ficus-dev"
ENV ZK_HOST="eng-logtools:2181"

# Run the application.
CMD ["fastapi", "run", "/app/src/ficus/main.py", "--port", "8000", "--host", "0.0.0.0"]
