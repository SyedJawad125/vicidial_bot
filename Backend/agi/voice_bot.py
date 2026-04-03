"""
agi/voice_bot.py
=================
Asterisk AGI script — the brain of the voice conversation loop.

Asterisk calls this script when a call hits the bot extension in the dialplan.
It runs as a child process, communicating with Asterisk via stdin/stdout.

Conversation loop:
  1. Answer the call.
  2. Play a greeting (TTS).
  3. Record caller audio → save to WAV.
  4. Run Vosk STT on the WAV.
  5. Pass transcript to the LLM/script engine (placeholder → next sprint).
  6. Generate TTS audio from the reply.
  7. Play TTS audio to caller.
  8. Repeat from step 3 until end-of-call condition.

Placement on your Asterisk server:
  /var/lib/asterisk/agi-bin/voice_bot.py
  chmod +x /var/lib/asterisk/agi-bin/voice_bot.py

Dialplan snippet (extensions.conf):
  [from-internal]
  exten => 9000,1,Answer()
  exten => 9000,n,AGI(voice_bot.py)
  exten => 9000,n,Hangup()

Run standalone for testing (no Asterisk):
  python agi/voice_bot.py --test --wav /path/to/test.wav
"""

import argparse
import logging
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

# ── Path setup so Django settings are importable ──────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from apps.voice.engines.stt_vosk import get_stt_engine
from apps.voice.engines.tts_melo import get_tts_engine
from apps.voice.audio_utils import (
    save_pcm_to_wav, trim_silence, get_audio_duration,
    wav_path_for_asterisk, validate_wav_format,
)
from apps.voice.session_manager import VoiceSessionManager

log = logging.getLogger("vicidial_bot.agi")

# ── Constants ─────────────────────────────────────────────────────────────────
RECORD_DIR   = Path(getattr(settings, "VOICE_AUDIO_DIR",
                             Path(settings.BASE_DIR) / "voice_audio")) / "recordings"
RECORD_DIR.mkdir(parents=True, exist_ok=True)

MAX_RECORD_SEC      = 15    # max seconds to wait for caller to speak
SILENCE_SEC         = 2     # stop recording after N seconds of silence
MAX_TURNS           = 20    # safety: hang up after this many turns
LANGUAGE            = getattr(settings, "BOT_LANGUAGE", "en")
GREETING_TEXT       = getattr(
    settings, "BOT_GREETING",
    "Hello! You have reached our automated assistant. How can I help you today?"
)
END_PHRASES = {"goodbye", "bye", "hang up", "end call", "stop"}


# ═══════════════════════════════════════════════════════════════════════════════
#  SIMPLE AGI WRAPPER
#  A minimal class so we don't depend on pyst2/panoramisk for this script.
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleAGI:
    """
    Minimal Asterisk AGI interface via stdin / stdout.
    Compatible with FastAGI (TCP) and standard AGI (subprocess).
    """

    def __init__(self, stdin=None, stdout=None):
        self._in  = stdin  or sys.stdin
        self._out = stdout or sys.stdout
        self.env  = {}
        self._read_env()

    def _read_env(self):
        """Read the AGI environment block sent by Asterisk on startup."""
        while True:
            line = self._in.readline().strip()
            if not line:
                break
            if ":" in line:
                key, _, val = line.partition(":")
                self.env[key.strip()] = val.strip()
        log.debug("AGI env: %s", self.env)

    def _send(self, cmd: str) -> dict:
        """Send a command and parse the '200 result=N' response."""
        self._out.write(cmd.rstrip() + "\n")
        self._out.flush()
        response = self._in.readline().strip()
        log.debug("AGI > %s | < %s", cmd.strip(), response)
        return self._parse_response(response)

    @staticmethod
    def _parse_response(line: str) -> dict:
        result = {"code": 0, "result": "-1", "raw": line}
        if line.startswith("200"):
            result["code"] = 200
            for part in line.split():
                if part.startswith("result="):
                    result["result"] = part.split("=", 1)[1]
        elif line.startswith("5"):
            result["code"] = int(line[:3])
        return result

    # ── AGI commands ──────────────────────────────────────────────────────────

    def answer(self) -> dict:
        return self._send("ANSWER")

    def hangup(self) -> dict:
        return self._send("HANGUP")

    def stream_file(self, filename: str, escape_digits: str = "") -> dict:
        """Play a WAV/GSM file. filename = path WITHOUT extension."""
        return self._send(f'STREAM FILE "{filename}" "{escape_digits}"')

    def record_file(
        self,
        filename: str,
        fmt: str = "wav",
        escape_digits: str = "#",
        timeout_ms: int = 15000,
        offset: int = 0,
        beep: bool = True,
        silence_sec: int = 2,
    ) -> dict:
        """
        Record caller audio to filename.fmt.
        Returns when silence_sec of silence detected or timeout reached.
        """
        beep_str    = "BEEP" if beep else ""
        silence_str = f"s={silence_sec}"
        return self._send(
            f'RECORD FILE "{filename}" {fmt} "{escape_digits}" '
            f"{timeout_ms} {offset} {beep_str} {silence_str}"
        )

    def get_variable(self, name: str) -> str:
        r = self._send(f"GET VARIABLE {name}")
        val = r.get("result", "")
        # Asterisk returns: 200 result=1 (value)
        if "(" in r.get("raw", ""):
            val = r["raw"].split("(", 1)[1].rstrip(")")
        return val

    def set_variable(self, name: str, value: str) -> dict:
        return self._send(f'SET VARIABLE {name} "{value}"')

    def verbose(self, msg: str, level: int = 1) -> dict:
        return self._send(f'VERBOSE "{msg}" {level}')

    @property
    def unique_id(self) -> str:
        return self.env.get("agi_uniqueid", str(uuid.uuid4()))

    @property
    def caller_id(self) -> str:
        return self.env.get("agi_callerid", "unknown")

    @property
    def channel(self) -> str:
        return self.env.get("agi_channel", "")


