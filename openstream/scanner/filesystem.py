"""Walk directories and detect media files, parse titles from filenames."""

import os
import re
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".m4v", ".ts", ".mov",
    ".wmv", ".flv", ".webm", ".mpg", ".mpeg", ".m2ts",
}

MIN_FILE_SIZE = 50 * 1024 * 1024  # 50 MB — skip samples/extras

# Movie: "Title (2024).mkv" or "Title.2024.1080p.BluRay.mkv"
MOVIE_PATTERNS = [
    re.compile(r"^(.+?)\s*\((\d{4})\)"),
    re.compile(r"^(.+?)\.(\d{4})\."),
    re.compile(r"^(.+?)\s+(\d{4})\s"),
]

# TV: "Show.S01E05.Title.mkv" or "Show.1x05.mkv"
TV_PATTERNS = [
    re.compile(r"^(.+?)[.\s]+[Ss](\d{1,2})[Ee](\d{1,3})"),
    re.compile(r"^(.+?)[.\s]+(\d{1,2})x(\d{1,3})"),
]


def scan_directory(path: str) -> list[dict]:
    """Recursively find video files in a directory.

    Returns list of dicts: {file_path, file_name, extension, size_bytes}.
    """
    results = []
    root = Path(path)
    if not root.is_dir():
        return results

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = Path(dirpath) / fname
            ext = fpath.suffix.lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            if size < MIN_FILE_SIZE:
                continue
            results.append({
                "file_path": str(fpath),
                "file_name": fpath.stem,
                "extension": ext,
                "size_bytes": size,
            })
    return results


def identify_media(file_path: str) -> dict:
    """Parse a filename to extract title, year, season/episode.

    Returns dict with keys: title, year, season, episode, media_type.
    """
    p = Path(file_path)
    name = p.stem

    # Try TV patterns first (more specific)
    for pattern in TV_PATTERNS:
        m = pattern.match(name)
        if m:
            title = m.group(1).replace(".", " ").strip()
            return {
                "title": title,
                "year": None,
                "season": int(m.group(2)),
                "episode": int(m.group(3)),
                "media_type": "tv",
            }

    # Try to extract from parent directory for TV
    parts = p.parts
    for i, part in enumerate(parts):
        season_match = re.match(r"[Ss]eason\s*(\d+)", part)
        if season_match:
            season_num = int(season_match.group(1))
            show_name = parts[i - 1] if i > 0 else name
            ep_match = re.match(r"[Ee]?(\d{1,3})", name)
            ep_num = int(ep_match.group(1)) if ep_match else 1
            return {
                "title": show_name,
                "year": None,
                "season": season_num,
                "episode": ep_num,
                "media_type": "tv",
            }

    # Try movie patterns
    for pattern in MOVIE_PATTERNS:
        m = pattern.match(name)
        if m:
            title = m.group(1).replace(".", " ").strip()
            return {
                "title": title,
                "year": int(m.group(2)),
                "season": None,
                "episode": None,
                "media_type": "movie",
            }

    # Try parent directory for movie year
    parent = p.parent.name
    for pattern in MOVIE_PATTERNS:
        m = pattern.match(parent)
        if m:
            title = m.group(1).replace(".", " ").strip()
            return {
                "title": title,
                "year": int(m.group(2)),
                "season": None,
                "episode": None,
                "media_type": "movie",
            }

    # Fallback — use filename as title, no year
    title = name.replace(".", " ").replace("_", " ").strip()
    return {
        "title": title,
        "year": None,
        "season": None,
        "episode": None,
        "media_type": "movie",
    }


def group_tv_episodes(files: list[dict]) -> dict:
    """Group identified TV files by show title.

    Returns {show_title: {season_num: [file_info, ...]}}.
    """
    shows: dict[str, dict[int, list]] = {}
    for f in files:
        info = identify_media(f["file_path"])
        if info["media_type"] != "tv":
            continue
        title = info["title"]
        season = info["season"] or 1
        shows.setdefault(title, {}).setdefault(season, []).append({
            **f,
            **info,
        })
    return shows
