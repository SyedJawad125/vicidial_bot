# """
# api/views.py
# ============
# Django REST Framework views for the VICIdial Bot.

# All control goes through the bot's command queue.
# State reads come from the shared bot_state object.

# Endpoints:
#   GET  /api/status/              → bot status + active calls
#   GET  /api/events/              → event log (paginated)
#   GET  /api/calls/               → call log (paginated)
#   GET  /api/commands/            → command audit log

#   POST /api/commands/originate/  → dial a number
#   POST /api/commands/hangup/     → hang up a channel
#   POST /api/commands/transfer/   → transfer a call
#   POST /api/commands/dtmf/       → send DTMF digits
#   POST /api/commands/dnc/        → add phone to DNC
#   POST /api/commands/ping/       → ping AMI connection

#   GET  /api/vicidial/campaigns/     → list VICIdial campaigns
#   GET  /api/vicidial/agents/        → list agent statuses
#   GET  /api/vicidial/active_calls/  → active calls from VICIdial API
#   POST /api/vicidial/add_lead/      → add lead to VICIdial
#   POST /api/vicidial/update_lead/   → update lead disposition
# """

# import logging
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from rest_framework import status, serializers
# from apps.bot_api.apps import get_bot_instance
# from .models import BotEventLog, CallLog, BotCommand

# log = logging.getLogger("vicidial_bot.api")


# def _get_bot():
#     """Get the running bot instance from the app registry."""
#     from apps import get_bot_instance
#     return get_bot_instance()


# # ── Serializers ──────────────────────────────────────────

# class EventLogSerializer(serializers.ModelSerializer):
#     class Meta:
#         model  = BotEventLog
#         fields = "__all__"


# class CallLogSerializer(serializers.ModelSerializer):
#     class Meta:
#         model  = CallLog
#         fields = "__all__"


# class BotCommandSerializer(serializers.ModelSerializer):
#     issued_by_username = serializers.CharField(source="issued_by.username",
#                                                read_only=True, default=None)
#     class Meta:
#         model  = BotCommand
#         fields = "__all__"


# # ── Status ───────────────────────────────────────────────

# class BotStatusView(APIView):
#     """GET /api/status/ — bot health + active calls."""

#     def get(self, request):
#         from bot.vici_bot import bot_state
#         return Response(bot_state.snapshot())


# # ── Event Log ────────────────────────────────────────────

# class EventLogView(APIView):
#     """GET /api/events/?type=CALL_ENDED&limit=50"""

#     def get(self, request):
#         qs = BotEventLog.objects.all()
#         event_type = request.query_params.get("type")
#         limit      = min(int(request.query_params.get("limit", 50)), 500)
#         if event_type:
#             qs = qs.filter(event_type=event_type)
#         return Response(EventLogSerializer(qs[:limit], many=True).data)


# # ── Call Log ─────────────────────────────────────────────

# class CallLogView(APIView):
#     """GET /api/calls/?campaign_id=CAMP1&limit=50"""

#     def get(self, request):
#         qs = CallLog.objects.all()
#         campaign = request.query_params.get("campaign_id")
#         agent    = request.query_params.get("agent_user")
#         limit    = min(int(request.query_params.get("limit", 50)), 500)
#         if campaign:
#             qs = qs.filter(campaign_id=campaign)
#         if agent:
#             qs = qs.filter(agent_user=agent)
#         return Response(CallLogSerializer(qs[:limit], many=True).data)


# # ── Command Log ──────────────────────────────────────────

# class CommandLogView(APIView):
#     """GET /api/commands/"""

#     def get(self, request):
#         limit = min(int(request.query_params.get("limit", 50)), 200)
#         qs = BotCommand.objects.select_related("issued_by")[:limit]
#         return Response(BotCommandSerializer(qs, many=True).data)


# # ── Bot Commands ─────────────────────────────────────────

# class OriginateView(APIView):
#     """
#     POST /api/commands/originate/
#     Body: {"phone": "09001234567", "campaign_id": "CAMP1", "caller_id": "Company <1000>"}
#     """
#     def post(self, request):
#         phone = request.data.get("phone", "").strip()
#         if not phone:
#             return Response({"error": "phone is required"}, status=400)

