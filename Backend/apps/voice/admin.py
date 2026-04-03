"""
apps/voice/admin.py
"""
from django.contrib import admin
from .models import VoiceSession, TranscriptLog
 
 
@admin.register(VoiceSession)
class VoiceSessionAdmin(admin.ModelAdmin):
    list_display   = ["started_at", "caller_id", "campaign_id", "status",
                      "language", "duration_sec", "disposition"]
    list_filter    = ["status", "language", "campaign_id"]
    search_fields  = ["caller_id", "unique_id", "channel"]
    readonly_fields = ["id", "started_at", "ended_at"]
    date_hierarchy = "started_at"
 
 
@admin.register(TranscriptLog)
class TranscriptLogAdmin(admin.ModelAdmin):
    list_display   = ["timestamp", "turn_type", "text_preview", "confidence", "latency_ms"]
    list_filter    = ["turn_type"]
    search_fields  = ["text"]
    readonly_fields = ["id", "timestamp"]
 
    def text_preview(self, obj):
        return obj.text[:80]
    text_preview.short_description = "Text"