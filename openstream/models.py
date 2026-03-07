"""SQLAlchemy ORM models for all database tables."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, BigInteger, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class Library(Base):
    __tablename__ = "libraries"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    path = Column(String(1000), nullable=False, unique=True)
    lib_type = Column(String(20), nullable=False)  # "movie" | "tv"
    scan_status = Column(String(20), default="pending")
    last_scanned = Column(DateTime, nullable=True)
    item_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    items = relationship("MediaItem", back_populates="library", cascade="all, delete-orphan")


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True)
    library_id = Column(Integer, ForeignKey("libraries.id"), nullable=False)
    media_type = Column(String(20), nullable=False)  # "movie" | "show"
    title = Column(String(500), nullable=False)
    sort_title = Column(String(500))
    year = Column(Integer, nullable=True)
    overview = Column(Text, nullable=True)
    tagline = Column(String(500), nullable=True)
    runtime_mins = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    content_rating = Column(String(20), nullable=True)
    genres = Column(String(500), nullable=True)
    tmdb_id = Column(Integer, nullable=True, index=True)
    imdb_id = Column(String(20), nullable=True)
    poster_path = Column(String(500), nullable=True)
    backdrop_path = Column(String(500), nullable=True)
    added_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    library = relationship("Library", back_populates="items")
    files = relationship("MediaFile", back_populates="media_item", cascade="all, delete-orphan")
    seasons = relationship("Season", back_populates="show", cascade="all, delete-orphan")
    history = relationship("WatchHistory", back_populates="media_item", cascade="all, delete-orphan")


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    season_number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=True)
    overview = Column(Text, nullable=True)
    poster_path = Column(String(500), nullable=True)

    show = relationship("MediaItem", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    overview = Column(Text, nullable=True)
    runtime_mins = Column(Integer, nullable=True)
    air_date = Column(String(20), nullable=True)
    still_path = Column(String(500), nullable=True)

    season = relationship("Season", back_populates="episodes")
    file = relationship("MediaFile", back_populates="episode", uselist=False)


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    file_path = Column(String(2000), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=True)
    container = Column(String(20), nullable=True)
    video_codec = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    resolution = Column(String(20), nullable=True)
    bitrate = Column(Integer, nullable=True)
    duration_secs = Column(Integer, nullable=True)
    subtitle_langs = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    probed_at = Column(DateTime, nullable=True)

    media_item = relationship("MediaItem", back_populates="files")
    episode = relationship("Episode", back_populates="file")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    history = relationship("WatchHistory", back_populates="user", cascade="all, delete-orphan")


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_item_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    position_secs = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    watched_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="history")
    media_item = relationship("MediaItem", back_populates="history")


class TranscodeSession(Base):
    __tablename__ = "transcode_sessions"

    id = Column(String(36), primary_key=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    profile = Column(String(20))
    status = Column(String(20), default="active")
    pid = Column(Integer, nullable=True)
    output_dir = Column(String(1000))
    started_at = Column(DateTime, default=_utcnow)
