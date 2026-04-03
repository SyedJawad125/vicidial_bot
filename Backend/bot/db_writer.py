"""
bot/db_writer.py
================
Safe Django ORM calls from the bot's background thread.

Django ORM is thread-safe but needs django.setup() first.
These functions are called from the bot thread — they use
django.db.connection carefully to avoid issues.
"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.vici_bot import ActiveCall
    from bot.ami_client import AMIEvent

log = logging.getLogger("vicidial_bot.db_writer")


def write_event_log(event_type: str, message: str, payload: dict = None):
    try:
        from apps.bot_api.models import BotEventLog
        BotEventLog.objects.create(
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
    except Exception as e:
        log.debug(f"write_event_log failed: {e}")


def write_raw_event(event):
    try:
        from apps.bot_api.models import BotEventLog
        name = event.get("Event", "UNKNOWN")
        BotEventLog.objects.create(
            event_type="RAW_AMI",
            message=f"AMI: {name}",
            payload=dict(event),
        )
    except Exception as e:
        log.debug(f"write_raw_event failed: {e}")


def save_call_log(call, hangup_cause: str = ""):
    try:
        from apps.bot_api.models import CallLog
        CallLog.objects.update_or_create(
            unique_id=call.unique_id,
            defaults={
                "channel":      call.channel,
                "caller_id":    call.caller_id,
                "destination":  call.destination,
                "campaign_id":  call.campaign_id,
                "agent_user":   call.agent_user,
                "state":        call.state,
                "hangup_cause": hangup_cause,
                "started_at":   call.started_at,
                "answered_at":  call.answered_at,
                "ended_at":     call.ended_at or datetime.now(),
                "duration_sec": call.duration_sec,
            },
        )
    except Exception as e:
        log.warning(f"save_call_log failed: {e}")


def save_command(command: str, params: dict, result: dict, user=None) -> None:
    try:
        from apps.bot_api.models import BotCommand
        from django.utils import timezone
        BotCommand.objects.create(
            command=command,
            params=params,
            result=result,
            status="executed" if "error" not in result else "failed",
            issued_by=user,
            executed_at=timezone.now(),
        )
    except Exception as e:
        log.debug(f"save_command failed: {e}")
