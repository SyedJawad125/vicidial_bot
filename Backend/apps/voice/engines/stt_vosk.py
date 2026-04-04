# """
# apps/voice/engines/stt_vosk.py
# ================================
# Real-time Speech-to-Text engine using Vosk.

# How it works:
#   1. Asterisk writes raw PCM audio (16 kHz · 16-bit · mono) to a pipe/file.
#   2. VoskSTT.transcribe_stream() reads the audio in chunks and feeds Vosk.
#   3. When Vosk detects end-of-utterance it fires the on_result callback.
#   4. The AGI bridge collects results and passes them to the LLM brain.

# No API key needed — Vosk runs 100 % offline.

# Setup (one time):
#   pip install vosk
#   # Download the model (small English ≈ 40 MB):
#   # https://alphacephei.com/vosk/models  →  vosk-model-small-en-us-0.15
#   # Place the unzipped folder at:  BASE_DIR / vosk_models / en /
# """

# import json
# import logging
# import os
# import queue
# import threading
# import time
# import wave
# from pathlib import Path
# from typing import Callable, Optional

# from django.conf import settings

# log = logging.getLogger("vicidial_bot.voice.stt")

# # ── Model path resolution ───────────────────────────────────────────────────
# # Override in settings.py:  VOSK_MODELS = {"en": "/abs/path/to/model"}
# _DEFAULT_MODELS: dict[str, str] = {
#     "en": str(Path(settings.BASE_DIR) / "vosk_models" / "en"),
#     "ur": str(Path(settings.BASE_DIR) / "vosk_models" / "ur"),
# }
# VOSK_MODELS: dict[str, str] = getattr(settings, "VOSK_MODELS", _DEFAULT_MODELS)

# # Audio constants — Asterisk outputs these by default via AGI Record
# SAMPLE_RATE  = 16_000   # Hz
# CHANNELS     = 1        # mono
# SAMPLE_WIDTH = 2        # bytes  (16-bit PCM)
# CHUNK_MS     = 200      # how many ms of audio per read chunk
# CHUNK_BYTES  = int(SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * CHUNK_MS / 1000)


# class VoskSTT:
#     """
#     Wrapper around the Vosk streaming recogniser.

#     Usage (single utterance from a WAV file):
#         stt = VoskSTT(language="en")
#         result = stt.transcribe_file("/tmp/recording.wav")
#         print(result["text"], result["confidence"])

#     Usage (streaming from a byte-stream):
#         stt = VoskSTT(language="en")
#         for chunk in audio_generator:
#             partial = stt.feed_chunk(chunk)
#             if partial.get("final"):
#                 print(partial["text"])
#     """

#     def __init__(self, language: str = "en"):
#         self.language = language
#         self._model      = None
#         self._recognizer = None
#         self._load_model()

#     # ── Setup ────────────────────────────────────────────────────────────────

#     def _load_model(self) -> None:
#         """Import vosk lazily so the app starts even if vosk is not installed."""
#         try:
#             from vosk import KaldiRecognizer, Model, SetLogLevel
#             SetLogLevel(-1)  # suppress verbose Kaldi output

#             model_path = VOSK_MODELS.get(self.language)
#             if not model_path or not Path(model_path).exists():
#                 raise FileNotFoundError(
#                     f"Vosk model not found at: {model_path}\n"
#                     f"Download from https://alphacephei.com/vosk/models\n"
#                     f"Unzip to: {model_path}"
#                 )

#             log.info("Loading Vosk model from %s", model_path)
#             self._model      = Model(model_path)
#             self._recognizer = KaldiRecognizer(self._model, SAMPLE_RATE)
#             self._recognizer.SetWords(True)   # include word-level timestamps + confidences
#             log.info("Vosk model loaded (%s)", self.language)

#         except ImportError:
#             log.error("vosk is not installed. Run: pip install vosk")
#             raise

#     def _new_recognizer(self):
#         """Create a fresh recogniser (needed at start of each new utterance)."""
#         from vosk import KaldiRecognizer
#         rec = KaldiRecognizer(self._model, SAMPLE_RATE)
#         rec.SetWords(True)
#         return rec

#     # ── Core API ─────────────────────────────────────────────────────────────

#     def transcribe_file(self, wav_path: str) -> dict:
#         """
#         Transcribe a WAV file (16 kHz · 16-bit · mono).
#         Returns: {"text": str, "confidence": float, "words": list}
#         """
#         t0  = time.monotonic()
#         rec = self._new_recognizer()

#         with wave.open(wav_path, "rb") as wf:
#             if wf.getsampwidth() != SAMPLE_WIDTH or wf.getnchannels() != CHANNELS:
#                 raise ValueError(
#                     f"WAV must be {SAMPLE_WIDTH*8}-bit mono. "
#                     f"Got channels={wf.getnchannels()} width={wf.getsampwidth()}"
#                 )
#             while True:
#                 data = wf.readframes(4000)
#                 if not data:
#                     break
#                 rec.AcceptWaveform(data)

#         raw    = json.loads(rec.FinalResult())
#         result = self._parse_result(raw)
#         result["latency_ms"] = int((time.monotonic() - t0) * 1000)
#         log.debug("STT file result: %s", result)
#         return result

