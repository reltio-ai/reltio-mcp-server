# Stage 1: Build dependencies with uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS uv

WORKDIR /app

# Copy the requirements and source code
COPY pyproject.toml /app/
COPY uv.lock /app/
COPY main.py /app/
COPY .env /app/.env
COPY src /app/src

# Install exact dependencies from uv.lock, producing a local .venv folder with a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-editable


# Stage 2: Final runtime image
FROM python:3.13-alpine

# Create application user and set up environment
RUN adduser -D -u 1001 -h /app appuser && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy application files from build stage
COPY --from=uv --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=uv --chown=appuser:appuser /app /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["python", "main.py"]