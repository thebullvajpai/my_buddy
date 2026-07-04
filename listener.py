# listener.py — MyBuddy Speech Input
# Handles microphone listening, ambient noise calibration, and STT conversion.

import logging
import speech_recognition as sr
import config

log = logging.getLogger(__name__)

# ── Recognizer singleton ──────────────────────────────────────────────────────
_recognizer = sr.Recognizer()
_recognizer.energy_threshold   = config.MIC_ENERGY_THRESHOLD
_recognizer.pause_threshold     = config.MIC_PAUSE_THRESHOLD
_recognizer.dynamic_energy_threshold = True


# ── Optional: local Whisper model (loaded once if configured) ─────────────────
_whisper_model = None

def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        log.info(f"Loading Whisper model '{config.WHISPER_MODEL}'…")
        _whisper_model = whisper.load_model(config.WHISPER_MODEL)
        log.info("Whisper model ready.")
    return _whisper_model


# ── Calibration ───────────────────────────────────────────────────────────────
def calibrate():
    """
    Adjust the recognizer's energy threshold for ambient background noise.
    Call once at startup before entering the main listening loop.
    """
    log.info("Calibrating microphone for ambient noise…")
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(
            source, duration=config.AMBIENT_ADJUST_SECS
        )
    log.info(f"Calibration done. Energy threshold: {_recognizer.energy_threshold:.0f}")


# ── Core listen function ──────────────────────────────────────────────────────
def listen_once() -> str | None:
    """
    Open the microphone, capture one phrase, and return its transcription.

    Returns:
        Lowercase transcribed string, or None if nothing was understood.

    Raises:
        Nothing — all exceptions are caught and logged internally so the
        calling loop never crashes on a bad audio frame.
    """
    try:
        with sr.Microphone() as source:
            log.debug("Listening…")
            audio = _recognizer.listen(
                source,
                timeout=config.MIC_LISTEN_TIMEOUT,
                phrase_time_limit=config.MIC_PHRASE_LIMIT,
            )

        return _transcribe(audio)

    except sr.WaitTimeoutError:
        log.debug("No speech detected within timeout.")
        return None
    except OSError as e:
        log.error(f"Microphone error: {e}")
        return None


def _transcribe(audio: sr.AudioData) -> str | None:
    """Send audio to the configured STT engine and return the transcript."""
    engine = config.STT_ENGINE.lower()

    if engine == "google":
        return _transcribe_google(audio)
    elif engine == "whisper":
        return _transcribe_whisper(audio)
    else:
        log.warning(f"Unknown STT engine '{engine}'. Falling back to Google.")
        return _transcribe_google(audio)


def _transcribe_google(audio: sr.AudioData) -> str | None:
    try:
        text = _recognizer.recognize_google(audio)
        log.info(f"[STT-Google] → '{text}'")
        return text.lower().strip()
    except sr.UnknownValueError:
        log.debug("Google STT: audio not understood.")
        return None
    except sr.RequestError as e:
        log.error(f"Google STT request failed: {e}")
        return None


def _transcribe_whisper(audio: sr.AudioData) -> str | None:
    import io
    import tempfile
    import os

    try:
        model = _load_whisper()
        # Whisper needs a WAV file on disk
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio.get_wav_data())
            tmp_path = tmp.name

        result = model.transcribe(tmp_path, fp16=False, language="en")
        os.unlink(tmp_path)

        text = result["text"].strip().lower()
        log.info(f"[STT-Whisper] → '{text}'")
        return text
    except Exception as e:
        log.error(f"Whisper transcription error: {e}")
        return None


# ── Wake-word helpers ─────────────────────────────────────────────────────────
def contains_wake_word(text: str) -> bool:
    return config.WAKE_WORD.lower() in text.lower()


def contains_stop_word(text: str) -> bool:
    return config.STOP_WORD.lower() in text.lower()


def strip_prefix(text: str) -> str:
    """
    Remove the command prefix ("buddy ") from the start of a transcription
    so the router receives a clean command.
    """
    prefix = config.COMMAND_PREFIX.lower() + " "
    lower  = text.lower().strip()
    if lower.startswith(prefix):
        return text[len(prefix):].strip()
    return text.strip()
