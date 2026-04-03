"""
apps/voice/bot_script.py
=========================
Rule-based script engine for the voice bot.

This is used by agi/voice_bot.py as the reply engine until
Sprint 3 (AI brain / LLM layer) is ready.

It reads the caller's transcript and returns a scripted response
based on keywords and conversation state stored on the VoiceSession.

Replace or extend get_reply() when you wire in the real LLM.
"""

import logging
from .models import VoiceSession

log = logging.getLogger("vicidial_bot.voice.script")


# ── Sales script state machine ────────────────────────────────────────────────
# Each state has:
#   "triggers"  — keywords that move us INTO this state
#   "response"  — what the bot says when in this state
#   "next"      — default next state after saying the response

SCRIPT: dict = {
    "greeting": {
        "response": (
            "Hello! I'm calling to let you know about our special offer this month. "
            "Do you have just two minutes to hear about it?"
        ),
        "next": "qualify",
    },
    "qualify": {
        "triggers": ["yes", "sure", "okay", "go ahead", "tell me", "what is it"],
        "response": (
            "Great! We are offering a complete package starting at just nineteen "
            "dollars per month with no setup fees. Are you currently using any "
            "similar service?"
        ),
        "next": "pitch",
    },
    "pitch": {
        "triggers": ["no", "not using", "nothing", "looking"],
        "response": (
            "Perfect timing then! Our service includes unlimited support, "
            "cloud backup, and a thirty-day money-back guarantee. "
            "Would you like to take advantage of this offer today?"
        ),
        "next": "close",
    },
    "close": {
        "triggers": ["yes", "interested", "sign up", "want it", "okay"],
        "response": (
            "Wonderful! Let me transfer you to one of our account specialists "
            "who will get everything set up for you right away. "
            "Please hold for just a moment."
        ),
        "next": "transfer",
    },
    "not_interested": {
        "triggers": ["no", "not interested", "busy", "remove", "don't call"],
        "response": (
            "I completely understand. I'll remove your number from our list right away. "
            "Thank you for your time and have a wonderful day!"
        ),
        "next": "end",
    },
    "pricing": {
        "triggers": ["price", "cost", "how much", "fee", "charge", "expensive"],
        "response": (
            "Our plans start at just nineteen dollars per month for the basic package, "
            "and thirty-nine dollars for the premium. Both include a free trial period. "
            "Which would you like to know more about?"
        ),
        "next": "close",
    },
    "callback": {
        "triggers": ["call back", "later", "busy", "not now", "another time"],
        "response": (
            "No problem at all! When would be the best time for me to call you back? "
            "Morning or afternoon?"
        ),
        "next": "schedule",
    },
    "schedule": {
        "triggers": ["morning", "afternoon", "evening", "tomorrow", "monday",
                     "tuesday", "wednesday", "thursday", "friday"],
        "response": (
            "Perfect, I've made a note of that. We'll reach out at that time. "
            "Thank you for your time today, and have a great day!"
        ),
        "next": "end",
    },
    "fallback": {
        "response": (
            "I'm sorry, could you please repeat that? "
            "I want to make sure I understand you correctly."
        ),
        "next": None,   # stay in current state
    },
}

# How many fallback turns before we end the call
MAX_FALLBACK_TURNS = 3


def get_reply(user_text: str, session: VoiceSession) -> str:
    """
    Given what the caller said and the current session,
    return the bot's next response text.

    Stores conversation state as a JSON string in session.disposition
    (repurposed temporarily — Sprint 3 will give this its own field).
    """
    import json

    # Load or initialise conversation state
    try:
        state = json.loads(session.disposition) if session.disposition.startswith("{") else {}
    except Exception:
        state = {}

    current_stage   = state.get("stage", "greeting")
    fallback_count  = state.get("fallback_count", 0)

    text_lower = user_text.lower().strip()
    log.debug("Script engine: stage=%s  text=%r", current_stage, text_lower)

    # ── Check for hard exit phrases ───────────────────────────────────────────
    exit_phrases = ["goodbye", "bye", "hang up", "stop", "end call"]
    if any(p in text_lower for p in exit_phrases):
        _save_state(session, {"stage": "end", "fallback_count": 0})
        return "Thank you for calling. Have a wonderful day! Goodbye!"

    # ── Check for not-interested phrases (priority) ───────────────────────────
    not_interested = SCRIPT["not_interested"]["triggers"]
    if current_stage in ("qualify", "pitch", "close") and \
            any(t in text_lower for t in not_interested):
        _save_state(session, {"stage": "end", "fallback_count": 0})
        return SCRIPT["not_interested"]["response"]

    # ── Check for pricing question anywhere in the call ───────────────────────
    if any(t in text_lower for t in SCRIPT["pricing"]["triggers"]):
        next_stage = SCRIPT["pricing"]["next"]
        _save_state(session, {"stage": next_stage, "fallback_count": 0})
        return SCRIPT["pricing"]["response"]

    # ── Check for callback request ────────────────────────────────────────────
    if any(t in text_lower for t in SCRIPT["callback"]["triggers"]) \
            and current_stage not in ("callback", "schedule"):
        _save_state(session, {"stage": "callback", "fallback_count": 0})
        return SCRIPT["callback"]["response"]

    # ── Try to match current stage triggers ───────────────────────────────────
    stage_cfg = SCRIPT.get(current_stage, SCRIPT["fallback"])
    triggers  = stage_cfg.get("triggers", [])

    if not triggers or any(t in text_lower for t in triggers):
        # Matched — advance to next stage
        next_stage = stage_cfg.get("next")
        if next_stage and next_stage in SCRIPT:
            response = SCRIPT[next_stage]["response"]
            _save_state(session, {"stage": next_stage, "fallback_count": 0})
        else:
            response = stage_cfg["response"]
            _save_state(session, {"stage": current_stage, "fallback_count": 0})
        return response

    # ── No match — use fallback ───────────────────────────────────────────────
    fallback_count += 1
    if fallback_count >= MAX_FALLBACK_TURNS:
        _save_state(session, {"stage": "end", "fallback_count": 0})
        return (
            "I'm having a little trouble understanding. "
            "Let me connect you with one of our agents who can better assist you. "
            "Please hold."
        )

    _save_state(session, {"stage": current_stage, "fallback_count": fallback_count})
    return SCRIPT["fallback"]["response"]


def _save_state(session: VoiceSession, state: dict) -> None:
    """Persist conversation state to the session row."""
    import json
    session.disposition = json.dumps(state)
    session.save(update_fields=["disposition"])