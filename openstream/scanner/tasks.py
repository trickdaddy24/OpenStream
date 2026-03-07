"""Background scan orchestrator — ties together filesystem, metadata, and ffprobe."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from openstream.config import settings
from openstream.models import Library, MediaItem, MediaFile, Season, Episode
from openstream.scanner.filesystem import scan_directory, identify_media, group_tv_episodes
from openstream.scanner.metadata import (
    search_movie, get_movie_details, search_tv, get_tv_details,
    get_season_details, download_image,
)
from openstream.transcoder.ffprobe import probe_file

logger = logging.getLogger("openstream.scanner.tasks")

# SSE progress queues keyed by library_id
progress_queues: dict[int, asyncio.Queue] = {}


async def _send_progress(library_id: int, current: int, total: int, title: str):
    q = progress_queues.get(library_id)
    if q:
        await q.put({"event": "progress", "current": current, "total": total, "title": title})


async def _process_movie(db: Session, library: Library, file_info: dict, parsed: dict):
    """Process a single movie file: fetch metadata, save to DB."""
    # Check if file already in DB
    existing = db.query(MediaFile).filter_by(file_path=file_info["file_path"]).first()
    if existing:
        return

    title = parsed["title"]
    year = parsed["year"]

    # Search TMDB
    tmdb_data = await search_movie(title, year)
    details = None
    poster_local = None
    backdrop_local = None

    if tmdb_data:
        tmdb_id = tmdb_data["id"]
        details = await get_movie_details(tmdb_id)

        # Download images
        if tmdb_data.get("poster_path"):
            dest = settings.metadata_dir / "posters" / f"{tmdb_id}_poster.jpg"
            poster_local = await download_image(tmdb_data["poster_path"], "w500", dest)

        if tmdb_data.get("backdrop_path"):
            dest = settings.metadata_dir / "backdrops" / f"{tmdb_id}_backdrop.jpg"
            backdrop_local = await download_image(tmdb_data["backdrop_path"], "w1280", dest)

    # Probe file for codec info
    probe = probe_file(file_info["file_path"])

    # Create MediaItem
    item = MediaItem(
        library_id=library.id,
        media_type="movie",
        title=details.get("title", title) if details else title,
        sort_title=(details.get("title", title) if details else title).lower(),
        year=details.get("release_date", "")[:4] if details and details.get("release_date") else year,
        overview=details.get("overview") if details else None,
        tagline=details.get("tagline") if details else None,
        runtime_mins=details.get("runtime") if details else None,
        rating=details.get("vote_average") if details else None,
        genres=", ".join(g["name"] for g in details.get("genres", [])) if details else None,
        tmdb_id=tmdb_data["id"] if tmdb_data else None,
        imdb_id=details.get("imdb_id") if details else None,
        poster_path=str(poster_local) if poster_local else None,
        backdrop_path=str(backdrop_local) if backdrop_local else None,
    )
    db.add(item)
    db.flush()

    # Create MediaFile
    mf = MediaFile(
        media_item_id=item.id,
        file_path=file_info["file_path"],
        file_size=file_info["size_bytes"],
        container=file_info["extension"].lstrip("."),
        video_codec=probe.get("video_codec") if probe else None,
        audio_codec=probe.get("audio_codec") if probe else None,
        resolution=probe.get("resolution") if probe else None,
        bitrate=probe.get("bitrate") if probe else None,
        duration_secs=probe.get("duration_secs") if probe else None,
        probed_at=datetime.now(timezone.utc) if probe else None,
    )
    db.add(mf)


async def _process_tv_library(
    db: Session, library: Library, files: list[dict],
    library_id: int, total: int,
):
    """Process all TV files in a library grouped by show.

    Sends SSE progress events as each episode file is processed so
    the frontend progress bar updates in real time.
    """
    grouped = group_tv_episodes([{"file_path": f["file_path"], **f} for f in files])

    processed = 0

    for show_title, seasons_dict in grouped.items():
        # Check if show already exists
        existing_show = db.query(MediaItem).filter_by(
            library_id=library.id, title=show_title, media_type="show"
        ).first()
        if existing_show:
            # Count the episodes we're skipping so the progress counter stays accurate
            for _sn, ep_list in seasons_dict.items():
                processed += len(ep_list)
            await _send_progress(library_id, processed, total, f"Skipped: {show_title}")
            continue

        await _send_progress(library_id, processed, total, f"Fetching metadata: {show_title}")

        # Search TMDB
        tmdb_data = await search_tv(show_title)
        details = None
        poster_local = None
        backdrop_local = None

        if tmdb_data:
            tmdb_id = tmdb_data["id"]
            details = await get_tv_details(tmdb_id)

            if tmdb_data.get("poster_path"):
                dest = settings.metadata_dir / "posters" / f"tv_{tmdb_id}_poster.jpg"
                poster_local = await download_image(tmdb_data["poster_path"], "w500", dest)

            if tmdb_data.get("backdrop_path"):
                dest = settings.metadata_dir / "backdrops" / f"tv_{tmdb_id}_backdrop.jpg"
                backdrop_local = await download_image(tmdb_data["backdrop_path"], "w1280", dest)

        show_item = MediaItem(
            library_id=library.id,
            media_type="show",
            title=details.get("name", show_title) if details else show_title,
            sort_title=(details.get("name", show_title) if details else show_title).lower(),
            overview=details.get("overview") if details else None,
            rating=details.get("vote_average") if details else None,
            genres=", ".join(g["name"] for g in details.get("genres", [])) if details else None,
            tmdb_id=tmdb_data["id"] if tmdb_data else None,
            poster_path=str(poster_local) if poster_local else None,
            backdrop_path=str(backdrop_local) if backdrop_local else None,
        )
        db.add(show_item)
        db.flush()

        for season_num, ep_files in sorted(seasons_dict.items()):
            season_details = None
            if tmdb_data:
                season_details = await get_season_details(tmdb_data["id"], season_num)

            season = Season(
                show_id=show_item.id,
                season_number=season_num,
                name=season_details.get("name") if season_details else f"Season {season_num}",
                overview=season_details.get("overview") if season_details else None,
            )
            db.add(season)
            db.flush()

            tmdb_episodes = {}
            if season_details and "episodes" in season_details:
                tmdb_episodes = {e["episode_number"]: e for e in season_details["episodes"]}

            for ef in ep_files:
                ep_num = ef.get("episode", 1)
                tmdb_ep = tmdb_episodes.get(ep_num, {})

                episode = Episode(
                    season_id=season.id,
                    episode_number=ep_num,
                    title=tmdb_ep.get("name", ef.get("file_name")),
                    overview=tmdb_ep.get("overview"),
                    runtime_mins=tmdb_ep.get("runtime"),
                    air_date=tmdb_ep.get("air_date"),
                )
                db.add(episode)
                db.flush()

                probe = probe_file(ef["file_path"])
                mf = MediaFile(
                    media_item_id=show_item.id,
                    episode_id=episode.id,
                    file_path=ef["file_path"],
                    file_size=ef["size_bytes"],
                    container=ef["extension"].lstrip("."),
                    video_codec=probe.get("video_codec") if probe else None,
                    audio_codec=probe.get("audio_codec") if probe else None,
                    resolution=probe.get("resolution") if probe else None,
                    duration_secs=probe.get("duration_secs") if probe else None,
                    probed_at=datetime.now(timezone.utc) if probe else None,
                )
                db.add(mf)

                processed += 1
                progress_title = f"{show_title} — S{season_num:02d}E{ep_num:02d}"
                await _send_progress(library_id, processed, total, progress_title)

                # Rate limit TMDB calls
                await asyncio.sleep(0.15)


async def run_library_scan(library_id: int, db: Session):
    """Main scan entry point. Discovers files, fetches metadata, inserts into DB."""
    library = db.query(Library).get(library_id)
    if not library:
        logger.error("Library %d not found", library_id)
        return

    library.scan_status = "scanning"
    db.commit()

    queue = asyncio.Queue()
    progress_queues[library_id] = queue

    try:
        # Discover files
        files = scan_directory(library.path)
        total = len(files)
        logger.info("Found %d video files in %s", total, library.path)

        if library.lib_type == "tv":
            await _process_tv_library(db, library, files, library_id, total)
        else:
            for i, f in enumerate(files):
                parsed = identify_media(f["file_path"])
                await _send_progress(library_id, i + 1, total, parsed["title"])
                await _process_movie(db, library, f, parsed)
                # Rate limit TMDB calls
                await asyncio.sleep(0.3)

        db.commit()

        # Update library stats
        library.item_count = db.query(MediaItem).filter_by(library_id=library.id).count()
        library.scan_status = "complete"
        library.last_scanned = datetime.now(timezone.utc)
        db.commit()

        await _send_progress(library_id, total, total, "Complete")
        if queue:
            await queue.put({"event": "complete"})

        logger.info("Scan complete: %d items in %s", library.item_count, library.name)

    except Exception as e:
        logger.exception("Scan failed for library %d: %s", library_id, e)
        library.scan_status = "error"
        db.commit()
        if queue:
            await queue.put({"event": "error", "message": str(e)})
    finally:
        progress_queues.pop(library_id, None)
