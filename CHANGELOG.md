# Changelog

All notable changes to OpenStream will be documented in this file.

---

## [v0.1.9] — 2026-03-07

### Added
- Plex-style smart playback decision system — automatically picks the lightest processing path
- **Direct Stream** mode — MKV files with H.264 + AAC are remuxed to HLS with `-c:v copy -c:a copy` (near-zero CPU, no quality loss)
- **Audio-Only Transcode** mode — H.264 video with DTS/TrueHD/AC3/FLAC audio copies the video stream and only transcodes audio to AAC (very light CPU)
- New `get_playback_decision()` function in `ffprobe.py` evaluates container, video codec, and audio codec to choose: direct play > direct stream > audio transcode > full transcode
- `remux` and `audio_transcode` profiles in `profiles.py` for the copy-based HLS modes
- Playback mode badges on the player page (green "Direct Play", green "Direct Stream", yellow "Audio Transcode", purple "Transcoding")
- Direct stream and audio transcode modes auto-start playback without requiring user to pick quality
- Full HLS audio copy support in `hls.py` (`-c:a copy` when profile specifies `audio_codec: "copy"`)

---

## [v0.1.8] — 2026-03-07

### Added
- Real-time scan progress bar for both movie and TV show library scans
- Global scan indicator bar below the navbar — visible from any page while a scan is running
- Improved progress UI on Settings page with large percentage display, animated shimmer effect, current item name, and file count
- TV scan now reports per-episode progress during processing (previously sent all events after processing was complete)
- Progress bar automatically connects via SSE on page load if a scan is in progress
- Smooth fade-out animation when scan completes

### Fixed
- TV library scan progress was broken — progress events were sent after all processing finished instead of during each episode
- Scan progress now shows show name, season, and episode number for TV scans (e.g., "Breaking Bad — S01E03")

---

## [v0.1.7] — 2026-03-07

### Fixed
- HLS segments served while still being written — added `-hls_flags temp_file` for atomic writes
- `.env` not loaded when server started from a different directory — now uses absolute path based on project root
- Transcoding too slow for real-time playback — switched all presets from `veryfast` to `ultrafast`
- HLS.js buffer underruns — increased buffer to 60s, added retry/timeout tuning for live transcoding
- Added `hls.recoverMediaError()` for non-fatal media decode errors
- Reduced default HLS segment duration from 6s to 4s for faster segment production
- Added `-hls_init_time 1` for a 1-second first segment (near-instant playback start)
- Increased FFmpeg rate-control bufsize for smoother bitrate output
- Segment wait timeout increased from 5s to 15s to handle slow encodes

---

## [v0.1.6] — 2026-03-07

### Added
- About page (`/about`) showing app version, system info, tech stack, and project links
- About route in `pages.py` with Python version, platform, database path, library/item/user counts
- About link in sidebar navigation
- About page CSS with hero card, info grid, tech stack table, and link cards

---

## [v0.1.5] — 2026-03-07

### Added
- Rotating log file at `data/logs/openstream.log` (5 MB max, 3 backups)
- Log viewer on Settings page with level filtering (All / Errors / Warnings / Info)
- API endpoints: `GET /api/logs` (admin-only, with `lines` and `level` params), `POST /api/logs/clear`
- Uvicorn access and error logs now captured in the same log file
- Timestamps and module names in log format (`YYYY-MM-DD HH:MM:SS  LEVEL  module  message`)
- Configurable via `OPENSTREAM_LOG_MAX_BYTES` and `OPENSTREAM_LOG_BACKUP_COUNT`

---

## [v0.1.4] — 2026-03-07

### Fixed
- Video player double initialization — removed `data-setup` from `<video>` tag that conflicted with `player.js` init
- HLS.js + Video.js integration — now correctly attaches to the underlying `<video>` element via `player.tech().el()`
- Browser autoplay policy blocking — no longer force-calls `play()` on load; lets user click the big play button
- Added visible error messages for player failures, HLS errors, and transcode errors
- FFmpeg `pad` filter removed from scale command (caused failures on non-standard aspect ratios)
- Audio stream mapping now optional (`0:a:0?`) so files without audio don't crash FFmpeg

---

## [v0.1.3] — 2026-03-07

### Added
- Password complexity validation with configurable policy (min length, character classes, blocklist)
- Password strength meter with live per-rule feedback (weak/fair/good/strong)
- Change password form on Settings page with match indicator
- API endpoints: `GET /api/password/policy`, `POST /api/password/validate`, `POST /api/password/change`
- New module: `openstream/passwords.py`

---

## [v0.1.2] — 2026-03-07

### Added
- Self-update system with GitHub release checking (24h cache)
- Install mode detection (git clone / pip / Docker)
- Update banner in navbar when a new version is available
- Update section on Settings page with Check / Apply buttons and release notes
- API endpoints: `POST /api/update/check`, `GET /api/update/status`, `GET /api/update/instructions`, `POST /api/update/apply`
- Background update check on server startup
- New module: `openstream/updater.py`

---

## [v0.1.1] — 2026-03-07

### Fixed
- Double `posters/posters/` path in media image URLs — added `media_url` Jinja2 filter
- Jinja2 `split` filter not found error on detail page — added `basename` Jinja2 filter

---

## [v0.1.0] — 2026-03-07

### Added
- Initial release
- Media scanner with recursive folder walking and smart filename parsing
- TMDB integration for metadata, posters, and backdrop downloads
- Direct play streaming for browser-native formats (H.264 + AAC in MP4)
- HLS transcoding via FFmpeg with 1080p / 720p / 480p quality presets
- Dark-themed web UI with responsive poster grid, detail pages, and search
- Multi-user authentication with bcrypt password hashing and session cookies
- Watch history with playback position tracking and resume support
- TV show support with season/episode organization
- Live scan progress via Server-Sent Events (SSE)
- REST API for libraries, items, search, and streaming
- Docker support with multi-stage build and docker-compose
