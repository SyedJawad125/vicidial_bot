"""
apps/bot_api/serializers.py
============================
DRF serializers for VICIdial Bot models.

Serializer pairs:
  - EventLog   → EventLogListSerializer  (lightweight, for listings)
               → EventLogSerializer      (full detail)
  - CallLog    → CallLogListSerializer   (lightweight)
               → CallLogSerializer       (full detail)
  - BotCommand → BotCommandListSerializer (lightweight)
               → BotCommandSerializer    (full detail + issued_by user)
"""

from rest_framework import serializers
from .models import BotEventLog, CallLog, BotCommand


# ═══════════════════════════════════════════════════════════════════
#  BOT EVENT LOG SERIALIZERS
# ═══════════════════════════════════════════════════════════════════

class EventLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for event log listings / dropdowns."""

    class Meta:
        model  = BotEventLog
        fields = ["id", "event_type", "message", "timestamp"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Flatten timestamp to readable format
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = data["timestamp"].replace("T", " ").split(".")[0]
        return data


class EventLogSerializer(serializers.ModelSerializer):
    """Full serializer for a single event log entry."""

    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )

    class Meta:
        model  = BotEventLog
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "message",
            "payload",
            "timestamp",
        ]
        read_only_fields = fields  # All log entries are read-only via API

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Order fields intentionally
        ordered = {
            "id":                 data.get("id"),
            "event_type":         data.get("event_type"),
            "event_type_display": data.get("event_type_display"),
            "message":            data.get("message"),
            "payload":            data.get("payload"),
            "timestamp":          data.get("timestamp"),
        }

        if isinstance(ordered.get("timestamp"), str):
            ordered["timestamp"] = ordered["timestamp"].replace("T", " ").split(".")[0]

        # Append any unexpected extra fields
        for key, value in data.items():
            if key not in ordered:
                ordered[key] = value

        return ordered


# ═══════════════════════════════════════════════════════════════════
#  CALL LOG SERIALIZERS
# ═══════════════════════════════════════════════════════════════════

class CallLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for call log listings."""

    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model  = CallLog
        fields = [
            "id",
            "unique_id",
            "destination",
            "campaign_id",
            "agent_user",
            "state",
            "duration_sec",
            "duration_formatted",
            "started_at",
        ]

    def get_duration_formatted(self, obj):
        """Convert seconds → HH:MM:SS string."""
        s = obj.duration_sec or 0
        h, remainder = divmod(s, 3600)
        m, sec       = divmod(remainder, 60)
        return f"{h:02}:{m:02}:{sec:02}"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("started_at"), str):
            data["started_at"] = data["started_at"].replace("T", " ").split(".")[0]
        return data


class CallLogSerializer(serializers.ModelSerializer):
    """Full serializer for a completed call record."""

    duration_formatted = serializers.SerializerMethodField()
    state_display      = serializers.SerializerMethodField()

    class Meta:
        model  = CallLog
        fields = [
            "id",
            "unique_id",
            "channel",
            "caller_id",
            "destination",
            "campaign_id",
            "agent_user",
            "state",
            "state_display",
            "hangup_cause",
            "started_at",
            "answered_at",
            "ended_at",
            "duration_sec",
            "duration_formatted",
            "created_at",
        ]
        read_only_fields = fields  # Read-only via API

    def get_duration_formatted(self, obj):
        s = obj.duration_sec or 0
        h, remainder = divmod(s, 3600)
        m, sec       = divmod(remainder, 60)
        return f"{h:02}:{m:02}:{sec:02}"

    def get_state_display(self, obj):
        STATE_LABELS = {
            "ANSWERED": "Answered",
            "NO_ANSWER": "No Answer",
            "BUSY": "Busy",
            "FAILED": "Failed",
            "UNKNOWN": "Unknown",
        }
        return STATE_LABELS.get(obj.state, obj.state)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Normalise datetime fields
        for field in ("started_at", "answered_at", "ended_at", "created_at"):
            if isinstance(data.get(field), str):
                data[field] = data[field].replace("T", " ").split(".")[0]

        ordered = {
            "id":                 data.get("id"),
            "unique_id":          data.get("unique_id"),
            "channel":            data.get("channel"),
            "caller_id":          data.get("caller_id"),
            "destination":        data.get("destination"),
            "campaign_id":        data.get("campaign_id"),
            "agent_user":         data.get("agent_user"),
            "state":              data.get("state"),
            "state_display":      data.get("state_display"),
            "hangup_cause":       data.get("hangup_cause"),
            "duration_sec":       data.get("duration_sec"),
            "duration_formatted": data.get("duration_formatted"),
            "started_at":         data.get("started_at"),
            "answered_at":        data.get("answered_at"),
            "ended_at":           data.get("ended_at"),
            "created_at":         data.get("created_at"),
        }

        for key, value in data.items():
            if key not in ordered:
                ordered[key] = value

        return ordered


