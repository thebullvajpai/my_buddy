# speaker.py — MyBuddy Text-to-Speech Output
# Supports edge-tts (default), pyttsx3 (offline fallback), and ElevenLabs (premium).

import asyncio
import logging
import os
import tempfile
import config

log = logging.getLogger(__name__)


# ── pyttsx3 engine singleton (offline) ───────────────────────────────────────
_pyttsx3_engine = None

def _get_pyttsx3():
    global _pyttsx3_engine
    if _pyttsx3_engine is None:
        import pyttsx3
        _pyttsx3_engine = pyttsx3.init()
        _pyttsx3_engine.setProperty("rate",   config.PYTTSX3_RATE)
        _pyttsx3_engine.setProperty("volume", config.PYTTSX3_VOLUME)
    return _pyttsx3_engine


# ── Audio playback helper ─────────────────────────────────────────────────────
def _play_file(path: str):
    """Play an audio file cross-platform using pygame (preferred) or playsound."""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except ImportError:
        try:
            from playsound import playsound
            playsound(path)
        except ImportError:
            # Last-resort: OS command
            import platform
            system = platform.system()
            if system == "Darwin":
                os.system(f"afplay '{path}'")
            elif system == "Linux":
                os.system(f"mpg321 -q '{path}' 2>/dev/null || aplay '{path}' 2>/dev/null")
            else:
                os.system(f"start /min wmplayer \"{path}\"")


# ── edge-tts ──────────────────────────────────────────────────────────────────
async def _speak_edge_async(text: str):
    import edge_tts

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        communicate = edge_tts.Communicate(
            text,
            voice=config.TTS_VOICE,
            rate=config.TTS_RATE,
            volume=config.TTS_VOLUME,
        )
        await communicate.save(tmp_path)
        _play_file(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _speak_edge(text: str):
    try:
        asyncio.run(_speak_edge_async(text))
    except Exception as e:
        log.error(f"edge-tts error: {e}. Falling back to pyttsx3.")
        _speak_pyttsx3(text)


# ── pyttsx3 (offline) ─────────────────────────────────────────────────────────
def _speak_pyttsx3(text: str):
    try:
        engine = _get_pyttsx3()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        log.error(f"pyttsx3 error: {e}")


# ── ElevenLabs ────────────────────────────────────────────────────────────────
def _speak_elevenlabs(text: str):
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play

        client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            voice_id=config.ELEVENLABS_VOICE_ID,
            text=text,
            model_id=config.ELEVENLABS_MODEL,
        )
        play(audio)
    except Exception as e:
        log.error(f"ElevenLabs error: {e}. Falling back to edge-tts.")
        _speak_edge(text)


# ── Public interface ──────────────────────────────────────────────────────────
def speak(text: str):
    """
    Speak the given text using whichever TTS engine is configured.
    This is the only function you need to call from other modules.
    """
    if not text or not text.strip():
        return

    log.info(f"[TTS] '{text}'")
    engine = config.TTS_ENGINE.lower()

    if engine == "edge":
        _speak_edge(text)
    elif engine == "pyttsx3":
        _speak_pyttsx3(text)
    elif engine == "elevenlabs":
        _speak_elevenlabs(text)
    else:
        log.warning(f"Unknown TTS engine '{engine}'. Using pyttsx3.")
        _speak_pyttsx3(text)


def speak_fast(text: str):
    """
    Always uses pyttsx3 for zero-latency responses.
    Ideal for quick confirmations: "Done.", "Opening Chrome.", etc.
    """
    log.info(f"[TTS-fast] '{text}'")
    _speak_pyttsx3(text)
