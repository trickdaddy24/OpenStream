# Changelog

All notable changes to OpenStream will be documented in this file.

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
