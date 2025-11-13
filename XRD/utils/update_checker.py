"""
Update Checker Module
=====================
Checks for new PRISMA releases via GitHub API and notifies users.

Features:
- Queries GitHub releases API for latest version
- Compares with current installed version
- Respects user opt-out preferences
- Handles offline mode gracefully
- Caches results to avoid API rate limits
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import logging

from XRD import __version__

logger = logging.getLogger(__name__)

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com/repos/wdgonzo/PRISMA/releases/latest"
CACHE_DURATION_HOURS = 24  # Cache update check results for 24 hours
USER_AGENT = f"PRISMA/{__version__}"


def parse_version(version_string: str) -> tuple:
    """
    Parse version string to tuple for comparison.

    Args:
        version_string: Version string (e.g., "0.3.0-beta", "1.0.0")

    Returns:
        Tuple of (major, minor, patch, prerelease) for comparison

    Examples:
        >>> parse_version("0.3.0-beta")
        (0, 3, 0, 'beta')
        >>> parse_version("1.0.0")
        (1, 0, 0, '')
    """
    # Remove 'v' prefix if present
    version_string = version_string.lstrip('v')

    # Split on '-' to separate version from prerelease
    parts = version_string.split('-')
    version_part = parts[0]
    prerelease = parts[1] if len(parts) > 1 else ''

    # Parse major.minor.patch
    version_nums = version_part.split('.')
    major = int(version_nums[0]) if len(version_nums) > 0 else 0
    minor = int(version_nums[1]) if len(version_nums) > 1 else 0
    patch = int(version_nums[2]) if len(version_nums) > 2 else 0

    return (major, minor, patch, prerelease)


def is_newer_version(current: str, latest: str) -> bool:
    """
    Check if latest version is newer than current version.

    Args:
        current: Current installed version
        latest: Latest available version

    Returns:
        True if latest is newer than current

    Examples:
        >>> is_newer_version("0.1.0-beta", "0.3.0-beta")
        True
        >>> is_newer_version("1.0.0", "0.3.0-beta")
        False
        >>> is_newer_version("0.3.0-beta", "0.3.0")
        True  # Release is newer than beta
    """
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)

    # Compare major.minor.patch first
    if current_tuple[:3] != latest_tuple[:3]:
        return latest_tuple[:3] > current_tuple[:3]

    # If versions are same, release (no prerelease) is newer than prerelease
    current_prerelease = current_tuple[3]
    latest_prerelease = latest_tuple[3]

    if current_prerelease and not latest_prerelease:
        return True  # Latest is release, current is prerelease
    elif not current_prerelease and latest_prerelease:
        return False  # Current is release, latest is prerelease
    else:
        # Both are same type (both release or both prerelease)
        return False


def check_for_updates(force: bool = False, cache_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Check GitHub for new PRISMA releases.

    Args:
        force: Force check even if cached result exists
        cache_file: Path to cache file (default: ~/.prisma/update_cache.json)

    Returns:
        Dictionary with update info if update available, None otherwise:
        {
            'update_available': bool,
            'current_version': str,
            'latest_version': str,
            'release_url': str,
            'download_url': str,  # URL to installer .exe
            'release_notes_url': str,
            'published_at': str,
            'checked_at': str (ISO timestamp)
        }

    Returns None if:
        - No update available
        - Network error (offline mode)
        - API error
        - Cache valid and force=False
    """
    if cache_file is None:
        # Default cache location
        cache_dir = os.path.expanduser("~/.prisma")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "update_cache.json")

    # Check cache first (unless forced)
    if not force and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)

            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached_data.get('checked_at', ''))
            if datetime.now() - cache_time < timedelta(hours=CACHE_DURATION_HOURS):
                logger.info("Using cached update check result")
                return cached_data if cached_data.get('update_available') else None
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Invalid cache file, will check for updates: {e}")

    # Query GitHub API
    try:
        logger.info("Checking for updates from GitHub...")
        request = Request(GITHUB_API_URL, headers={'User-Agent': USER_AGENT})

        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        latest_version = data['tag_name']  # e.g., "v0.3.0-beta"
        current_version = __version__  # e.g., "0.3.0-beta"

        # Check if update available
        update_available = is_newer_version(current_version, latest_version)

        # Find installer download URL
        download_url = None
        for asset in data.get('assets', []):
            if asset['name'].endswith('.exe'):
                download_url = asset['browser_download_url']
                break

        result = {
            'update_available': update_available,
            'current_version': current_version,
            'latest_version': latest_version.lstrip('v'),
            'release_url': data['html_url'],
            'download_url': download_url,
            'release_notes_url': data['html_url'],
            'published_at': data['published_at'],
            'checked_at': datetime.now().isoformat()
        }

        # Cache result
        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2)
        except IOError as e:
            logger.warning(f"Could not cache update result: {e}")

        if update_available:
            logger.info(f"Update available: {current_version} -> {latest_version}")
            return result
        else:
            logger.info("PRISMA is up to date")
            return None

    except HTTPError as e:
        if e.code == 404:
            logger.warning("No releases found on GitHub")
        else:
            logger.warning(f"HTTP error checking for updates: {e.code}")
        return None

    except URLError as e:
        logger.info(f"Network error checking for updates (offline?): {e.reason}")
        return None

    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing GitHub API response: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return None


def clear_update_cache(cache_file: Optional[str] = None) -> bool:
    """
    Clear the update check cache file.

    Args:
        cache_file: Path to cache file (default: ~/.prisma/update_cache.json)

    Returns:
        True if cache was cleared, False if cache didn't exist
    """
    if cache_file is None:
        cache_file = os.path.expanduser("~/.prisma/update_cache.json")

    try:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logger.info("Update cache cleared")
            return True
        else:
            logger.info("No update cache to clear")
            return False
    except OSError as e:
        logger.error(f"Error clearing update cache: {e}")
        return False


if __name__ == "__main__":
    # Test the update checker
    logging.basicConfig(level=logging.INFO)

    print(f"Current PRISMA version: {__version__}")
    print("Checking for updates...")

    update_info = check_for_updates(force=True)

    if update_info:
        print("\n" + "="*60)
        print("UPDATE AVAILABLE!")
        print("="*60)
        print(f"Current version: {update_info['current_version']}")
        print(f"Latest version:  {update_info['latest_version']}")
        print(f"Release notes:   {update_info['release_notes_url']}")
        if update_info['download_url']:
            print(f"Download:        {update_info['download_url']}")
        print("="*60)
    else:
        print("\nPRISMA is up to date!")
