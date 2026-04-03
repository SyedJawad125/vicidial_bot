"""
apps/voice/engines/tts_melo.py
================================
Text-to-Speech engine using MeloTTS (free · offline · multi-language).

How it works:
  1. Bot logic produces a reply text string.
  2. MeloTTS.synthesize() generates a WAV file from that text.
  3. The AGI bridge plays the WAV back to the caller via Asterisk STREAM FILE.

No API key needed — MeloTTS runs 100 % offline after model download.

Setup (one time):
  pip install git+https://github.com/myshell-ai/MeloTTS.git
  python -m unidic download          # needed by MeloTTS for Japanese (safe to run for all)
  # Models are downloaded automatically on first use (cached in ~/.cache/huggingface/).

Supported MeloTTS language codes:
  EN  (English)
  ZH  (Chinese)
  FR  (French)
  ES  (Spanish)
  KR  (Korean)
  JA  (Japanese)

  Note: Urdu (ur) is NOT natively supported by MeloTTS.
        For Urdu use gTTS as the fallback (internet required).
"""

import logging
import os
import time
import threading
import uuid
from pathlib import Path
from typing import Optional

from django.conf import settings

log = logging.getLogger("vicidial_bot.voice.tts")

# ── Config ────────────────────────────────────────────────────────────────────
# Override in settings.py as needed.
TTS_AUDIO_DIR: Path = Path(
    getattr(settings, "VOICE_AUDIO_DIR", Path(settings.BASE_DIR) / "voice_audio" / "tts")
)
TTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# MeloTTS speaker IDs — English has multiple accents
MELO_SPEAKERS: dict = {
    "en": {"speaker": "EN-Default", "speed": 1.0},
    "en-us": {"speaker": "EN-US",     "speed": 1.0},
    "en-br": {"speaker": "EN-BR",     "speed": 1.0},
    "zh":    {"speaker": "ZH",        "speed": 1.0},
    "fr":    {"speaker": "FR",        "speed": 1.0},
    "es":    {"speaker": "ES",        "speed": 1.0},
    "kr":    {"speaker": "KR",        "speed": 1.0},
    "ja":    {"speaker": "JA",        "speed": 1.0},
}

# Languages that fall back to gTTS (internet needed)
GTTS_FALLBACK_LANGS = {"ur", "ar", "hi", "bn"}