# ═══════════════════════════════════════════════════════════════════
#  BOT COMMAND SERIALIZERS
# ═══════════════════════════════════════════════════════════════════

class _IssuedBySerializer(serializers.Serializer):
    """Minimal user representation for command audit logs."""
    id       = serializers.IntegerField()
    username = serializers.CharField()
    email    = serializers.EmailField()


class BotCommandListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for command audit listings."""

    issued_by_username = serializers.CharField(
        source="issued_by.username", read_only=True, default=None
    )

    class Meta:
        model  = BotCommand
        fields = [
            "id",
            "command",
            "status",
            "issued_by_username",
            "issued_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("issued_at"), str):
            data["issued_at"] = data["issued_at"].replace("T", " ").split(".")[0]
        return data


class BotCommandSerializer(serializers.ModelSerializer):
    """Full serializer for a bot command audit record."""

    issued_by_details  = serializers.SerializerMethodField()
    status_display     = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model  = BotCommand
        fields = [
            "id",
            "command",
            "params",
            "status",
            "status_display",
            "result",
            "issued_by",
            "issued_by_details",
            "issued_at",
            "executed_at",
        ]
        read_only_fields = fields  # Audit log — read-only via API
        extra_kwargs = {
            "issued_by": {"write_only": True},  # Expose via issued_by_details instead
        }

    def get_issued_by_details(self, obj):
        if obj.issued_by:
            return {
                "id":       obj.issued_by.pk,
                "username": obj.issued_by.username,
                "email":    getattr(obj.issued_by, "email", None),
            }
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for field in ("issued_at", "executed_at"):
            if isinstance(data.get(field), str):
                data[field] = data[field].replace("T", " ").split(".")[0]

        ordered = {
            "id":               data.get("id"),
            "command":          data.get("command"),
            "params":           data.get("params"),
            "status":           data.get("status"),
            "status_display":   data.get("status_display"),
            "result":           data.get("result"),
            "issued_by_details":data.get("issued_by_details"),
            "issued_at":        data.get("issued_at"),
            "executed_at":      data.get("executed_at"),
        }

        for key, value in data.items():
            if key not in ordered:
                ordered[key] = value

        return ordered


# ═══════════════════════════════════════════════════════════════════
#  BOT COMMAND REQUEST SERIALIZERS  (for incoming POST validation)
# ═══════════════════════════════════════════════════════════════════

class OriginateRequestSerializer(serializers.Serializer):
    phone       = serializers.CharField(max_length=20)
    campaign_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    caller_id   = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_phone(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Phone number cannot be empty.")
        if not value.lstrip("+").isdigit():
            raise serializers.ValidationError(
                "Phone must contain digits only (optional leading +)."
            )
        return value


class HangupRequestSerializer(serializers.Serializer):
    channel = serializers.CharField(max_length=200)

    def validate_channel(self, value):
        if not value.strip():
            raise serializers.ValidationError("Channel cannot be empty.")
        return value.strip()


class TransferRequestSerializer(serializers.Serializer):
    channel     = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=100)
    context     = serializers.CharField(max_length=100, required=False, default="default")


class DTMFRequestSerializer(serializers.Serializer):
    channel = serializers.CharField(max_length=200)
    digit   = serializers.CharField(max_length=1)

    def validate_digit(self, value):
        if value not in "0123456789*#ABCD":
            raise serializers.ValidationError(
                "Digit must be one of: 0-9, *, #, A, B, C, D"
            )
        return value


class DNCRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Phone number cannot be empty.")
        return value


class AddLeadRequestSerializer(serializers.Serializer):
    phone       = serializers.CharField(max_length=20)
    campaign_id = serializers.CharField(max_length=100)
    first_name  = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name   = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email       = serializers.EmailField(required=False, allow_blank=True)


class UpdateLeadRequestSerializer(serializers.Serializer):
    VALID_STATUSES = ["SALE", "NI", "DNC", "CALLBACK", "DROP", "PDROP", "XFER"]

    lead_id = serializers.CharField(max_length=100)
    status  = serializers.CharField(max_length=20)

    def validate_status(self, value):
        value = value.upper()
        if value not in self.VALID_STATUSES:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(self.VALID_STATUSES)}"
            )
        return value