#         bot = _get_bot()
#         result = bot.send_command(
#             "originate",
#             phone=phone,
#             campaign_id=request.data.get("campaign_id", ""),
#             caller_id=request.data.get("caller_id", ""),
#         )
#         _log_command("originate", request.data, result, request.user)
#         return Response(result, status=202)


# class HangupView(APIView):
#     """
#     POST /api/commands/hangup/
#     Body: {"channel": "SIP/trunk-0000001"}
#     """
#     def post(self, request):
#         channel = request.data.get("channel", "").strip()
#         if not channel:
#             return Response({"error": "channel is required"}, status=400)
#         bot    = _get_bot()
#         result = bot.send_command("hangup", channel=channel)
#         _log_command("hangup", request.data, result, request.user)
#         return Response(result, status=202)


# class TransferView(APIView):
#     """
#     POST /api/commands/transfer/
#     Body: {"channel": "...", "destination": "1001", "context": "default"}
#     """
#     def post(self, request):
#         channel = request.data.get("channel", "")
#         dest    = request.data.get("destination", "")
#         if not channel or not dest:
#             return Response({"error": "channel and destination required"}, status=400)
#         bot    = _get_bot()
#         result = bot.send_command(
#             "transfer",
#             channel=channel,
#             destination=dest,
#             context=request.data.get("context", "default"),
#         )
#         _log_command("transfer", request.data, result, request.user)
#         return Response(result, status=202)


# class DTMFView(APIView):
#     """
#     POST /api/commands/dtmf/
#     Body: {"channel": "...", "digit": "5"}
#     """
#     def post(self, request):
#         channel = request.data.get("channel", "")
#         digit   = request.data.get("digit", "")
#         if not channel or not digit:
#             return Response({"error": "channel and digit required"}, status=400)
#         bot    = _get_bot()
#         result = bot.send_command("dtmf", channel=channel, digit=digit)
#         _log_command("dtmf", request.data, result, request.user)
#         return Response(result, status=202)


# class DNCView(APIView):
#     """
#     POST /api/commands/dnc/
#     Body: {"phone": "09001234567"}
#     """
#     def post(self, request):
#         phone = request.data.get("phone", "")
#         if not phone:
#             return Response({"error": "phone required"}, status=400)
#         bot    = _get_bot()
#         result = bot.send_command("dnc_add", phone=phone)
#         _log_command("dnc_add", request.data, result, request.user)
#         return Response(result, status=202)


# class PingView(APIView):
#     """GET /api/commands/ping/ — test AMI connection."""
#     def get(self, request):
#         bot    = _get_bot()
#         result = bot.execute_now("ping")
#         return Response(result)


# # ── VICIdial API Proxy ───────────────────────────────────

# class VICICampaignsView(APIView):
#     """GET /api/vicidial/campaigns/ — list all campaigns from VICIdial."""
#     def get(self, request):
#         bot = _get_bot()
#         try:
#             campaigns = bot.api.get_campaigns()
#             return Response(campaigns)
#         except Exception as e:
#             return Response({"error": str(e)}, status=502)


# class VICIAgentsView(APIView):
#     """GET /api/vicidial/agents/ — all agent statuses."""
#     def get(self, request):
#         bot = _get_bot()
#         try:
#             agents = bot.api.get_all_agent_status()
#             return Response(agents)
#         except Exception as e:
#             return Response({"error": str(e)}, status=502)


# class VICIActiveCallsView(APIView):
#     """GET /api/vicidial/active_calls/ — active calls from VICIdial API."""
#     def get(self, request):
#         bot = _get_bot()
#         try:
#             calls = bot.api.get_active_calls()
#             return Response(calls)
#         except Exception as e:
#             return Response({"error": str(e)}, status=502)


# class VICIAddLeadView(APIView):
#     """
#     POST /api/vicidial/add_lead/
#     Body: {phone, campaign_id, first_name, last_name, email}
#     """
#     def post(self, request):
#         phone = request.data.get("phone", "")
#         camp  = request.data.get("campaign_id", "")
#         if not phone or not camp:
#             return Response({"error": "phone and campaign_id required"}, status=400)
#         bot    = _get_bot()
#         result = bot.execute_now("add_lead", **request.data)
#         _log_command("add_lead", request.data, result, request.user)
#         return Response(result)