#     def feed_chunk(self, chunk: bytes, recognizer=None) -> dict:
#         """
#         Feed a raw PCM chunk to the recogniser.
#         Returns {"text": str, "final": bool, "confidence": float}.

#         Pass the same recognizer across calls within one utterance.
#         When final=True, create a new recognizer for the next utterance.
#         """
#         rec = recognizer or self._recognizer
#         if rec.AcceptWaveform(chunk):
#             raw    = json.loads(rec.Result())
#             result = self._parse_result(raw)
#             result["final"] = True
#         else:
#             partial = json.loads(rec.PartialResult())
#             result  = {"text": partial.get("partial", ""), "final": False, "confidence": None}
#         return result

#     def transcribe_stream(
#         self,
#         audio_source,           # file-like object or generator yielding bytes
#         on_result: Callable,    # callback(text: str, confidence: float, is_final: bool)
#         stop_event: Optional[threading.Event] = None,
#     ) -> None:
#         """
#         Continuously read from audio_source and fire on_result for each utterance.
#         Runs synchronously — call from a dedicated thread.

#         audio_source: anything with a .read(n) method or an iterable of bytes.
#         """
#         rec = self._new_recognizer()

#         def _read_chunks():
#             if hasattr(audio_source, "read"):
#                 while True:
#                     if stop_event and stop_event.is_set():
#                         return
#                     data = audio_source.read(CHUNK_BYTES)
#                     if not data:
#                         break
#                     yield data
#             else:
#                 yield from audio_source

#         for chunk in _read_chunks():
#             if stop_event and stop_event.is_set():
#                 break
#             result = self.feed_chunk(chunk, rec)
#             on_result(result["text"], result.get("confidence"), result["final"])
#             if result["final"]:
#                 rec = self._new_recognizer()   # reset for next utterance

#         # Flush any remaining audio
#         raw    = json.loads(rec.FinalResult())
#         result = self._parse_result(raw)
#         if result["text"]:
#             on_result(result["text"], result.get("confidence"), True)

#     # ── Helpers ───────────────────────────────────────────────────────────────

#     @staticmethod
#     def _parse_result(raw: dict) -> dict:
#         text  = raw.get("text", "").strip()
#         words = raw.get("result", [])
#         conf  = (
#             sum(w.get("conf", 0) for w in words) / len(words)
#             if words else None
#         )
#         return {"text": text, "confidence": conf, "words": words, "final": True}

#     def is_ready(self) -> bool:
#         return self._model is not None and self._recognizer is not None


# # ── Module-level singleton (one per language, lazily created) ─────────────────

# _instances: dict[str, VoskSTT] = {}
# _lock = threading.Lock()


# def get_stt_engine(language: str = "en") -> VoskSTT:
#     """Return a shared VoskSTT instance for the given language."""
#     if language not in _instances:
#         with _lock:
#             if language not in _instances:
#                 _instances[language] = VoskSTT(language)
#     return _instances[language]









"""
apps/voice/engines/stt_vosk.py
================================
Real-time Speech-to-Text engine using Vosk (offline, free).

FIX applied:
  - 'WindowsPath' object has no attribute 'encode'
    Root cause: vosk.Model() and vosk.KaldiRecognizer() require a plain
    Python str, NOT a pathlib.Path / WindowsPath object.
    Fix: wrap every path passed to vosk with str().
"""

import json
import logging
import os
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Optional

from django.conf import settings

log = logging.getLogger("vicidial_bot.voice.stt")

# ── Model path resolution ──────────────────────────────────────────────────────
# settings.py can override:
#   VOSK_MODELS = {"en": "F:/vicidial_bot_1/Backend/vosk_models/en"}
_DEFAULT_MODELS: dict = {
    "en": str(Path(settings.BASE_DIR) / "vosk_models" / "en"),
    "ur": str(Path(settings.BASE_DIR) / "vosk_models" / "ur"),
}

# Always convert every value to str so WindowsPath never leaks into vosk
_raw = getattr(settings, "VOSK_MODELS", _DEFAULT_MODELS)
VOSK_MODELS: dict = {k: str(v) for k, v in _raw.items()}

# Audio constants (Asterisk AGI default output)
SAMPLE_RATE  = 16_000
CHANNELS     = 1
SAMPLE_WIDTH = 2        # bytes — 16-bit PCM
CHUNK_MS     = 200
CHUNK_BYTES  = int(SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * CHUNK_MS / 1000)


