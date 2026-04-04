# """
# apps/voice/views.py
# ====================
# REST API views for the Voice Layer.

# Endpoints:
#   GET  /api/voice/sessions/          → list all voice sessions
#   GET  /api/voice/sessions/?id=UUID  → single session with full transcript
#   GET  /api/voice/transcripts/       → all transcript entries (filterable)

#   POST /api/voice/test/tts/          → test TTS engine, returns WAV download
#   POST /api/voice/test/stt/          → test STT engine, upload WAV get text back

#   GET  /api/voice/health/            → engine status check
# """

# import logging
# import os
# import tempfile

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from rest_framework import status
# from django.http import FileResponse

# from utils.reusable_functions import create_response, get_first_error
# from utils.response_messages import SUCCESSFUL, NOT_FOUND
# from utils.helpers import paginate_data

# from .models import VoiceSession, TranscriptLog
# from .serializers import (
#     VoiceSessionSerializer, VoiceSessionListSerializer,
#     TranscriptLogSerializer,
#     TTSTestSerializer, STTTestSerializer,
# )
# from .filters import VoiceSessionFilter, TranscriptLogFilter

# log = logging.getLogger("vicidial_bot.voice.api")


# # ── Base view (mirrors BotBaseView pattern) ───────────────────────────────────

# class VoiceBaseView(APIView):
#     permission_classes    = (IsAuthenticated,)
#     serializer_class      = None
#     list_serializer_class = None
#     filterset_class       = None
#     model                 = None
#     order_by_default      = "-started_at"

#     def get(self, request):
#         try:
#             Model      = self.model or self.serializer_class.Meta.model
#             serializer = self.serializer_class

#             if request.query_params.get("api_type") in ("list", "cards") \
#                     and self.list_serializer_class:
#                 serializer = self.list_serializer_class

#             record_id = request.query_params.get("id")
#             if record_id:
#                 instance = Model.objects.filter(id=record_id).first()
#                 if not instance:
#                     return Response(create_response(NOT_FOUND),
#                                     status=status.HTTP_404_NOT_FOUND)
#                 return Response(
#                     create_response(SUCCESSFUL, serializer(instance).data, 1),
#                     status=status.HTTP_200_OK,
#                 )

#             order    = request.query_params.get("order", "desc")
#             order_by = request.query_params.get("order_by",
#                                                  self.order_by_default.lstrip("-"))
#             ordering = f"-{order_by}" if order == "desc" else order_by
#             qs       = Model.objects.all().order_by(ordering)

#             if self.filterset_class:
#                 qs = self.filterset_class(request.GET, queryset=qs).qs

#             data, count = paginate_data(qs, request)
#             return Response(
#                 create_response(SUCCESSFUL, serializer(data, many=True).data, count),
#                 status=status.HTTP_200_OK,
#             )
#         except Exception as exc:
#             log.exception("VoiceBaseView.get: %s", exc)
#             return Response(create_response(str(exc)),
#                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# # ── Session views ─────────────────────────────────────────────────────────────

# class VoiceSessionView(VoiceBaseView):
#     """GET /api/voice/sessions/ — list + single fetch."""
#     serializer_class      = VoiceSessionSerializer
#     list_serializer_class = VoiceSessionListSerializer
#     filterset_class       = VoiceSessionFilter
#     model                 = VoiceSession
#     order_by_default      = "-started_at"


# class TranscriptLogView(VoiceBaseView):
#     """GET /api/voice/transcripts/?turn_type=stt&search=hello"""
#     serializer_class  = TranscriptLogSerializer
#     filterset_class   = TranscriptLogFilter
#     model             = TranscriptLog
#     order_by_default  = "-timestamp"


# # ── Engine test views ─────────────────────────────────────────────────────────

# class TTSTestView(APIView):
#     """
#     POST /api/voice/test/tts/
#     Body: {"text": "Hello world", "language": "en"}
#     Returns: WAV audio file download.
#     """
#     permission_classes = (IsAuthenticated,)