# ═══════════════════════════════════════════════════════════════════════════════
#  VOICE BOT  (conversation state machine)
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceBot:
    """
    Runs the full STT → LLM → TTS conversation loop for one call.
    """

    def __init__(self, agi: SimpleAGI):
        self.agi      = agi
        self.stt      = get_stt_engine(LANGUAGE)
        self.tts      = get_tts_engine(LANGUAGE)
        self.session  = VoiceSessionManager.create(
            unique_id=agi.unique_id,
            channel=agi.channel,
            caller_id=agi.caller_id,
        )
        self.turn     = 0
        self._running = True

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        log.info("VoiceBot started — unique_id=%s", self.agi.unique_id)
        try:
            self.agi.answer()
            self._speak(GREETING_TEXT)

            while self._running and self.turn < MAX_TURNS:
                self.turn += 1
                log.info("Turn %d / %d", self.turn, MAX_TURNS)

                # 1. Record caller
                wav_path = self._record_caller()
                if not wav_path:
                    log.info("No audio received — ending call")
                    break

                # 2. STT
                transcript = self._transcribe(wav_path)
                if not transcript:
                    self._speak("Sorry, I didn't catch that. Could you please repeat?")
                    continue

                log.info("Caller said: %s", transcript)
                self.agi.verbose(f"[STT] {transcript}")

                # 3. Check end-of-call phrases
                if any(p in transcript.lower() for p in END_PHRASES):
                    self._speak("Thank you for calling. Goodbye!")
                    break

                # 4. LLM / script engine → get reply
                reply = self._get_bot_reply(transcript)
                log.info("Bot reply: %s", reply)

                # 5. TTS → play
                self._speak(reply)

            VoiceSessionManager.complete(self.session)

        except Exception as exc:
            log.exception("VoiceBot error: %s", exc)
            VoiceSessionManager.fail(self.session, str(exc))
            try:
                self._speak("I'm sorry, an error occurred. Please call back later.")
            except Exception:
                pass
        finally:
            self.agi.hangup()

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _record_caller(self) -> str:
        """Record caller audio → WAV. Returns path or empty string on silence."""
        filename = str(RECORD_DIR / f"{self.agi.unique_id}_turn{self.turn}")
        wav_path = filename + ".wav"

        result = self.agi.record_file(
            filename=filename,
            fmt="wav",
            timeout_ms=MAX_RECORD_SEC * 1000,
            silence_sec=SILENCE_SEC,
            beep=False,
        )

        if result.get("result") == "-1":
            log.warning("record_file returned -1 (channel hung up?)")
            self._running = False
            return ""

        if not Path(wav_path).exists():
            log.warning("WAV file not created: %s", wav_path)
            return ""

        duration = get_audio_duration(wav_path)
        if duration < 0.3:
            log.info("Recording too short (%.2f s) — treating as silence", duration)
            return ""

        trim_silence(wav_path)
        VoiceSessionManager.log_stt_start(self.session, wav_path)
        return wav_path

    def _transcribe(self, wav_path: str) -> str:
        """Run Vosk STT on the WAV. Returns the transcript or empty string."""
        t0 = time.monotonic()
        try:
            ok, msg = validate_wav_format(wav_path)
            if not ok:
                log.warning("Invalid WAV format for STT: %s", msg)
                from apps.voice.audio_utils import convert_to_vosk_format
                wav_path = convert_to_vosk_format(wav_path)

            result   = self.stt.transcribe_file(wav_path)
            text     = result.get("text", "").strip()
            conf     = result.get("confidence")
            latency  = int((time.monotonic() - t0) * 1000)

            VoiceSessionManager.log_transcript(
                session=self.session,
                turn_type="stt",
                text=text,
                confidence=conf,
                audio_file=wav_path,
                latency_ms=latency,
            )
            return text

        except Exception as exc:
            log.error("STT failed: %s", exc)
            VoiceSessionManager.log_transcript(
                session=self.session,
                turn_type="err",
                text=f"STT error: {exc}",
            )
            return ""

    def _get_bot_reply(self, user_text: str) -> str:
        """
        Get bot reply from the LLM/script engine.

        ── PLACEHOLDER ──────────────────────────────────────────────────────
        Sprint 3 (AI brain) will replace this with a real LLM call.
        For now a simple rule-based script demonstrates the full pipeline.
        ─────────────────────────────────────────────────────────────────────
        """
        try:
            from apps.voice.bot_script import get_reply
            return get_reply(user_text, session=self.session)
        except ImportError:
            return self._fallback_reply(user_text)

    def _fallback_reply(self, text: str) -> str:
        """Rule-based fallback when the LLM module is not yet available."""
        t = text.lower()
        if "price" in t or "cost" in t:
            return "Our plans start at just $19 per month. Would you like more details?"
        if "yes" in t or "sure" in t or "okay" in t:
            return "Great! Let me connect you with one of our agents right away."
        if "no" in t or "not interested" in t:
            return "No problem at all. Thank you for your time. Have a wonderful day!"
        if "help" in t or "information" in t:
            return "I can help you with pricing, availability, and appointments. What would you like to know?"
        return "I understand. Could you please tell me more about what you are looking for?"

    def _speak(self, text: str) -> None:
        """Convert text → TTS audio → play to caller."""
        t0 = time.monotonic()
        try:
            wav_path = self.tts.synthesize(text)
            latency  = int((time.monotonic() - t0) * 1000)

            VoiceSessionManager.log_transcript(
                session=self.session,
                turn_type="tts",
                text=text,
                audio_file=wav_path,
                latency_ms=latency,
            )

            play_path = wav_path_for_asterisk(wav_path)
            self.agi.stream_file(play_path)

        except Exception as exc:
            log.error("TTS failed: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def _run_test_mode(wav_path: str) -> None:
    """
    Offline test: skip Asterisk, run STT + fake bot reply + TTS directly.
    Usage: python agi/voice_bot.py --test --wav /path/to/test.wav
    """
    print("=== VOICE BOT TEST MODE ===")
    print(f"STT: processing {wav_path}")

    stt    = get_stt_engine(LANGUAGE)
    result = stt.transcribe_file(wav_path)
    print(f"STT result : {result['text']!r}  (conf={result['confidence']})")

    tts    = get_tts_engine(LANGUAGE)
    reply  = "This is a test of the text-to-speech system. The pipeline is working correctly."
    out    = tts.synthesize(reply)
    print(f"TTS output : {out}")
    print("=== TEST COMPLETE ===")


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in offline test mode")
    parser.add_argument("--wav",  type=str, default="",  help="WAV file for test mode")
    args, _ = parser.parse_known_args()

    if args.test:
        if not args.wav:
            print("ERROR: --wav required in test mode")
            sys.exit(1)
        _run_test_mode(args.wav)
    else:
        # Normal AGI mode — Asterisk calls us
        agi = SimpleAGI()
        bot = VoiceBot(agi)
        bot.run()


if __name__ == "__main__":
    main()