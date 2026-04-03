"""
apps/voice/filters.py
"""
from django_filters import CharFilter, FilterSet, DateTimeFilter, BooleanFilter
from .models import VoiceSession, TranscriptLog


class VoiceSessionFilter(FilterSet):
    caller_id   = CharFilter(field_name="caller_id",   lookup_expr="icontains")
    campaign_id = CharFilter(field_name="campaign_id", lookup_expr="iexact")
    status      = CharFilter(field_name="status",      lookup_expr="iexact")
    language    = CharFilter(field_name="language",    lookup_expr="iexact")
    from_dt     = DateTimeFilter(field_name="started_at", lookup_expr="gte")
    to_dt       = DateTimeFilter(field_name="started_at", lookup_expr="lte")

    class Meta:
        model  = VoiceSession
        fields = ["caller_id", "campaign_id", "status", "language", "from_dt", "to_dt"]


class TranscriptLogFilter(FilterSet):
    turn_type = CharFilter(field_name="turn_type", lookup_expr="iexact")
    search    = CharFilter(field_name="text",       lookup_expr="icontains")

    class Meta:
        model  = TranscriptLog
        fields = ["turn_type", "search"]