#     def post(self, request):
#         req_ser = TTSTestSerializer(data=request.data)
#         if not req_ser.is_valid():
#             return Response(create_response(get_first_error(req_ser.errors)),
#                             status=status.HTTP_400_BAD_REQUEST)
#         try:
#             from .engines.tts_melo import get_tts_engine
#             tts     = get_tts_engine(req_ser.validated_data["language"])
#             out     = tts.synthesize(req_ser.validated_data["text"])
#             return FileResponse(
#                 open(out, "rb"),
#                 content_type="audio/wav",
#                 as_attachment=True,
#                 filename="tts_output.wav",
#             )
#         except Exception as exc:
#             log.exception("TTS test failed: %s", exc)
#             return Response(create_response(str(exc)),
#                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class STTTestView(APIView):
#     """
#     POST /api/voice/test/stt/
#     Body: multipart — audio_file (WAV), language (str)
#     Returns: {"text": "...", "confidence": 0.95}
#     """
#     permission_classes = (IsAuthenticated,)

#     def post(self, request):
#         req_ser = STTTestSerializer(data=request.data)
#         if not req_ser.is_valid():
#             return Response(create_response(get_first_error(req_ser.errors)),
#                             status=status.HTTP_400_BAD_REQUEST)
#         try:
#             from .engines.stt_vosk import get_stt_engine
#             from .audio_utils import convert_to_vosk_format

#             uploaded = req_ser.validated_data["audio_file"]
#             language = req_ser.validated_data["language"]

#             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
#                 for chunk in uploaded.chunks():
#                     tmp.write(chunk)
#                 tmp_path = tmp.name

#             # Ensure correct format for Vosk
#             wav_path = convert_to_vosk_format(tmp_path)
#             stt      = get_stt_engine(language)
#             result   = stt.transcribe_file(wav_path)

#             os.unlink(tmp_path)
#             if wav_path != tmp_path:
#                 os.unlink(wav_path)

#             return Response(create_response(SUCCESSFUL, {
#                 "text":       result["text"],
#                 "confidence": result["confidence"],
#                 "words":      result.get("words", []),
#                 "latency_ms": result.get("latency_ms", 0),
#             }), status=status.HTTP_200_OK)

#         except Exception as exc:
#             log.exception("STT test failed: %s", exc)
#             return Response(create_response(str(exc)),
#                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class VoiceHealthView(APIView):
#     """GET /api/voice/health/ — check STT and TTS engine status."""
#     permission_classes = (IsAuthenticated,)

#     def get(self, request):
#         health = {}
#         try:
#             from .engines.stt_vosk import get_stt_engine
#             stt          = get_stt_engine("en")
#             health["stt"] = {"engine": "vosk", "ready": stt.is_ready(),
#                               "language": "en"}
#         except Exception as exc:
#             health["stt"] = {"engine": "vosk", "ready": False, "error": str(exc)}

#         try:
#             from .engines.tts_melo import get_tts_engine
#             tts           = get_tts_engine("en")
#             health["tts"] = {"engine": "melotts", "ready": tts.is_ready(),
#                               "language": "en"}
#         except Exception as exc:
#             health["tts"] = {"engine": "melotts", "ready": False, "error": str(exc)}

#         overall = all(v.get("ready") for v in health.values())
#         return Response(
#             create_response(SUCCESSFUL, {"status": "ok" if overall else "degraded",
#                                          "engines": health}),
#             status=status.HTTP_200_OK,
#         )








"""
apps/voice/views.py  — STTTestView fix for WindowsPath on Windows.

ONLY the STTTestView is changed here.
Replace the full views.py with this content.
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


# ── Base view ─────────────────────────────────────────────────────────────────

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
            order_by = request.query_params.get(
                "order_by", self.order_by_default.lstrip("-"))
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
    serializer_class      = VoiceSessionSerializer
    list_serializer_class = VoiceSessionListSerializer
    filterset_class       = VoiceSessionFilter
    model                 = VoiceSession
    order_by_default      = "-started_at"


class TranscriptLogView(VoiceBaseView):
    serializer_class  = TranscriptLogSerializer
    filterset_class   = TranscriptLogFilter
    model             = TranscriptLog
    order_by_default  = "-timestamp"


# ── TTS test view ─────────────────────────────────────────────────────────────

class TTSTestView(APIView):
    """
    POST /api/voice/test/tts/
    Body JSON: {"text": "Hello world", "language": "en"}
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
            tts = get_tts_engine(req_ser.validated_data["language"])
            out = str(tts.synthesize(req_ser.validated_data["text"]))   # str() for Windows
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


