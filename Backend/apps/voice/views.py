"""
apps/voice/views.py
====================
REST API views for the Voice Layer.

Endpoints:
  GET  /api/voice/sessions/          → list all voice sessions
  GET  /api/voice/sessions/?id=UUID  → single session with full transcript
  GET  /api/voice/transcripts/       → all transcript entries (filterable)

  POST /api/voice/test/tts/          → test TTS engine, returns WAV download
  POST /api/voice/test/stt/          → test STT engine, upload WAV get text back

  GET  /api/voice/health/            → engine status check
"""

import logging
import os
import tempfile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.http import FileResponse

from utils.reusable_functions import create_response, get_first_error
from utils.response_messages import SUCCESSFUL, NOT_FOUND
from utils.helpers import paginate_data

from .models import VoiceSession, TranscriptLog
from .serializers import (
    VoiceSessionSerializer, VoiceSessionListSerializer,
    TranscriptLogSerializer,
    TTSTestSerializer, STTTestSerializer,
)
from .filters import VoiceSessionFilter, TranscriptLogFilter

log = logging.getLogger("vicidial_bot.voice.api")


# ── Base view (mirrors BotBaseView pattern) ───────────────────────────────────

class VoiceBaseView(APIView):
    permission_classes    = (IsAuthenticated,)
    serializer_class      = None
    list_serializer_class = None
    filterset_class       = None
    model                 = None
    order_by_default      = "-started_at"

    def get(self, request):
        try:
            Model      = self.model or self.serializer_class.Meta.model
            serializer = self.serializer_class

            if request.query_params.get("api_type") in ("list", "cards") \
                    and self.list_serializer_class:
                serializer = self.list_serializer_class

            record_id = request.query_params.get("id")
            if record_id:
                instance = Model.objects.filter(id=record_id).first()
                if not instance:
                    return Response(create_response(NOT_FOUND),
                                    status=status.HTTP_404_NOT_FOUND)
                return Response(
                    create_response(SUCCESSFUL, serializer(instance).data, 1),
                    status=status.HTTP_200_OK,
                )

            order    = request.query_params.get("order", "desc")
            order_by = request.query_params.get("order_by",
                                                 self.order_by_default.lstrip("-"))
            ordering = f"-{order_by}" if order == "desc" else order_by
            qs       = Model.objects.all().order_by(ordering)

            if self.filterset_class:
                qs = self.filterset_class(request.GET, queryset=qs).qs

            data, count = paginate_data(qs, request)
            return Response(
                create_response(SUCCESSFUL, serializer(data, many=True).data, count),
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            log.exception("VoiceBaseView.get: %s", exc)
            return Response(create_response(str(exc)),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Session views ─────────────────────────────────────────────────────────────

class VoiceSessionView(VoiceBaseView):
    """GET /api/voice/sessions/ — list + single fetch."""
    serializer_class      = VoiceSessionSerializer
    list_serializer_class = VoiceSessionListSerializer
    filterset_class       = VoiceSessionFilter
    model                 = VoiceSession
    order_by_default      = "-started_at"


class TranscriptLogView(VoiceBaseView):
    """GET /api/voice/transcripts/?turn_type=stt&search=hello"""
    serializer_class  = TranscriptLogSerializer
    filterset_class   = TranscriptLogFilter
    model             = TranscriptLog
    order_by_default  = "-timestamp"


# ── Engine test views ─────────────────────────────────────────────────────────

class TTSTestView(APIView):
    """
    POST /api/voice/test/tts/
    Body: {"text": "Hello world", "language": "en"}
    Returns: WAV audio file download.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = TTSTestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(create_response(get_first_error(req_ser.errors)),
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from .engines.tts_melo import get_tts_engine
            tts     = get_tts_engine(req_ser.validated_data["language"])
            out     = tts.synthesize(req_ser.validated_data["text"])
            return FileResponse(
                open(out, "rb"),
                content_type="audio/wav",
                as_attachment=True,
                filename="tts_output.wav",
            )
        except Exception as exc:
            log.exception("TTS test failed: %s", exc)
            return Response(create_response(str(exc)),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class STTTestView(APIView):
    """
    POST /api/voice/test/stt/
    Body: multipart — audio_file (WAV), language (str)
    Returns: {"text": "...", "confidence": 0.95}
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = STTTestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(create_response(get_first_error(req_ser.errors)),
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from .engines.stt_vosk import get_stt_engine
            from .audio_utils import convert_to_vosk_format

            uploaded = req_ser.validated_data["audio_file"]
            language = req_ser.validated_data["language"]

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Ensure correct format for Vosk
            wav_path = convert_to_vosk_format(tmp_path)
            stt      = get_stt_engine(language)
            result   = stt.transcribe_file(wav_path)

            os.unlink(tmp_path)
            if wav_path != tmp_path:
                os.unlink(wav_path)

            return Response(create_response(SUCCESSFUL, {
                "text":       result["text"],
                "confidence": result["confidence"],
                "words":      result.get("words", []),
                "latency_ms": result.get("latency_ms", 0),
            }), status=status.HTTP_200_OK)

        except Exception as exc:
            log.exception("STT test failed: %s", exc)
            return Response(create_response(str(exc)),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VoiceHealthView(APIView):
    """GET /api/voice/health/ — check STT and TTS engine status."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        health = {}
        try:
            from .engines.stt_vosk import get_stt_engine
            stt          = get_stt_engine("en")
            health["stt"] = {"engine": "vosk", "ready": stt.is_ready(),
                              "language": "en"}
        except Exception as exc:
            health["stt"] = {"engine": "vosk", "ready": False, "error": str(exc)}

        try:
            from .engines.tts_melo import get_tts_engine
            tts           = get_tts_engine("en")
            health["tts"] = {"engine": "melotts", "ready": tts.is_ready(),
                              "language": "en"}
        except Exception as exc:
            health["tts"] = {"engine": "melotts", "ready": False, "error": str(exc)}

        overall = all(v.get("ready") for v in health.values())
        return Response(
            create_response(SUCCESSFUL, {"status": "ok" if overall else "degraded",
                                         "engines": health}),
            status=status.HTTP_200_OK,
        )