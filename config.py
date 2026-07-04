# config.py — MyBuddy Central Configuration
# All secrets are loaded from the .env file via python-dotenv.
# Non-secret settings (voices, timeouts, etc.) are set directly here.

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (same folder as this file)
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


def _require(key: str) -> str:
    """Read a required env var. Raises a clear error if it's missing or placeholder."""
    value = os.getenv(key, "")
    if not value or value.startswith("your_"):
        raise EnvironmentError(
            f"\n[MyBuddy] Missing or unfilled environment variable: {key}\n"
            f"  → Open your .env file and set {key}=<your actual value>"
        )
    return value


def _optional(key: str, default: str = "") -> str:
    """Read an optional env var, returning default if not set."""
    return os.getenv(key, default) or default


# ── Wake / Stop Words ────────────────────────────────────────────────────────
WAKE_WORD      = "hello"
STOP_WORD      = "goodbye"
COMMAND_PREFIX = "buddy"          # say "buddy <command>" after wake word

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY     = _require("OPENAI_API_KEY")
OPENAI_MODEL       = "gpt-4o"
OPENAI_MAX_TOKENS  = 200          # keep responses short for speaking aloud
OPENAI_TEMPERATURE = 0.7
OPENAI_HISTORY_LIMIT = 20         # max messages kept in session memory

# ── Spotify ───────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = _require("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = _require("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI  = _optional("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
SPOTIFY_SCOPE         = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing"
)
SPOTIFY_VOLUME_STEP = 10          # % to increase/decrease per command

# ── ElevenLabs (optional) ─────────────────────────────────────────────────────
ELEVENLABS_API_KEY  = _optional("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _optional("ELEVENLABS_VOICE_ID")
ELEVENLABS_MODEL    = "eleven_turbo_v2"

# ── Speech Recognition ────────────────────────────────────────────────────────
STT_ENGINE           = "google"   # "google" | "whisper"
WHISPER_MODEL        = "base"     # "tiny" | "base" | "small" | "medium"
MIC_ENERGY_THRESHOLD = 300        # lower = more sensitive microphone
MIC_PAUSE_THRESHOLD  = 0.8        # seconds of silence before phrase ends
MIC_LISTEN_TIMEOUT   = 6          # seconds to wait for speech to begin
MIC_PHRASE_LIMIT     = 12         # max seconds for a single phrase
AMBIENT_ADJUST_SECS  = 1          # seconds to calibrate ambient noise on startup

# ── Text-to-Speech ────────────────────────────────────────────────────────────
TTS_ENGINE = "edge"               # "edge" | "pyttsx3" | "elevenlabs"
TTS_VOICE  = "en-US-GuyNeural"   # edge-tts voice  (run `edge-tts --list-voices`)
TTS_RATE   = "+10%"              # edge-tts speaking rate
TTS_VOLUME = "+0%"               # edge-tts volume adjustment

PYTTSX3_RATE   = 175
PYTTSX3_VOLUME = 0.9

# ── System / Apps ─────────────────────────────────────────────────────────────
VOLUME_STEP_PERCENT = 10          # % to change system volume per command

# Add your own app shortcuts: "spoken name" → executable / shell command
CUSTOM_APPS: dict[str, str] = {
    # "photoshop": "photoshop.exe",
    # "notion":    "notion",
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL   = "INFO"              # "DEBUG" | "INFO" | "WARNING" | "ERROR"
LOG_TO_FILE = False
LOG_FILE    = "mybuddy.log"