class MeloTTS:
    """
    Wrapper around MeloTTS for offline, high-quality TTS.

    Usage:
        tts = MeloTTS(language="en")
        path = tts.synthesize("Hello, how are you today?")
        # path → /voice_audio/tts/<uuid>.wav  (16 kHz mono WAV)
    """

    def __init__(self, language: str = "en"):
        self.language = language.lower()
        self._model   = None
        self._speaker_ids = None
        self._load_model()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """Import MeloTTS lazily and load the model for the requested language."""
        if self.language in GTTS_FALLBACK_LANGS:
            log.info("Language '%s' uses gTTS fallback (online)", self.language)
            return

        melo_lang = self._resolve_melo_lang()
        try:
            from melo.api import TTS as _MeloTTS
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            log.info("Loading MeloTTS model — lang=%s  device=%s", melo_lang, device)

            self._model = _MeloTTS(language=melo_lang, device=device)
            self._speaker_ids = self._model.hps.data.spk2id
            log.info("MeloTTS ready (%s)", melo_lang)

        except ImportError:
            log.error(
                "MeloTTS is not installed.\n"
                "Run: pip install git+https://github.com/myshell-ai/MeloTTS.git\n"
                "     python -m unidic download"
            )
            raise

    def _resolve_melo_lang(self) -> str:
        """Map our language code to MeloTTS language string."""
        mapping = {
            "en": "EN", "en-us": "EN", "en-br": "EN",
            "zh": "ZH", "fr": "FR",
            "es": "ES", "kr": "KR", "ja": "JA",
        }
        resolved = mapping.get(self.language, "EN")
        log.debug("Language '%s' → MeloTTS '%s'", self.language, resolved)
        return resolved

    # ── Core API ──────────────────────────────────────────────────────────────

    def synthesize(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Convert text to speech and save as a 16 kHz mono WAV.

        Returns the absolute path to the output WAV file.
        Raises RuntimeError on failure.
        """
        if not text or not text.strip():
            raise ValueError("synthesize() received empty text")

        if output_path is None:
            output_path = str(TTS_AUDIO_DIR / f"{uuid.uuid4().hex}.wav")

        t0 = time.monotonic()

        if self.language in GTTS_FALLBACK_LANGS:
            output_path = self._synthesize_gtts(text, output_path)
        else:
            output_path = self._synthesize_melo(text, output_path)

        latency = int((time.monotonic() - t0) * 1000)
        log.info("TTS generated in %d ms → %s", latency, output_path)
        return output_path

    def _synthesize_melo(self, text: str, output_path: str) -> str:
        """Generate audio with MeloTTS and convert to 16 kHz mono."""
        cfg     = MELO_SPEAKERS.get(self.language, MELO_SPEAKERS["en"])
        speaker = cfg["speaker"]
        speed   = cfg["speed"]

        # Look up speaker ID
        speaker_id = self._speaker_ids.get(speaker)
        if speaker_id is None:
            # Fall back to first available speaker
            speaker_id = next(iter(self._speaker_ids.values()))
            log.warning("Speaker '%s' not found, using id=%s", speaker, speaker_id)

        # MeloTTS writes a WAV directly — we then resample to 16 kHz for Asterisk
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        self._model.tts_to_file(text, speaker_id, tmp_path, speed=speed)
        self._resample_to_asterisk(tmp_path, output_path)
        os.unlink(tmp_path)
        return output_path

    def _synthesize_gtts(self, text: str, output_path: str) -> str:
        """
        Fallback: use gTTS (internet required) for languages MeloTTS doesn't support.
        Converts MP3 → WAV 16 kHz mono.
        """
        try:
            from gtts import gTTS
            import tempfile

            log.info("gTTS fallback for language '%s'", self.language)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                mp3_path = tmp.name

            gTTS(text=text, lang=self.language, slow=False).save(mp3_path)
            self._mp3_to_wav(mp3_path, output_path)
            os.unlink(mp3_path)
            return output_path

        except ImportError:
            raise ImportError("gTTS not installed. Run: pip install gtts")

    # ── Audio conversion helpers ──────────────────────────────────────────────

    @staticmethod
    def _resample_to_asterisk(src_wav: str, dst_wav: str) -> None:
        """
        Resample any WAV → 16 kHz · 16-bit · mono (what Asterisk AGI needs).
        Uses pydub + ffmpeg (ffmpeg must be installed on the server).
        """
        try:
            from pydub import AudioSegment
            audio = (
                AudioSegment.from_wav(src_wav)
                .set_frame_rate(16_000)
                .set_channels(1)
                .set_sample_width(2)
            )
            audio.export(dst_wav, format="wav")
        except ImportError:
            # pydub not available — try raw copy (may not be 16 kHz)
            import shutil
            shutil.copy(src_wav, dst_wav)
            log.warning("pydub not installed — WAV not resampled. Install: pip install pydub")

    @staticmethod
    def _mp3_to_wav(mp3_path: str, wav_path: str) -> None:
        """Convert MP3 → WAV 16 kHz mono."""
        try:
            from pydub import AudioSegment
            audio = (
                AudioSegment.from_mp3(mp3_path)
                .set_frame_rate(16_000)
                .set_channels(1)
                .set_sample_width(2)
            )
            audio.export(wav_path, format="wav")
        except ImportError:
            raise ImportError("pydub not installed. Run: pip install pydub")

    def is_ready(self) -> bool:
        if self.language in GTTS_FALLBACK_LANGS:
            return True   # gTTS is always ready (internet-dependent)
        return self._model is not None


# ── Module-level singleton ────────────────────────────────────────────────────

_instances: dict[str, MeloTTS] = {}
_lock = threading.Lock()


def get_tts_engine(language: str = "en") -> MeloTTS:
    """Return a shared MeloTTS instance for the given language."""
    language = language.lower()
    if language not in _instances:
        with _lock:
            if language not in _instances:
                _instances[language] = MeloTTS(language)
    return _instances[language]