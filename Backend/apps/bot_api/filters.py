"""
apps/bot_api/filters.py
========================
django-filter FilterSets for VICIdial Bot models.

  EventLogFilter   → /api/v1/events/?event_type=CALL_ENDED&search=09001234
  CallLogFilter    → /api/v1/calls/?campaign_id=CAMP1&state=ANSWERED&agent_user=ali
  BotCommandFilter → /api/v1/commands/?command=originate&status=executed
"""

import django_filters
from django_filters import CharFilter, FilterSet, NumberFilter, DateTimeFilter

from .models import BotEventLog, CallLog, BotCommand


# ═══════════════════════════════════════════════════════════════════
#  EVENT LOG FILTER
# ═══════════════════════════════════════════════════════════════════

class EventLogFilter(FilterSet):
    """
    Query params:
      event_type  – exact match (e.g. CALL_ENDED)
      search      – case-insensitive substring on message
      from_dt     – timestamp >= value  (ISO-8601)
      to_dt       – timestamp <= value  (ISO-8601)
    """

    event_type = CharFilter(field_name="event_type", lookup_expr="iexact")
    search     = CharFilter(field_name="message",    lookup_expr="icontains")
    from_dt    = DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    to_dt      = DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model  = BotEventLog
        fields = ["event_type", "search", "from_dt", "to_dt"]


# ═══════════════════════════════════════════════════════════════════
#  CALL LOG FILTER
# ═══════════════════════════════════════════════════════════════════

class CallLogFilter(FilterSet):
    """
    Query params:
      campaign_id  – exact match
      agent_user   – case-insensitive contains
      state        – exact match  (ANSWERED | NO_ANSWER | BUSY | FAILED | UNKNOWN)
      destination  – phone number contains
      caller_id    – contains
      min_duration – duration_sec >= value (seconds)
      max_duration – duration_sec <= value (seconds)
      from_dt      – started_at  >= value
      to_dt        – started_at  <= value
    """

    campaign_id  = CharFilter(field_name="campaign_id",  lookup_expr="iexact")
    agent_user   = CharFilter(field_name="agent_user",   lookup_expr="icontains")
    state        = CharFilter(field_name="state",        lookup_expr="iexact")
    destination  = CharFilter(field_name="destination",  lookup_expr="icontains")
    caller_id    = CharFilter(field_name="caller_id",    lookup_expr="icontains")
    min_duration = NumberFilter(field_name="duration_sec", lookup_expr="gte")
    max_duration = NumberFilter(field_name="duration_sec", lookup_expr="lte")
    from_dt      = DateTimeFilter(field_name="started_at", lookup_expr="gte")
    to_dt        = DateTimeFilter(field_name="started_at", lookup_expr="lte")

    class Meta:
        model  = CallLog
        fields = [
            "campaign_id",
            "agent_user",
            "state",
            "destination",
            "caller_id",
            "min_duration",
            "max_duration",
            "from_dt",
            "to_dt",
        ]


# ═══════════════════════════════════════════════════════════════════
#  BOT COMMAND FILTER
# ═══════════════════════════════════════════════════════════════════

class BotCommandFilter(FilterSet):
    """
    Query params:
      command    – exact match  (originate | hangup | transfer | dtmf | dnc_add …)
      status     – exact match  (queued | executed | failed)
      issued_by  – user id (integer)
      from_dt    – issued_at >= value
      to_dt      – issued_at <= value
    """

    command   = CharFilter(field_name="command", lookup_expr="iexact")
    status    = CharFilter(field_name="status",  lookup_expr="iexact")
    issued_by = NumberFilter(field_name="issued_by__id")
    from_dt   = DateTimeFilter(field_name="issued_at", lookup_expr="gte")
    to_dt     = DateTimeFilter(field_name="issued_at", lookup_expr="lte")

    class Meta:
        model  = BotCommand
        fields = ["command", "status", "issued_by", "from_dt", "to_dt"]