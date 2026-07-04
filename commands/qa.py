# qa.py — MyBuddy Q&A via OpenAI
# Answers general questions using GPT-4o with multi-turn session memory.

import logging
from openai import OpenAI
import config

log = logging.getLogger(__name__)

# ── Client ────────────────────────────────────────────────────────────────────
_client: OpenAI | None = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


# ── Session memory ────────────────────────────────────────────────────────────
# Stores the rolling conversation so Buddy remembers earlier turns.
_history: list[dict] = []


# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are MyBuddy, a friendly, witty, and concise personal AI assistant
that responds via voice. Follow these rules at all times:

1. Keep answers SHORT — 1 to 3 sentences maximum. The user hears your reply, not reads it.
2. No markdown, bullet points, code blocks, or formatting of any kind.
3. Speak naturally, like a helpful friend — not a formal document.
4. If you don't know something or it's outside your knowledge cutoff, say so honestly.
5. If the user's question is unclear, ask a single clarifying question.
6. Never repeat the user's question back to them.
"""


# ── Public interface ──────────────────────────────────────────────────────────
def answer(question: str) -> str:
    client = _get_client()   # will raise EnvironmentError cleanly if key is missing

    _history.append({"role": "user", "content": question})
    recent = _history[-config.OPENAI_HISTORY_LIMIT:]

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + recent,
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=config.OPENAI_TEMPERATURE,
        )
        reply = response.choices[0].message.content.strip()
        _history.append({"role": "assistant", "content": reply})
        log.info(f"[QA] Q: '{question}' → A: '{reply}'")
        return reply
    except Exception as e:
        log.error(f"OpenAI API error: {e}")
        return "Sorry, I ran into a problem reaching OpenAI. Please try again."


def clear_history():
    """Wipe the session conversation history (e.g. on a new session start)."""
    _history.clear()
    log.info("Conversation history cleared.")


def get_history() -> list[dict]:
    """Return a copy of the current conversation history."""
    return list(_history)
