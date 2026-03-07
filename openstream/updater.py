"""Update checker — queries GitHub releases and manages self-update.

Checks once per 24 hours (cached). Supports git, pip, and Docker install modes.
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from openstream.config import settings

logger = logging.getLogger("openstream.updater")

GITHUB_REPO = "trickdaddy24/OpenStream"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_INTERVAL = 86400  # 24 hours in seconds
CACHE_FILE = settings.data_dir / "update_cache.json"

# Module-level state (populated on startup)
_update_info: dict | None = None


# ------------------------------------------------------------------ #
#  Install mode detection                                             #
# ------------------------------------------------------------------ #

def detect_install_mode() -> str:
    """Detect how OpenStream was installed.

    Returns one of: 'git', 'pip', 'docker', 'unknown'.
    """
    app_dir = Path(__file__).parent.parent

    # Docker — /.dockerenv exists in containers
    if Path("/.dockerenv").exists():
        return "docker"

    # Git — .git directory in the project root
    if (app_dir / ".git").exists():
        return "git"

    # Pip — installed into site-packages
    if "site-packages" in str(Path(__file__).resolve()):
        return "pip"

    return "unknown"


# ------------------------------------------------------------------ #
#  Version comparison                                                 #
# ------------------------------------------------------------------ #

def _parse_version(v: str) -> tuple[int, ...]:
    """Parse 'v0.1.2' or '0.1.2' into (0, 1, 2)."""
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _is_newer(remote: str, local: str) -> bool:
    """Return True if remote version is strictly newer than local."""
    return _parse_version(remote) > _parse_version(local)


# ------------------------------------------------------------------ #
#  Cache                                                              #
# ------------------------------------------------------------------ #

def _read_cache() -> dict | None:
    """Read the cached update check result."""
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text())
            if time.time() - data.get("checked_at", 0) < CHECK_INTERVAL:
                return data
    except Exception:
        pass
    return None


def _write_cache(data: dict):
    """Write update check result to cache."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["checked_at"] = time.time()
        CACHE_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


# ------------------------------------------------------------------ #
#  GitHub check                                                       #
# ------------------------------------------------------------------ #

async def check_for_update() -> dict:
    """Check GitHub for a newer release.

    Returns dict with keys:
        update_available (bool), current_version, remote_version,
        release_url, release_notes, install_mode, checked_at.
    """
    global _update_info

    current = settings.app_version
    install_mode = detect_install_mode()

    # Try cache first
    cached = _read_cache()
    if cached and cached.get("current_version") == current:
        _update_info = cached
        return cached

    # Fetch from GitHub
    result = {
        "update_available": False,
        "current_version": current,
        "remote_version": current,
        "release_url": f"https://github.com/{GITHUB_REPO}/releases",
        "release_notes": "",
        "install_mode": install_mode,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(GITHUB_API, headers={"Accept": "application/vnd.github.v3+json"})
            r.raise_for_status()
            data = r.json()

        remote_tag = data.get("tag_name", "")
        result["remote_version"] = remote_tag
        result["release_url"] = data.get("html_url", result["release_url"])
        result["release_notes"] = data.get("body", "")[:500]
        result["update_available"] = _is_newer(remote_tag, current)

    except Exception as e:
        logger.debug("Update check failed (non-critical): %s", e)

    _write_cache(result)
    _update_info = result
    return result


def get_cached_update_info() -> dict | None:
    """Return the last update check result (from memory or disk cache)."""
    global _update_info
    if _update_info:
        return _update_info
    cached = _read_cache()
    if cached:
        _update_info = cached
    return _update_info


# ------------------------------------------------------------------ #
#  Self-update actions                                                #
# ------------------------------------------------------------------ #

def update_via_git() -> dict:
    """Pull latest changes via git.

    Returns dict with 'success' (bool) and 'output' (str).
    """
    app_dir = Path(__file__).parent.parent
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(app_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        success = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        if success:
            logger.info("Git update successful: %s", output)
        else:
            logger.warning("Git update failed: %s", output)
        return {"success": success, "output": output, "method": "git pull"}
    except Exception as e:
        return {"success": False, "output": str(e), "method": "git pull"}


def update_via_pip() -> dict:
    """Upgrade via pip.

    Returns dict with 'success' (bool) and 'output' (str).
    """
    try:
        result = subprocess.run(
            ["pip", "install", "--upgrade",
             f"git+https://github.com/{GITHUB_REPO}.git"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        success = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        if success:
            logger.info("Pip update successful")
        else:
            logger.warning("Pip update failed: %s", output)
        return {"success": success, "output": output, "method": "pip install --upgrade"}
    except Exception as e:
        return {"success": False, "output": str(e), "method": "pip install --upgrade"}


def get_update_instructions() -> dict:
    """Return update instructions based on the detected install mode."""
    mode = detect_install_mode()
    instructions = {
        "git": {
            "mode": "git",
            "auto": True,
            "label": "Git Pull",
            "command": "git pull origin main",
            "description": "Pull the latest changes from GitHub and restart the server.",
        },
        "pip": {
            "mode": "pip",
            "auto": True,
            "label": "Pip Upgrade",
            "command": f"pip install --upgrade git+https://github.com/{GITHUB_REPO}.git",
            "description": "Upgrade the package via pip and restart the server.",
        },
        "docker": {
            "mode": "docker",
            "auto": False,
            "label": "Docker Pull",
            "command": "docker compose pull && docker compose up -d",
            "description": "Pull the latest Docker image and recreate the container.",
        },
        "unknown": {
            "mode": "unknown",
            "auto": False,
            "label": "Manual Update",
            "command": f"Download from https://github.com/{GITHUB_REPO}/releases",
            "description": "Download the latest release and replace the files manually.",
        },
    }
    return instructions.get(mode, instructions["unknown"])


def perform_update() -> dict:
    """Execute the appropriate update action.

    Returns dict with 'success', 'output', 'method', and 'restart_required'.
    """
    mode = detect_install_mode()

    if mode == "git":
        result = update_via_git()
    elif mode == "pip":
        result = update_via_pip()
    elif mode == "docker":
        return {
            "success": False,
            "output": "Docker containers cannot self-update. Run: docker compose pull && docker compose up -d",
            "method": "docker",
            "restart_required": False,
        }
    else:
        return {
            "success": False,
            "output": f"Unknown install mode. Download manually from https://github.com/{GITHUB_REPO}/releases",
            "method": "manual",
            "restart_required": False,
        }

    result["restart_required"] = result.get("success", False)

    # Clear the update cache so the next check reflects the new version
    if result.get("success"):
        try:
            CACHE_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    return result
