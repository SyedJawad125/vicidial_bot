# """
# models.py — Django models for VICIdial Bot event/call logging.
# """
# import uuid
# from django.db import models


# class BotEventLog(models.Model):
#     """Every significant bot event stored here."""
#     EVENT_TYPES = [
#         ("SYSTEM",       "System"),
#         ("CALL_STARTED", "Call Started"),
#         ("CALL_ANSWERED","Call Answered"),
#         ("CALL_ENDED",   "Call Ended"),
#         ("AGENT",        "Agent Event"),
#         ("DNC",          "Do Not Call"),
#         ("COMMAND",      "Bot Command"),
#         ("ERROR",        "Error"),
#         ("RAW_AMI",      "Raw AMI Event"),
#     ]

#     id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
#     message    = models.TextField()
#     payload    = models.JSONField(default=dict, blank=True)
#     timestamp  = models.DateTimeField(auto_now_add=True, db_index=True)

#     class Meta:
#         ordering = ["-timestamp"]

#     def __str__(self):
#         return f"[{self.event_type}] {self.message[:80]}"


# class CallLog(models.Model):
#     """Record of each completed outbound call."""
#     id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     unique_id     = models.CharField(max_length=100, unique=True, db_index=True)
#     channel       = models.CharField(max_length=200)
#     caller_id     = models.CharField(max_length=100, blank=True)
#     destination   = models.CharField(max_length=100, blank=True)
#     campaign_id   = models.CharField(max_length=100, blank=True)
#     agent_user    = models.CharField(max_length=100, blank=True)
#     state         = models.CharField(max_length=20, default="UNKNOWN")
#     hangup_cause  = models.CharField(max_length=100, blank=True)
#     started_at    = models.DateTimeField()
#     answered_at   = models.DateTimeField(null=True, blank=True)
#     ended_at      = models.DateTimeField(null=True, blank=True)
#     duration_sec  = models.PositiveIntegerField(default=0)
#     created_at    = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-started_at"]

#     def __str__(self):
#         return f"Call {self.unique_id} → {self.destination} [{self.state}]"


# class BotCommand(models.Model):
#     """Audit log of every command sent to the bot."""
#     STATUS = [
#         ("queued",    "Queued"),
#         ("executed",  "Executed"),
#         ("failed",    "Failed"),
#     ]

#     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     command     = models.CharField(max_length=50)
#     params      = models.JSONField(default=dict)
#     status      = models.CharField(max_length=20, choices=STATUS, default="queued")
#     result      = models.JSONField(default=dict, blank=True)
#     issued_by   = models.ForeignKey(
#         "auth.User", on_delete=models.SET_NULL, null=True, blank=True
#     )
#     issued_at   = models.DateTimeField(auto_now_add=True)
#     executed_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         ordering = ["-issued_at"]

#     def __str__(self):
#         return f"[{self.status}] {self.command} @ {self.issued_at:%H:%M:%S}"



"""
models.py — Django models for VICIdial Bot event/call logging.
"""
import uuid
from django.db import models
from django.conf import settings  # ← ADD THIS IMPORT


class BotEventLog(models.Model):
    """Every significant bot event stored here."""
    EVENT_TYPES = [
        ("SYSTEM",       "System"),
        ("CALL_STARTED", "Call Started"),
        ("CALL_ANSWERED","Call Answered"),
        ("CALL_ENDED",   "Call Ended"),
        ("AGENT",        "Agent Event"),
        ("DNC",          "Do Not Call"),
        ("COMMAND",      "Bot Command"),
        ("ERROR",        "Error"),
        ("RAW_AMI",      "Raw AMI Event"),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    message    = models.TextField()
    payload    = models.JSONField(default=dict, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.event_type}] {self.message[:80]}"


class CallLog(models.Model):
    """Record of each completed outbound call."""
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unique_id     = models.CharField(max_length=100, unique=True, db_index=True)
    channel       = models.CharField(max_length=200)
    caller_id     = models.CharField(max_length=100, blank=True)
    destination   = models.CharField(max_length=100, blank=True)
    campaign_id   = models.CharField(max_length=100, blank=True)
    agent_user    = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=20, default="UNKNOWN")
    hangup_cause  = models.CharField(max_length=100, blank=True)
    started_at    = models.DateTimeField()
    answered_at   = models.DateTimeField(null=True, blank=True)
    ended_at      = models.DateTimeField(null=True, blank=True)
    duration_sec  = models.PositiveIntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Call {self.unique_id} → {self.destination} [{self.state}]"


class BotCommand(models.Model):
    """Audit log of every command sent to the bot."""
    STATUS = [
        ("queued",    "Queued"),
        ("executed",  "Executed"),
        ("failed",    "Failed"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    command     = models.CharField(max_length=50)
    params      = models.JSONField(default=dict)
    status      = models.CharField(max_length=20, choices=STATUS, default="queued")
    result      = models.JSONField(default=dict, blank=True)
    # FIXED: Use settings.AUTH_USER_MODEL instead of 'auth.User'
    issued_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ← CHANGED THIS LINE
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    issued_at   = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"[{self.status}] {self.command} @ {self.issued_at:%H:%M:%S}"