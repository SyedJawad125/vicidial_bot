"""
apps/voice/serializers.py
"""
from rest_framework import serializers
from .models import VoiceSession, TranscriptLog


class TranscriptLogSerializer(serializers.ModelSerializer):
    turn_type_display = serializers.CharField(source="get_turn_type_display", read_only=True)

    class Meta:
        model  = TranscriptLog
        fields = ["id", "turn_type", "turn_type_display", "text",
                  "confidence", "audio_file", "latency_ms", "timestamp"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = data["timestamp"].replace("T", " ").split(".")[0]
        return data


class VoiceSessionListSerializer(serializers.ModelSerializer):
    """Lightweight listing serializer."""
    class Meta:
        model  = VoiceSession
        fields = ["id", "unique_id", "caller_id", "campaign_id",
                  "status", "language", "duration_sec", "started_at"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("started_at"), str):
            data["started_at"] = data["started_at"].replace("T", " ").split(".")[0]
        return data


class VoiceSessionSerializer(serializers.ModelSerializer):
    """Full detail serializer with nested transcripts."""
    transcripts       = TranscriptLogSerializer(many=True, read_only=True)
    status_display    = serializers.CharField(source="get_status_display", read_only=True)
    transcript_count  = serializers.SerializerMethodField()

    class Meta:
        model  = VoiceSession
        fields = [
            "id", "unique_id", "channel", "caller_id", "campaign_id",
            "status", "status_display", "language",
            "stt_engine", "tts_engine",
            "started_at", "ended_at", "duration_sec",
            "disposition", "transferred_to", "error_message",
            "transcript_count", "transcripts",
        ]
        read_only_fields = fields

    def get_transcript_count(self, obj):
        return obj.transcripts.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for f in ("started_at", "ended_at"):
            if isinstance(data.get(f), str):
                data[f] = data[f].replace("T", " ").split(".")[0]
        return data


# ─── TTS test request serializer ────────────────────────────────────────────
class TTSTestSerializer(serializers.Serializer):
    text     = serializers.CharField(max_length=500)
    language = serializers.CharField(max_length=10, default="en")

    def validate_language(self, value):
        supported = {"en", "en-us", "en-br", "zh", "fr", "es", "kr", "ja", "ur"}
        if value.lower() not in supported:
            raise serializers.ValidationError(
                f"Unsupported language. Choose from: {', '.join(sorted(supported))}"
            )
        return value.lower()


class STTTestSerializer(serializers.Serializer):
    audio_file = serializers.FileField()
    language   = serializers.CharField(max_length=10, default="en")