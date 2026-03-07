"""Application settings loaded from environment variables / .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OpenStream"
    app_version: str = "0.1.6"
    secret_key: str = "change-me-in-production"
    debug: bool = False

    # Paths
    data_dir: Path = Path("data")
    db_path: Path = Path("data/openstream.db")
    cache_dir: Path = Path("data/cache/sessions")
    metadata_dir: Path = Path("data/metadata")
    thumbnail_dir: Path = Path("data/thumbnails")
    log_dir: Path = Path("data/logs")

    # Logging
    log_max_bytes: int = 5_242_880  # 5 MB per log file
    log_backup_count: int = 3  # keep 3 rotated backups

    # TMDB
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base: str = "https://image.tmdb.org/t/p"

    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # Transcoding
    hls_segment_duration: int = 6
    max_transcode_sessions: int = 3

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_prefix": "OPENSTREAM_"}


settings = Settings()
