"""TMDB API client for fetching movie/TV metadata and images."""

import logging
from pathlib import Path

import httpx

from openstream.config import settings

logger = logging.getLogger("openstream.scanner.metadata")

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=15)
    return _client


def _params(**extra) -> dict:
    return {"api_key": settings.tmdb_api_key, **extra}


async def search_movie(title: str, year: int | None = None) -> dict | None:
    """Search TMDB for a movie. Returns best match or None."""
    client = _get_client()
    params = _params(query=title)
    if year:
        params["year"] = year
    try:
        r = await client.get(f"{settings.tmdb_base_url}/search/movie", params=params)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        logger.warning("TMDB search_movie failed for %r: %s", title, e)
        return None


async def search_tv(title: str, year: int | None = None) -> dict | None:
    """Search TMDB for a TV show. Returns best match or None."""
    client = _get_client()
    params = _params(query=title)
    if year:
        params["first_air_date_year"] = year
    try:
        r = await client.get(f"{settings.tmdb_base_url}/search/tv", params=params)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        logger.warning("TMDB search_tv failed for %r: %s", title, e)
        return None


async def get_movie_details(tmdb_id: int) -> dict | None:
    """Fetch full movie details including credits."""
    client = _get_client()
    try:
        r = await client.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}",
            params=_params(append_to_response="credits,release_dates"),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("TMDB get_movie_details failed for %d: %s", tmdb_id, e)
        return None


async def get_tv_details(tmdb_id: int) -> dict | None:
    """Fetch full TV show details."""
    client = _get_client()
    try:
        r = await client.get(
            f"{settings.tmdb_base_url}/tv/{tmdb_id}",
            params=_params(append_to_response="credits,content_ratings"),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("TMDB get_tv_details failed for %d: %s", tmdb_id, e)
        return None


async def get_season_details(tmdb_id: int, season_num: int) -> dict | None:
    """Fetch season details with episode list."""
    client = _get_client()
    try:
        r = await client.get(
            f"{settings.tmdb_base_url}/tv/{tmdb_id}/season/{season_num}",
            params=_params(),
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("TMDB season details failed for %d S%d: %s", tmdb_id, season_num, e)
        return None


async def download_image(tmdb_path: str, size: str, dest: Path) -> Path | None:
    """Download a TMDB image and save locally.

    Args:
        tmdb_path: TMDB image path (e.g., "/abc123.jpg")
        size: Image size ("w500", "w1280", "w300", "original")
        dest: Local destination path

    Returns:
        The destination path on success, None on failure.
    """
    if not tmdb_path:
        return None
    client = _get_client()
    url = f"{settings.tmdb_image_base}/{size}{tmdb_path}"
    try:
        r = await client.get(url)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return dest
    except Exception as e:
        logger.warning("Image download failed for %s: %s", url, e)
        return None