# ── STT test view — FIXED for Windows WindowsPath bug ────────────────────────

class STTTestView(APIView):
    """
    POST /api/voice/test/stt/
    Body form-data: audio_file (WAV), language (str)
    Returns: {"text": "...", "confidence": 0.95, "latency_ms": 340}
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        req_ser = STTTestSerializer(data=request.data)
        if not req_ser.is_valid():
            return Response(create_response(get_first_error(req_ser.errors)),
                            status=status.HTTP_400_BAD_REQUEST)

        tmp_path  = None
        wav_path  = None

        try:
            from .engines.stt_vosk import get_stt_engine

            uploaded = req_ser.validated_data["audio_file"]
            language = req_ser.validated_data["language"]

            # ── Save uploaded file to a temp location ─────────────────────
            # Use tempfile.gettempdir() — works on both Windows and Linux.
            # IMPORTANT: keep the name as a plain str, never pathlib.Path,
            # because vosk.Model() and wave.open() both need str on Windows.
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)    # close the file descriptor, we'll write via open()

            with open(tmp_path, "wb") as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)

            log.info("Uploaded audio saved to: %s", tmp_path)

            # ── Check format and convert if needed ────────────────────────
            import wave as _wave
            try:
                with _wave.open(tmp_path, "rb") as wf:
                    rate = wf.getframerate()
                    ch   = wf.getnchannels()
                    sw   = wf.getsampwidth()
                    log.info("Uploaded WAV: rate=%d ch=%d width=%d", rate, ch, sw)

                if rate != 16000 or ch != 1 or sw != 2:
                    log.info("Converting audio to 16kHz mono 16-bit for Vosk")
                    wav_path = tmp_path.replace(".wav", "_converted.wav")
                    from pydub import AudioSegment
                    audio = (
                        AudioSegment.from_file(tmp_path)
                        .set_frame_rate(16000)
                        .set_channels(1)
                        .set_sample_width(2)
                    )
                    audio.export(wav_path, format="wav")
                else:
                    wav_path = tmp_path

            except Exception as conv_exc:
                log.warning("Format check failed (%s), using file as-is", conv_exc)
                wav_path = tmp_path

            # ── Run Vosk STT ──────────────────────────────────────────────
            # str() is critical here — vosk fails on WindowsPath
            stt    = get_stt_engine(language)
            result = stt.transcribe_file(str(wav_path))

            return Response(create_response(SUCCESSFUL, {
                "text":       result.get("text", ""),
                "confidence": round(result["confidence"], 3)
                              if result.get("confidence") else None,
                "words":      result.get("words", []),
                "latency_ms": result.get("latency_ms", 0),
            }), status=status.HTTP_200_OK)

        except Exception as exc:
            log.exception("STT test failed: %s", exc)
            return Response(create_response(str(exc)),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # Clean up temp files — always runs even if an exception occurred
            for path in (tmp_path, wav_path):
                if path and path != tmp_path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# ── Voice health view ─────────────────────────────────────────────────────────

class VoiceHealthView(APIView):
    """GET /api/voice/health/ — check STT and TTS engine status."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        health = {}

        try:
            from .engines.stt_vosk import get_stt_engine
            stt          = get_stt_engine("en")
            health["stt"] = {
                "engine":   "vosk",
                "ready":    stt.is_ready(),
                "language": "en",
            }
        except Exception as exc:
            health["stt"] = {"engine": "vosk", "ready": False, "error": str(exc)}

        try:
            from .engines.tts_melo import get_tts_engine
            tts           = get_tts_engine("en")
            health["tts"] = {
                "engine":   "melotts",
                "ready":    tts.is_ready(),
                "language": "en",
            }
        except Exception as exc:
            health["tts"] = {"engine": "melotts", "ready": False, "error": str(exc)}

        overall = all(v.get("ready") for v in health.values())
        return Response(
            create_response(SUCCESSFUL, {
                "status":  "ok" if overall else "degraded",
                "engines": health,
            }),
            status=status.HTTP_200_OK,
        )