# class VICIUpdateLeadView(APIView):
#     """
#     POST /api/vicidial/update_lead/
#     Body: {lead_id, status}  e.g. status = "SALE" | "NI" | "DNC" | "CALLBACK"
#     """
#     def post(self, request):
#         lead_id = request.data.get("lead_id", "")
#         status  = request.data.get("status", "")
#         if not lead_id or not status:
#             return Response({"error": "lead_id and status required"}, status=400)
#         bot    = _get_bot()
#         result = bot.execute_now("update_lead", lead_id=lead_id, status=status)
#         _log_command("update_lead", request.data, result, request.user)
#         return Response(result)


# class VICICampaignControlView(APIView):
#     """
#     POST /api/vicidial/campaign/<id>/pause/
#     POST /api/vicidial/campaign/<id>/activate/
#     """
#     def post(self, request, campaign_id, action):
#         if action not in ("pause", "activate"):
#             return Response({"error": "action must be pause or activate"}, status=400)
#         bot    = _get_bot()
#         cmd    = f"campaign_{action}"
#         result = bot.execute_now(cmd, campaign_id=campaign_id)
#         _log_command(cmd, {"campaign_id": campaign_id}, result, request.user)
#         return Response(result)


# # ── Helpers ──────────────────────────────────────────────

# def _log_command(command: str, params: dict, result: dict, user):
#     try:
#         from bot.db_writer import save_command
#         save_command(command, params, result, user)
#     except Exception as e:
#         log.debug(f"Command log failed: {e}")



