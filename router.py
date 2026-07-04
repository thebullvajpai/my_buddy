"""
router.py — MyBuddy Command Router
Detects intent from transcribed speech and dispatches to the right handler.
"""

import re
import datetime
import subprocess
import platform
import os

# ── Optional imports (gracefully degrade if not installed) ──────────────────
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ── Config ───────────────────────────────────────────────────────────────────
# Replace these with your actual keys, or load from a config.py / .env file
OPENAI_API_KEY    = "YOUR_OPENAI_API_KEY"
SPOTIFY_CLIENT_ID     = "YOUR_SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
SPOTIFY_REDIRECT_URI  = "http://localhost:8888/callback"

OS = platform.system()  # "Windows", "Darwin", "Linux"


# ── Spotify client (initialised once) ───────────────────────────────────────
def _init_spotify():
    if not SPOTIFY_AVAILABLE:
        return None
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-modify-playback-state user-read-playback-state",
    ))

sp = _init_spotify()


# ── OpenAI client (initialised once) ────────────────────────────────────────
def _init_openai():
    if not OPENAI_AVAILABLE:
        return None
    return OpenAI(api_key=OPENAI_API_KEY)

openai_client = _init_openai()

# Conversation history for multi-turn memory within a session
_chat_history = []


# ════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION
# ════════════════════════════════════════════════════════════════════════════

# Each intent is a tuple: (intent_name, list_of_keyword_patterns)
# Patterns are checked with re.search (case-insensitive) against the command.
INTENT_PATTERNS = [
    # ── Time & Date ──────────────────────────────────────────────────────────
    ("tell_time",    [r"\btime\b"]),
    ("tell_date",    [r"\bdate\b", r"\bday\b", r"\btoday\b"]),

    # ── Volume ───────────────────────────────────────────────────────────────
    ("volume_up",    [r"volume up", r"louder", r"turn up"]),
    ("volume_down",  [r"volume down", r"quieter", r"turn down", r"lower"]),
    ("volume_mute",  [r"\bmute\b", r"silence"]),

    # ── Applications ─────────────────────────────────────────────────────────
    ("open_app",     [r"\bopen\b", r"\blaunch\b", r"\bstart\b"]),

    # ── Spotify ──────────────────────────────────────────────────────────────
    ("spotify_play_song",  [r"play\s+.+\s+by\s+", r"play the song", r"play track"]),
    ("spotify_play_query", [r"\bplay\b"]),
    ("spotify_pause",      [r"\bpause\b", r"\bstop music\b"]),
    ("spotify_resume",     [r"\bresume\b", r"\bcontinue music\b"]),
    ("spotify_next",       [r"\bnext\b", r"\bskip\b"]),
    ("spotify_previous",   [r"\bprevious\b", r"\blast song\b", r"\bgo back\b"]),
    ("spotify_volume_up",  [r"spotify.*louder", r"music.*louder", r"increase music"]),
    ("spotify_volume_down",[r"spotify.*quieter", r"music.*quieter", r"decrease music"]),

    # ── General Q&A (fallback — always last) ─────────────────────────────────
    ("answer_question", [r".*"]),
]


def detect_intent(command: str) -> str:
    """Return the first matching intent name for the given command string."""
    command = command.lower().strip()
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return intent
    return "answer_question"


# ════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ════════════════════════════════════════════════════════════════════════════

# ── Time & Date ──────────────────────────────────────────────────────────────

def handle_tell_time(_command: str) -> str:
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p')}."


def handle_tell_date(_command: str) -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


# ── Volume ───────────────────────────────────────────────────────────────────

def _set_volume_windows(direction: str):
    """Simulate media key presses on Windows using nircmd or PowerShell."""
    if direction == "up":
        subprocess.call(["nircmd.exe", "changesysvolume", "5000"])
    elif direction == "down":
        subprocess.call(["nircmd.exe", "changesysvolume", "-5000"])
    elif direction == "mute":
        subprocess.call(["nircmd.exe", "mutesysvolume", "1"])


