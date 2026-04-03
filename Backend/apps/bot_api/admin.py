# from django.contrib import admin
# from .models import BotEventLog, CallLog, BotCommand


# @admin.register(BotEventLog)
# class EventLogAdmin(admin.ModelAdmin):
#     list_display  = ["timestamp", "event_type", "message_preview"]
#     list_filter   = ["event_type"]
#     search_fields = ["message"]
#     readonly_fields = ["id", "timestamp", "payload"]

#     def message_preview(self, obj):
#         return obj.message[:80]


# @admin.register(CallLog)
# class CallLogAdmin(admin.ModelAdmin):
#     list_display  = ["started_at", "destination", "caller_id", "campaign_id",
#                      "agent_user", "state", "duration_sec", "hangup_cause"]
#     list_filter   = ["state", "campaign_id"]
#     search_fields = ["destination", "caller_id", "unique_id", "agent_user"]
#     readonly_fields = ["id", "created_at"]


# @admin.register(BotCommand)
# class BotCommandAdmin(admin.ModelAdmin):
#     list_display  = ["issued_at", "command", "status", "issued_by"]
#     list_filter   = ["status", "command"]
#     readonly_fields = ["id", "issued_at", "executed_at"]



"""
apps/bot_api/admin.py
======================
Django Admin configuration for VICIdial Bot models.
"""

from django.contrib import admin
from .models import BotEventLog, CallLog, BotCommand


# ═══════════════════════════════════════════════════════════════════
#  BOT EVENT LOG
# ═══════════════════════════════════════════════════════════════════

@admin.register(BotEventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display    = ["timestamp", "event_type", "message_preview"]
    list_filter     = ["event_type"]
    search_fields   = ["message"]
    readonly_fields = ["id", "timestamp", "payload"]
    ordering        = ["-timestamp"]
    date_hierarchy  = "timestamp"

    def message_preview(self, obj):
        return obj.message[:100]

    message_preview.short_description = "Message"


# ═══════════════════════════════════════════════════════════════════
#  CALL LOG
# ═══════════════════════════════════════════════════════════════════

@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display    = [
        "started_at", "destination", "caller_id",
        "campaign_id", "agent_user", "state",
        "duration_sec", "hangup_cause",
    ]
    list_filter     = ["state", "campaign_id"]
    search_fields   = ["destination", "caller_id", "unique_id", "agent_user"]
    readonly_fields = ["id", "created_at"]
    ordering        = ["-started_at"]
    date_hierarchy  = "started_at"


# ═══════════════════════════════════════════════════════════════════
#  BOT COMMAND
# ═══════════════════════════════════════════════════════════════════

@admin.register(BotCommand)
class BotCommandAdmin(admin.ModelAdmin):
    list_display    = ["issued_at", "command", "status", "issued_by", "executed_at"]
    list_filter     = ["status", "command"]
    search_fields   = ["command", "issued_by__username"]
    readonly_fields = ["id", "issued_at", "executed_at"]
    ordering        = ["-issued_at"]
    date_hierarchy  = "issued_at"