# ===================================================
# OpenStream — Multi-stage Docker build
# ===================================================

# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
COPY openstream/ openstream/

RUN pip install --no-cache-dir --prefix=/install .

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim

LABEL maintainer="trickdaddy24"
LABEL description="OpenStream — Python media server with TMDB metadata and FFmpeg transcoding"

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY openstream/ openstream/
COPY pyproject.toml .

# Create data directories
RUN mkdir -p data/cache/sessions data/metadata/posters data/metadata/backdrops data/thumbnails

# Default environment
ENV OPENSTREAM_HOST=0.0.0.0 \
    OPENSTREAM_PORT=8000 \
    OPENSTREAM_DEBUG=false \
    OPENSTREAM_FFMPEG_PATH=ffmpeg \
    OPENSTREAM_FFPROBE_PATH=ffprobe \
    OPENSTREAM_MAX_TRANSCODE_SESSIONS=3

EXPOSE 8000

# Persistent data volume
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/login')" || exit 1

CMD ["uvicorn", "openstream.app:app", "--host", "0.0.0.0", "--port", "8000"]