def _set_volume_mac(direction: str):
    current = int(subprocess.check_output(
        ["osascript", "-e", "output volume of (get volume settings)"]
    ).strip())
    if direction == "up":
        subprocess.call(["osascript", "-e", f"set volume output volume {min(current + 10, 100)}"])
    elif direction == "down":
        subprocess.call(["osascript", "-e", f"set volume output volume {max(current - 10, 0)}"])
    elif direction == "mute":
        subprocess.call(["osascript", "-e", "set volume with output muted"])


def _set_volume_linux(direction: str):
    if direction == "up":
        subprocess.call(["amixer", "-q", "sset", "Master", "5%+"])
    elif direction == "down":
        subprocess.call(["amixer", "-q", "sset", "Master", "5%-"])
    elif direction == "mute":
        subprocess.call(["amixer", "-q", "sset", "Master", "toggle"])


def _change_volume(direction: str) -> str:
    try:
        if OS == "Windows":
            _set_volume_windows(direction)
        elif OS == "Darwin":
            _set_volume_mac(direction)
        else:
            _set_volume_linux(direction)
        labels = {"up": "turned up", "down": "turned down", "mute": "muted"}
        return f"Volume {labels.get(direction, 'changed')}."
    except Exception as e:
        return f"Sorry, I couldn't change the volume. {e}"


def handle_volume_up(_command: str)   -> str: return _change_volume("up")
def handle_volume_down(_command: str) -> str: return _change_volume("down")
def handle_volume_mute(_command: str) -> str: return _change_volume("mute")


# ── Open Applications ─────────────────────────────────────────────────────────

