"""
apps/voice/models.py
=====================
Models for tracking every voice session (call handled by the bot).

VoiceSession  — one per inbound/outbound call the bot talks on.
TranscriptLog — one row per STT/TTS exchange inside a session.
"""

import uuid
from django.db import models
from django.conf import settings


class VoiceSession(models.Model):
    """
    Represents a single bot-handled call conversation.
    Created when the AGI script starts; updated as the call progresses.
    """

    STATUS = [
        ("active",    "Active"),
        ("completed", "Completed"),
        ("failed",    "Failed"),
        ("timeout",   "Timeout"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Asterisk identifiers
    unique_id     = models.CharField(max_length=100, unique=True, db_index=True,
                                     help_text="Asterisk UniqueID for the channel")
    channel       = models.CharField(max_length=200, blank=True)
    caller_id     = models.CharField(max_length=100, blank=True)
    campaign_id   = models.CharField(max_length=100, blank=True)

    # Session lifecycle
    status        = models.CharField(max_length=20, choices=STATUS, default="active")
    started_at    = models.DateTimeField(auto_now_add=True)
    ended_at      = models.DateTimeField(null=True, blank=True)
    duration_sec  = models.PositiveIntegerField(default=0)

    # Audio / engine metadata
    stt_engine    = models.CharField(max_length=50, default="vosk",
                                     help_text="STT engine used  (vosk | whisper | google)")
    tts_engine    = models.CharField(max_length=50, default="melotts",
                                     help_text="TTS engine used  (melotts | gtts | elevenlabs)")
    language      = models.CharField(max_length=10, default="en",
                                     help_text="BCP-47 language code, e.g. en / ur / ar")

    # Outcome
    disposition   = models.CharField(max_length=100, blank=True,
                                     help_text="Final outcome: SALE, NI, DNC, TRANSFER …")
    transferred_to = models.CharField(max_length=100, blank=True)
    error_message  = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"[{self.status}] {self.caller_id} — {self.unique_id[:12]}"


class TranscriptLog(models.Model):
    """
    One row per STT/TTS exchange turn inside a VoiceSession.
    Gives a full conversation transcript.
    """

    TURN_TYPE = [
        ("stt", "Caller spoke  → STT text"),
        ("tts", "Bot replied   → TTS audio"),
        ("err", "Engine error"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session     = models.ForeignKey(VoiceSession, on_delete=models.CASCADE,
                                    related_name="transcripts")
    turn_type   = models.CharField(max_length=5, choices=TURN_TYPE)
    text        = models.TextField(help_text="Raw STT output or TTS input text")
    confidence  = models.FloatField(null=True, blank=True,
                                    help_text="STT confidence score 0-1")
    audio_file  = models.CharField(max_length=300, blank=True,
                                   help_text="Relative path to the saved audio file")
    latency_ms  = models.PositiveIntegerField(default=0,
                                              help_text="Engine processing time in ms")
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.turn_type}] {self.text[:60]}"