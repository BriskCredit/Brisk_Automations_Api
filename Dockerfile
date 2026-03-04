# syntax=docker/dockerfile:1.4

# =============================================================================
# Stage 1: Build dependencies
# =============================================================================
FROM python:3.11-slim as builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml ./

# Install dependencies into a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install --python=/app/.venv/bin/python -r pyproject.toml


# =============================================================================
# Stage 2: Production image
# =============================================================================
FROM python:3.11-slim as production

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Install runtime dependencies (for PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    # FastAPI/Uvicorn settings
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Create directories for uploads and ensure permissions
RUN mkdir -p /app/uploads/reports /app/uploads/resumes /app/uploads/temp && \
    chown -R appuser:appgroup /app/uploads

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
