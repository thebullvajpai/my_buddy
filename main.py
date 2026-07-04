# main.py — MyBuddy Entry Point

import logging
import sys

# Force UTF-8 encoding for standard output and error to support emojis and box-drawing chars
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
from listener import listen_once, calibrate, contains_wake_word, contains_stop_word, strip_prefix
from speaker import speak, speak_fast

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        *(
            [logging.FileHandler(config.LOG_FILE)]
            if config.LOG_TO_FILE else []
        ),
    ],
)
log = logging.getLogger("MyBuddy")


# ── Console helpers ───────────────────────────────────────────────────────────
def status(msg: str):
    """Print a clearly visible status line to the console."""
    print(f"\n  ⟳  {msg}", flush=True)


def heard(text: str):
    """Print what the microphone picked up."""
    print(f"  🎤 You said   : \"{text}\"", flush=True)


def buddy_says(text: str):
    """Print what Buddy is about to say, then speak it."""
    print(f"  🤖 Buddy says : \"{text}\"", flush=True)
    speak(text)


def buddy_says_fast(text: str):
    """Print + speak instantly (pyttsx3) for quick confirmations."""
    print(f"  🤖 Buddy says : \"{text}\"", flush=True)
    speak_fast(text)


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    print("\n" + "═" * 55)
    print("   🤖  M Y B U D D Y  —  Personal AI Assistant")
    print("═" * 55)
    print(f"   Wake word  : \"{config.WAKE_WORD}\"")
    print(f"   Stop word  : \"{config.STOP_WORD}\"")
    print(f"   STT engine : {config.STT_ENGINE}")
    print(f"   TTS engine : {config.TTS_ENGINE}")
    print("═" * 55 + "\n")

    # Calibrate mic for ambient noise once at startup
    status("Calibrating microphone for background noise…")
    calibrate()

    startup_msg = "Your Buddy is ready. Say hello buddy to wake me up."
    buddy_says_fast(startup_msg)
    print()

    while True:
        try:
            # ── Phase 1: Wait for wake word ──────────────────────────────────
            status("Waiting for wake word…")
            phrase = listen_once()

            if phrase is None:
                continue   # timeout or no speech — keep waiting

            heard(phrase)

            if not contains_wake_word(phrase):
                continue   # not the wake word — keep waiting

            # ── Phase 2: Wake word detected — listen for command ─────────────
            buddy_says_fast("Yes?")

            status("Listening for your command…")
            command_raw = listen_once()

            if command_raw is None:
                buddy_says_fast("I didn't catch that. Try again.")
                continue

            heard(command_raw)

            # ── Phase 3: Check for stop word ─────────────────────────────────
            if contains_stop_word(command_raw):
                buddy_says("Goodbye! Have a great day.")
                print("\n" + "═" * 55)
                print("   MyBuddy stopped.")
                print("═" * 55 + "\n")
                break

            # ── Phase 4: Route the command ────────────────────────────────────
            command = strip_prefix(command_raw)
            status(f"Processing: \"{command}\"")

            from router import route_command
            response = route_command(command)

            buddy_says(response)

        except KeyboardInterrupt:
            print("\n\n  [Ctrl+C detected]")
            buddy_says_fast("Shutting down. Goodbye!")
            break
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}", exc_info=True)
            buddy_says_fast("Something went wrong. I'll keep listening.")


if __name__ == "__main__":
    main()