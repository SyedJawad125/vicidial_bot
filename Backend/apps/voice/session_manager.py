"""
apps/voice/session_manager.py
==============================
Helper that creates / updates VoiceSession and TranscriptLog rows.
Keeps database logic out of the AGI script.
"""

import logging
from django.utils import timezone
from .models import VoiceSession, TranscriptLog

log = logging.getLogger("vicidial_bot.voice.session")


class VoiceSessionManager:

    @staticmethod
    def create(unique_id: str, channel: str = "", caller_id: str = "",
               campaign_id: str = "", language: str = "en") -> VoiceSession:
        session, _ = VoiceSession.objects.get_or_create(
            unique_id=unique_id,
            defaults={
                "channel":    channel,
                "caller_id":  caller_id,
                "campaign_id": campaign_id,
                "language":   language,
                "status":     "active",
            },
        )
        log.info("VoiceSession created: %s", session.id)
        return session

    @staticmethod
    def complete(session: VoiceSession, disposition: str = "") -> None:
        session.status      = "completed"
        session.ended_at    = timezone.now()
        session.disposition = disposition
        if session.started_at:
            session.duration_sec = int(
                (session.ended_at - session.started_at).total_seconds()
            )
        session.save(update_fields=["status", "ended_at", "disposition", "duration_sec"])
        log.info("VoiceSession completed: %s", session.id)

    @staticmethod
    def fail(session: VoiceSession, error_message: str) -> None:
        session.status        = "failed"
        session.ended_at      = timezone.now()
        session.error_message = error_message
        session.save(update_fields=["status", "ended_at", "error_message"])
        log.error("VoiceSession failed: %s — %s", session.id, error_message)

    @staticmethod
    def log_stt_start(session: VoiceSession, audio_file: str = "") -> None:
        log.debug("STT starting for session %s, audio=%s", session.id, audio_file)

    @staticmethod
    def log_transcript(
        session: VoiceSession,
        turn_type: str,
        text: str,
        confidence: float = None,
        audio_file: str = "",
        latency_ms: int = 0,
    ) -> TranscriptLog:
        entry = TranscriptLog.objects.create(
            session=session,
            turn_type=turn_type,
            text=text,
            confidence=confidence,
            audio_file=audio_file,
            latency_ms=latency_ms,
        )
        log.debug("[%s] %s", turn_type.upper(), text[:80])
        return entry