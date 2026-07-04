# commands/spotify.py — MyBuddy Spotify Controls
# Full playback control via the Spotify Web API using spotipy.

import logging
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import config

log = logging.getLogger(__name__)

# ── Client singleton ──────────────────────────────────────────────────────────
_sp: spotipy.Spotify | None = None

def _get_sp() -> spotipy.Spotify:
    global _sp
    if _sp is None:
        _sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=config.SPOTIFY_REDIRECT_URI,
                scope=config.SPOTIFY_SCOPE,
            )
        )
    return _sp

def _not_configured() -> str:
    return (
        "Spotify isn't configured yet. "
        "Add your credentials to config.py and make sure spotipy is installed."
    )


# ── Device helpers ─────────────────────────────────────────────────────────────
def _get_device_id() -> str | None:
    """Return the ID of the active Spotify device, or the first available one."""
    try:
        devices = _get_sp().devices().get("devices", [])
        for d in devices:
            if d["is_active"]:
                return d["id"]
        return devices[0]["id"] if devices else None
    except Exception:
        return None


def _current_volume() -> int:
    """Return the current Spotify playback volume (0-100), or 50 as default."""
    try:
        playback = _get_sp().current_playback()
        if playback and playback.get("device"):
            return playback["device"]["volume_percent"]
    except Exception:
        pass
    return 50


# ── Playback ──────────────────────────────────────────────────────────────────
def play_query(command: str) -> str:
    """
    Search Spotify for a track, artist, or playlist and start playback.
    Extracts the search term from commands like "play Shape of You by Ed Sheeran".
    """
    try:
        sp = _get_sp()
    except RuntimeError:
        return _not_configured()

    # Extract search query from command
    match = re.search(
        r"(?:play|put on|queue|start playing)\s+(.+)", command, re.IGNORECASE
    )
    query = match.group(1).strip() if match else command.strip()

    # Remove filler words
    query = re.sub(r"\b(some|the song|the track|music by)\b", "", query, flags=re.IGNORECASE).strip()

    if not query:
        return "What would you like me to play on Spotify?"

    try:
        results = sp.search(q=query, type="track,artist,playlist", limit=1)

        # Prefer track results
        tracks    = results.get("tracks", {}).get("items", [])
        artists   = results.get("artists", {}).get("items", [])
        playlists = results.get("playlists", {}).get("items", [])

        device_id = _get_device_id()

        if tracks:
            track = tracks[0]
            sp.start_playback(device_id=device_id, uris=[track["uri"]])
            artist = track["artists"][0]["name"]
            return f"Playing {track['name']} by {artist}."

        if artists:
            artist = artists[0]
            sp.start_playback(device_id=device_id, context_uri=artist["uri"])
            return f"Playing music by {artist['name']}."

        if playlists:
            playlist = playlists[0]
            sp.start_playback(device_id=device_id, context_uri=playlist["uri"])
            return f"Playing the playlist {playlist['name']}."

        return f"I couldn't find anything for '{query}' on Spotify."

    except spotipy.exceptions.SpotifyException as e:
        if "NO_ACTIVE_DEVICE" in str(e):
            return "No active Spotify device found. Open Spotify on a device first."
        log.error(f"Spotify play error: {e}")
        return "Something went wrong with Spotify playback."
    except Exception as e:
        log.error(f"Unexpected Spotify error: {e}")
        return "Sorry, I couldn't play that on Spotify."


def pause() -> str:
    try:
        _get_sp().pause_playback()
        return "Music paused."
    except spotipy.exceptions.SpotifyException as e:
        if "NOT_PLAYING" in str(e):
            return "Nothing is playing right now."
        return f"Couldn't pause: {e}"


def resume() -> str:
    try:
        _get_sp().start_playback()
        return "Resuming music."
    except RuntimeError:
        return _not_configured()
    except spotipy.exceptions.SpotifyException as e:
        if "NO_ACTIVE_DEVICE" in str(e):
            return "No active Spotify device found. Open Spotify on a device first."
        return f"Couldn't resume: {e}"


def next_track() -> str:
    try:
        _get_sp().next_track()
        return "Skipping to the next track."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        log.error(f"Spotify next error: {e}")
        return "Couldn't skip the track."


def previous_track() -> str:
    try:
        _get_sp().previous_track()
        return "Going back to the previous track."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        log.error(f"Spotify previous error: {e}")
        return "Couldn't go back."


def volume_up() -> str:
    try:
        new_vol = min(_current_volume() + config.SPOTIFY_VOLUME_STEP, 100)
        _get_sp().volume(new_vol, device_id=_get_device_id())
        return f"Spotify volume up to {new_vol}%."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        log.error(f"Spotify volume up error: {e}")
        return "Couldn't adjust Spotify volume."


def volume_down() -> str:
    try:
        new_vol = max(_current_volume() - config.SPOTIFY_VOLUME_STEP, 0)
        _get_sp().volume(new_vol, device_id=_get_device_id())
        return f"Spotify volume down to {new_vol}%."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        log.error(f"Spotify volume down error: {e}")
        return "Couldn't adjust Spotify volume."


def what_is_playing() -> str:
    """Tell the user what is currently playing."""
    try:
        sp = _get_sp()
        playback = sp.current_playback()
        if not playback or not playback.get("is_playing"):
            return "Nothing is playing on Spotify right now."
        track  = playback["item"]
        artist = track["artists"][0]["name"]
        return f"Currently playing {track['name']} by {artist}."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        log.error(f"Spotify what_is_playing error: {e}")
        return "I couldn't check what's playing right now."


def shuffle_on() -> str:
    try:
        _get_sp().shuffle(True, device_id=_get_device_id())
        return "Shuffle turned on."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        return f"Couldn't enable shuffle: {e}"


def shuffle_off() -> str:
    try:
        _get_sp().shuffle(False, device_id=_get_device_id())
        return "Shuffle turned off."
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        return f"Couldn't disable shuffle: {e}"


def set_repeat(mode: str = "track") -> str:
    """mode: 'track' | 'context' | 'off'"""
    try:
        _get_sp().repeat(mode, device_id=_get_device_id())
        labels = {"track": "Repeating current track.", "context": "Repeating playlist.", "off": "Repeat off."}
        return labels.get(mode, "Repeat mode changed.")
    except RuntimeError:
        return _not_configured()
    except Exception as e:
        return f"Couldn't set repeat: {e}"