# Map spoken app names → actual executables / paths
APP_MAP = {
    "chrome":       {"Windows": "chrome",         "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "firefox":      {"Windows": "firefox",        "Darwin": "open -a Firefox",         "Linux": "firefox"},
    "notepad":      {"Windows": "notepad",        "Darwin": "open -a TextEdit",        "Linux": "gedit"},
    "calculator":   {"Windows": "calc",           "Darwin": "open -a Calculator",      "Linux": "gnome-calculator"},
    "spotify":      {"Windows": "spotify",        "Darwin": "open -a Spotify",         "Linux": "spotify"},
    "vscode":       {"Windows": "code",           "Darwin": "open -a 'Visual Studio Code'", "Linux": "code"},
    "terminal":     {"Windows": "cmd",            "Darwin": "open -a Terminal",        "Linux": "gnome-terminal"},
    "file manager": {"Windows": "explorer",       "Darwin": "open ~",                  "Linux": "nautilus"},
}


def _extract_app_name(command: str) -> str:
    """Pull the app name after 'open/launch/start'."""
    match = re.search(r"(?:open|launch|start)\s+(.+)", command, re.IGNORECASE)
    return match.group(1).strip().lower() if match else ""


def handle_open_app(command: str) -> str:
    app_name = _extract_app_name(command)
    if not app_name:
        return "Which application would you like me to open?"

    # Check known app map first
    for key, paths in APP_MAP.items():
        if key in app_name:
            cmd = paths.get(OS, "")
            if cmd:
                subprocess.Popen(cmd, shell=True)
                return f"Opening {key}."

    # Fallback: try running it directly
    try:
        subprocess.Popen(app_name, shell=True)
        return f"Trying to open {app_name}."
    except Exception as e:
        return f"Sorry, I couldn't open {app_name}. {e}"


# ── Spotify ───────────────────────────────────────────────────────────────────

def _get_active_device_id():
    """Return the first active Spotify device ID, or None."""
    if not sp:
        return None
    devices = sp.devices().get("devices", [])
    for d in devices:
        if d["is_active"]:
            return d["id"]
    return devices[0]["id"] if devices else None


def handle_spotify_play_query(command: str) -> str:
    """Play a song/artist/playlist by searching Spotify."""
    if not sp:
        return "Spotify isn't set up. Please install spotipy and add your API credentials."

    # Extract what to play: "play Shape of You" → "Shape of You"
    match = re.search(r"(?:play|put on|queue)\s+(.+)", command, re.IGNORECASE)
    query = match.group(1).strip() if match else command

    try:
        results = sp.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if not tracks:
            return f"I couldn't find anything for '{query}' on Spotify."

        track = tracks[0]
        device_id = _get_active_device_id()
        sp.start_playback(device_id=device_id, uris=[track["uri"]])
        return f"Playing {track['name']} by {track['artists'][0]['name']}."
    except Exception as e:
        return f"Spotify error: {e}"


def handle_spotify_play_song(command: str) -> str:
    return handle_spotify_play_query(command)


def handle_spotify_pause(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.pause_playback()
        return "Music paused."
    except Exception as e:
        return f"Couldn't pause: {e}"


def handle_spotify_resume(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.start_playback()
        return "Resuming music."
    except Exception as e:
        return f"Couldn't resume: {e}"


def handle_spotify_next(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.next_track()
        return "Skipping to the next track."
    except Exception as e:
        return f"Couldn't skip: {e}"


def handle_spotify_previous(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.previous_track()
        return "Going back to the previous track."
    except Exception as e:
        return f"Couldn't go back: {e}"


def handle_spotify_volume_up(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        current = sp.current_playback()
        vol = min((current["device"]["volume_percent"] + 10), 100)
        sp.volume(vol)
        return f"Spotify volume set to {vol}%."
    except Exception as e:
        return f"Couldn't change Spotify volume: {e}"


def handle_spotify_volume_down(_command: str) -> str:
    if not sp:
        return "Spotify isn't configured."
    try:
        current = sp.current_playback()
        vol = max((current["device"]["volume_percent"] - 10), 0)
        sp.volume(vol)
        return f"Spotify volume set to {vol}%."
    except Exception as e:
        return f"Couldn't change Spotify volume: {e}"


# ── OpenAI Q&A ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are MyBuddy, a friendly and concise personal AI assistant.
You answer questions helpfully and keep responses short — suitable for speaking aloud.
Avoid markdown, bullet points, or formatting. Just plain natural speech.
If you don't know something, say so honestly."""


def handle_answer_question(command: str) -> str:
    if not openai_client:
        return "The OpenAI module isn't set up. Please install the openai package and add your API key."

    _chat_history.append({"role": "user", "content": command})

    # Keep history to last 10 exchanges to stay within token limits
    recent_history = _chat_history[-20:]

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + recent_history,
            max_tokens=200,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        _chat_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Sorry, I couldn't get an answer right now. {e}"


# ════════════════════════════════════════════════════════════════════════════
# DISPATCH TABLE
# Maps intent name → handler function
# ════════════════════════════════════════════════════════════════════════════

HANDLERS = {
    "tell_time":           handle_tell_time,
    "tell_date":           handle_tell_date,
    "volume_up":           handle_volume_up,
    "volume_down":         handle_volume_down,
    "volume_mute":         handle_volume_mute,
    "open_app":            handle_open_app,
    "spotify_play_song":   handle_spotify_play_song,
    "spotify_play_query":  handle_spotify_play_query,
    "spotify_pause":       handle_spotify_pause,
    "spotify_resume":      handle_spotify_resume,
    "spotify_next":        handle_spotify_next,
    "spotify_previous":    handle_spotify_previous,
    "spotify_volume_up":   handle_spotify_volume_up,
    "spotify_volume_down": handle_spotify_volume_down,
    "answer_question":     handle_answer_question,
}


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ════════════════════════════════════════════════════════════════════════════

def route_command(command: str) -> str:
    """
    Main entry point called from main.py.
    Takes a transcribed command string, detects intent, runs the handler,
    and returns a string response ready to be spoken aloud.
    """
    if not command or not command.strip():
        return "I didn't catch that. Could you repeat?"

    intent = detect_intent(command)
    handler = HANDLERS.get(intent, handle_answer_question)

    print(f"[MyBuddy] Command: '{command}' → Intent: {intent}")
    return handler(command)