"""
apps/bot_api/views.py
======================
Django REST Framework views for the VICIdial Bot.

All CRUD log views inherit BotBaseView (read-only, paginated, filterable).
Bot-command POST views use individual request serializers for strict validation.
VICIdial proxy views call the running bot instance via get_bot_instance().

Endpoints
─────────
  GET  /api/v1/status/                            → bot health + active calls
  GET  /api/v1/events/                            → event log
  GET  /api/v1/calls/                             → call log
  GET  /api/v1/commands/                          → command audit log

  POST /api/v1/commands/originate/                → dial a number
  POST /api/v1/commands/hangup/                   → hang up a channel
  POST /api/v1/commands/transfer/                 → transfer a call
  POST /api/v1/commands/dtmf/                     → send DTMF digits
  POST /api/v1/commands/dnc/                      → add phone to DNC list
  GET  /api/v1/commands/ping/                     → ping AMI connection

  GET  /api/v1/vicidial/campaigns/                → list campaigns
  GET  /api/v1/vicidial/agents/                   → list agent statuses
  GET  /api/v1/vicidial/active_calls/             → active calls
  POST /api/v1/vicidial/add_lead/                 → add lead
  POST /api/v1/vicidial/update_lead/              → update lead disposition
  POST /api/v1/vicidial/campaign/<id>/<action>/   → pause/activate campaign
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.reusable_functions import create_response, get_first_error
from utils.response_messages import SUCCESSFUL, NOT_FOUND, ID_NOT_PROVIDED
from utils.helpers import paginate_data

from .models import BotEventLog, CallLog, BotCommand
from .serializers import (
    # Event log
    EventLogSerializer,
    EventLogListSerializer,
    # Call log
    CallLogSerializer,
    CallLogListSerializer,
    # Command log
    BotCommandSerializer,
    BotCommandListSerializer,
    # Request validators
    OriginateRequestSerializer,
    HangupRequestSerializer,
    TransferRequestSerializer,
    DTMFRequestSerializer,
    DNCRequestSerializer,
    AddLeadRequestSerializer,
    UpdateLeadRequestSerializer,
)
from .filters import EventLogFilter, CallLogFilter, BotCommandFilter

log = logging.getLogger("vicidial_bot.api")


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_bot():
    """Return the running bot instance registered in apps.py."""
    from apps.bot_api.apps import get_bot_instance
    bot = get_bot_instance()
    if bot is None:
        raise RuntimeError("Bot is not running or has not been initialised yet.")
    return bot


def _log_command(command: str, params: dict, result: dict, user) -> None:
    """Persist a bot command to the BotCommand audit table."""
    try:
        from bot.db_writer import save_command
        save_command(command, params, result, user)
    except Exception as exc:
        log.debug("Command log failed: %s", exc)


def _bot_error_response(exc: Exception) -> Response:
    """Uniform 502 when the bot / VICIdial API is unreachable."""
    log.exception("Bot/VICIdial error: %s", exc)
    return Response(
        create_response(f"Bot error: {exc}"),
        status=status.HTTP_502_BAD_GATEWAY,
    )


# ═══════════════════════════════════════════════════════════════════
#  BOT BASE VIEW  (read-only, paginated, filterable)
#  The bot log models have no `deleted` field, so we skip that filter.
#  Mirrors the pattern of utils/base_api.py but adapted for log models.
# ═══════════════════════════════════════════════════════════════════

class BotBaseView(APIView):
    """
    Shared base for all read-only bot log endpoints.

    Subclasses set:
        serializer_class      – detail serializer
        list_serializer_class – lightweight listing serializer (optional)
        filterset_class       – django-filter FilterSet
        model                 – explicit model reference (or taken from Meta)
        order_by_default      – default ordering field  (default: '-timestamp')
    """

    permission_classes    = (IsAuthenticated,)
    serializer_class      = None
    list_serializer_class = None
    filterset_class       = None
    model                 = None
    order_by_default      = "-timestamp"

    def _get_model(self):
        if self.model:
            return self.model
        return self.serializer_class.Meta.model

    def get(self, request):
        try:
            Model       = self._get_model()
            serializer  = self.serializer_class

            # Switch to lightweight listing serializer when requested
            api_type = request.query_params.get("api_type")
            if api_type in ("list", "cards") and self.list_serializer_class:
                serializer = self.list_serializer_class

            # Single-record fetch
            record_id = request.query_params.get("id")
            if record_id:
                instance = Model.objects.filter(id=record_id).first()
                if not instance:
                    return Response(
                        create_response(NOT_FOUND),
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response(
                    create_response(SUCCESSFUL, serializer(instance).data, 1),
                    status=status.HTTP_200_OK,
                )

            # List fetch
            order    = request.query_params.get("order", "desc")
            order_by = request.query_params.get("order_by", self.order_by_default.lstrip("-"))
            ordering = f"-{order_by}" if order == "desc" else order_by

            qs = Model.objects.all().order_by(ordering)

            if self.filterset_class:
                qs = self.filterset_class(request.GET, queryset=qs).qs

            data, count = paginate_data(qs, request)
            serialized  = serializer(data, many=True).data

            return Response(
                create_response(SUCCESSFUL, serialized, count),
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            log.exception("BotBaseView.get error: %s", exc)
            return Response(
                create_response(str(exc)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═══════════════════════════════════════════════════════════════════
#  BOT STATUS
# ═══════════════════════════════════════════════════════════════════

class BotStatusView(APIView):
    """
    GET /api/v1/status/
    Returns the bot health snapshot: connection state, active calls, uptime.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            from bot.vici_bot import bot_state
            return Response(
                create_response(SUCCESSFUL, bot_state.snapshot()),
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return _bot_error_response(exc)


# ═══════════════════════════════════════════════════════════════════
#  LOG VIEWS
# ═══════════════════════════════════════════════════════════════════

class EventLogView(BotBaseView):
    """
    GET /api/v1/events/
    Supports: ?event_type=CALL_ENDED&search=09001&from_dt=2025-01-01&limit=50&api_type=list
    """

    serializer_class      = EventLogSerializer
    list_serializer_class = EventLogListSerializer
    filterset_class       = EventLogFilter
    model                 = BotEventLog
    order_by_default      = "-timestamp"


class CallLogView(BotBaseView):
    """
    GET /api/v1/calls/
    Supports: ?campaign_id=CAMP1&state=ANSWERED&agent_user=ali&from_dt=2025-01-01
    """

    serializer_class      = CallLogSerializer
    list_serializer_class = CallLogListSerializer
    filterset_class       = CallLogFilter
    model                 = CallLog
    order_by_default      = "-started_at"


class CommandLogView(BotBaseView):
    """
    GET /api/v1/commands/
    Supports: ?command=originate&status=executed&issued_by=3
    """

    serializer_class      = BotCommandSerializer
    list_serializer_class = BotCommandListSerializer
    filterset_class       = BotCommandFilter
    model                 = BotCommand
    order_by_default      = "-issued_at"


# ═══════════════════════════════════════════════════════════════════
#  BOT COMMAND VIEWS  (POST only, strict validation)
# ═══════════════════════════════════════════════════════════════════

class OriginateView(APIView):
    """
    POST /api/v1/commands/originate/
    Body: {"phone": "09001234567", "campaign_id": "CAMP1", "caller_id": "Company <1000>"}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = OriginateRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.send_command(
                "originate",
                phone=req_ser.validated_data["phone"],
                campaign_id=req_ser.validated_data.get("campaign_id", ""),
                caller_id=req_ser.validated_data.get("caller_id", ""),
            )
            _log_command("originate", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _bot_error_response(exc)


class HangupView(APIView):
    """
    POST /api/v1/commands/hangup/
    Body: {"channel": "SIP/trunk-0000001"}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = HangupRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.send_command("hangup", channel=req_ser.validated_data["channel"])
            _log_command("hangup", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _bot_error_response(exc)


class TransferView(APIView):
    """
    POST /api/v1/commands/transfer/
    Body: {"channel": "...", "destination": "1001", "context": "default"}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = TransferRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.send_command(
                "transfer",
                channel=req_ser.validated_data["channel"],
                destination=req_ser.validated_data["destination"],
                context=req_ser.validated_data.get("context", "default"),
            )
            _log_command("transfer", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _bot_error_response(exc)


class DTMFView(APIView):
    """
    POST /api/v1/commands/dtmf/
    Body: {"channel": "...", "digit": "5"}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = DTMFRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.send_command(
                "dtmf",
                channel=req_ser.validated_data["channel"],
                digit=req_ser.validated_data["digit"],
            )
            _log_command("dtmf", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _bot_error_response(exc)


class DNCView(APIView):
    """
    POST /api/v1/commands/dnc/
    Body: {"phone": "09001234567"}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = DNCRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.send_command("dnc_add", phone=req_ser.validated_data["phone"])
            _log_command("dnc_add", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return _bot_error_response(exc)


class PingView(APIView):
    """
    GET /api/v1/commands/ping/
    Tests AMI connection. Returns latency info from the bot.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            bot    = _get_bot()
            result = bot.execute_now("ping")
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


# ═══════════════════════════════════════════════════════════════════
#  VICIDIAL API PROXY VIEWS
# ═══════════════════════════════════════════════════════════════════

class VICICampaignsView(APIView):
    """GET /api/v1/vicidial/campaigns/ — list all campaigns from VICIdial."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            campaigns = _get_bot().api.get_campaigns()
            return Response(create_response(SUCCESSFUL, campaigns), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


class VICIAgentsView(APIView):
    """GET /api/v1/vicidial/agents/ — all agent statuses."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            agents = _get_bot().api.get_all_agent_status()
            return Response(create_response(SUCCESSFUL, agents), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


class VICIActiveCallsView(APIView):
    """GET /api/v1/vicidial/active_calls/ — active calls from VICIdial API."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            calls = _get_bot().api.get_active_calls()
            return Response(create_response(SUCCESSFUL, calls), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


class VICIAddLeadView(APIView):
    """
    POST /api/v1/vicidial/add_lead/
    Body: {phone, campaign_id, first_name, last_name, email}
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = AddLeadRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.execute_now("add_lead", **req_ser.validated_data)
            _log_command("add_lead", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


class VICIUpdateLeadView(APIView):
    """
    POST /api/v1/vicidial/update_lead/
    Body: {lead_id, status}  e.g. status = "SALE" | "NI" | "DNC" | "CALLBACK"
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = UpdateLeadRequestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(
                create_response(get_first_error(req_ser.errors)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            result = bot.execute_now(
                "update_lead",
                lead_id=req_ser.validated_data["lead_id"],
                status=req_ser.validated_data["status"],
            )
            _log_command("update_lead", req_ser.validated_data, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)


class VICICampaignControlView(APIView):
    """
    POST /api/v1/vicidial/campaign/<campaign_id>/pause/
    POST /api/v1/vicidial/campaign/<campaign_id>/activate/
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, campaign_id: str, action: str):
        if action not in ("pause", "activate"):
            return Response(
                create_response("action must be 'pause' or 'activate'"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bot    = _get_bot()
            cmd    = f"campaign_{action}"
            result = bot.execute_now(cmd, campaign_id=campaign_id)
            _log_command(cmd, {"campaign_id": campaign_id}, result, request.user)
            return Response(create_response(SUCCESSFUL, result), status=status.HTTP_200_OK)
        except Exception as exc:
            return _bot_error_response(exc)