class VoskSTT:
    """
    Offline Speech-to-Text wrapper around the Vosk streaming recogniser.

    Quick usage:
        stt = VoskSTT(language="en")
        result = stt.transcribe_file("recording.wav")
        print(result["text"], result["confidence"])
    """

    def __init__(self, language: str = "en"):
        self.language    = language
        self._model      = None
        self._recognizer = None
        self._load_model()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)     # silence Kaldi verbose output

            model_path = VOSK_MODELS.get(self.language)

            # ── KEY FIX: always str(), never Path/WindowsPath ──────────────
            model_path = str(model_path) if model_path else ""

            if not model_path or not Path(model_path).exists():
                raise FileNotFoundError(
                    f"Vosk model not found at: {model_path}\n"
                    f"Download from https://alphacephei.com/vosk/models\n"
                    f"Unzip to: {model_path}"
                )

            log.info("Loading Vosk model from %s", model_path)
            # str() again to be absolutely safe on Windows
            self._model      = Model(str(model_path))
            self._recognizer = KaldiRecognizer(self._model, SAMPLE_RATE)
            self._recognizer.SetWords(True)
            log.info("Vosk model loaded successfully (%s)", self.language)

        except ImportError:
            log.error("vosk is not installed. Run: pip install vosk")
            raise

    def _new_recognizer(self):
        """Fresh recogniser for each new utterance."""
        from vosk import KaldiRecognizer
        rec = KaldiRecognizer(self._model, SAMPLE_RATE)
        rec.SetWords(True)
        return rec

    # ── Core API ──────────────────────────────────────────────────────────────

    def transcribe_file(self, wav_path: str) -> dict:
        """
        Transcribe a WAV file (16 kHz · 16-bit · mono).
        Returns: {"text": str, "confidence": float, "words": list, "latency_ms": int}
        """
        # Always pass str to wave.open and vosk — never Path
        wav_path = str(wav_path)

        t0  = time.monotonic()
        rec = self._new_recognizer()

        with wave.open(wav_path, "rb") as wf:
            # If the WAV is not 16 kHz mono, convert it first
            if wf.getframerate() != SAMPLE_RATE or wf.getnchannels() != CHANNELS:
                log.warning(
                    "WAV format mismatch (rate=%d ch=%d) — converting",
                    wf.getframerate(), wf.getnchannels()
                )
                wav_path = self._convert_to_vosk_format(wav_path)
                wf.close()

        with wave.open(wav_path, "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)

        raw    = json.loads(rec.FinalResult())
        result = self._parse_result(raw)
        result["latency_ms"] = int((time.monotonic() - t0) * 1000)
        log.info("STT result: %r  conf=%.2f  latency=%dms",
                 result["text"], result["confidence"] or 0, result["latency_ms"])
        return result

    def feed_chunk(self, chunk: bytes, recognizer=None) -> dict:
        """
        Feed a raw PCM chunk to a streaming recogniser.
        Returns {"text": str, "final": bool, "confidence": float|None}.
        """
        rec = recognizer or self._recognizer
        if rec.AcceptWaveform(chunk):
            raw    = json.loads(rec.Result())
            result = self._parse_result(raw)
            result["final"] = True
        else:
            partial = json.loads(rec.PartialResult())
            result  = {"text": partial.get("partial", ""), "final": False,
                       "confidence": None}
        return result

    def transcribe_stream(
        self,
        audio_source,
        on_result: Callable,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Continuously read from audio_source and call on_result for each utterance.
        Runs synchronously — call from a dedicated thread.
        """
        rec = self._new_recognizer()

        def _chunks():
            if hasattr(audio_source, "read"):
                while True:
                    if stop_event and stop_event.is_set():
                        return
                    data = audio_source.read(CHUNK_BYTES)
                    if not data:
                        break
                    yield data
            else:
                yield from audio_source

        for chunk in _chunks():
            if stop_event and stop_event.is_set():
                break
            result = self.feed_chunk(chunk, rec)
            on_result(result["text"], result.get("confidence"), result["final"])
            if result["final"]:
                rec = self._new_recognizer()

        raw    = json.loads(rec.FinalResult())
        result = self._parse_result(raw)
        if result["text"]:
            on_result(result["text"], result.get("confidence"), True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_result(raw: dict) -> dict:
        text  = raw.get("text", "").strip()
        words = raw.get("result", [])
        conf  = (
            sum(w.get("conf", 0) for w in words) / len(words)
            if words else None
        )
        return {"text": text, "confidence": conf, "words": words, "final": True}

    @staticmethod
    def _convert_to_vosk_format(wav_path: str) -> str:
        """Convert any WAV to 16 kHz 16-bit mono. Returns new path."""
        try:
            from pydub import AudioSegment
            out_path = wav_path.replace(".wav", "_vosk.wav")
            audio = (
                AudioSegment.from_file(str(wav_path))
                .set_frame_rate(SAMPLE_RATE)
                .set_channels(CHANNELS)
                .set_sample_width(SAMPLE_WIDTH)
            )
            audio.export(str(out_path), format="wav")
            log.info("Converted to Vosk format: %s", out_path)
            return out_path
        except ImportError:
            log.warning("pydub not installed — cannot convert audio format")
            return wav_path

    def is_ready(self) -> bool:
        return self._model is not None and self._recognizer is not None


# ── Module-level singleton (one instance per language) ────────────────────────
_instances: dict = {}
_lock = threading.Lock()


def get_stt_engine(language: str = "en") -> VoskSTT:
    """Return a shared VoskSTT instance for the given language."""
    if language not in _instances:
        with _lock:
            if language not in _instances:
                _instances[language] = VoskSTT(language)
    return _instances[language]