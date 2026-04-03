"""
agi/agi_handler.py
===================
FastAGI TCP server — Asterisk connects to this process over the network
instead of spawning a new Python process for every call.

Why FastAGI instead of plain AGI?
  Plain AGI  → Asterisk forks a NEW Python process per call
               → slow startup, loads Vosk + MeloTTS models every single time
  FastAGI    → ONE persistent Python server, models loaded ONCE at startup
               → 10-100x faster response, handles concurrent calls

How the call flow works:
  1. Caller dials a number → Asterisk picks up
  2. Asterisk dialplan hits:  AGI(agi://127.0.0.1:4577/voice_bot)
  3. Asterisk opens a TCP socket to this server on port 4577
  4. This server accepts the connection, reads AGI env variables
  5. Hands the connection to VoiceBot (from agi/voice_bot.py)
  6. VoiceBot runs STT → LLM → TTS loop
  7. Connection closes when call ends

Architecture:
  ┌─────────────┐    TCP:4577     ┌──────────────────────┐
  │  Asterisk   │ ─────────────►  │  FastAGI Server      │
  │  (PBX)      │ ◄─────────────  │  (this file)         │
  └─────────────┘   AGI commands  │  ┌────────────────┐  │
                                   │  │  VoiceBot      │  │
                                   │  │  Vosk STT      │  │
                                   │  │  MeloTTS TTS   │  │
                                   │  └────────────────┘  │
                                   └──────────────────────┘

Dialplan entry (extensions.conf):
  exten => 9000,1,Answer()
  exten => 9000,n,AGI(agi://127.0.0.1:4577/voice_bot)
  exten => 9000,n,Hangup()

Start the server:
  python agi/agi_handler.py
  # or in production:
  gunicorn is NOT used here — use supervisord or systemd (see below)

Supervisord config (recommended for production):
  [program:fastagi]
  command=python /path/to/project/agi/agi_handler.py
  directory=/path/to/project
  autostart=true
  autorestart=true
  stderr_logfile=/var/log/fastagi.err.log
  stdout_logfile=/var/log/fastagi.out.log
  environment=DJANGO_SETTINGS_MODULE="config.settings"
"""

import argparse
import logging
import os
import socketserver
import sys
import threading
import time
from pathlib import Path

# ── Django setup (must happen before any app imports) ─────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings

# ── Now import our voice modules (Django is ready) ────────────────────────────
from apps.voice.engines.stt_vosk import get_stt_engine
from apps.voice.engines.tts_melo import get_tts_engine

log = logging.getLogger("vicidial_bot.fastagi")

# ── Server config ─────────────────────────────────────────────────────────────
FASTAGI_HOST    = getattr(settings, "FASTAGI_HOST", "127.0.0.1")
FASTAGI_PORT    = getattr(settings, "FASTAGI_PORT", 4577)
MAX_WORKERS     = getattr(settings, "FASTAGI_MAX_WORKERS", 20)   # max concurrent calls
LANGUAGE        = getattr(settings, "BOT_LANGUAGE", "en")


# ═══════════════════════════════════════════════════════════════════════════════
#  REQUEST HANDLER — one instance per incoming Asterisk connection
# ═══════════════════════════════════════════════════════════════════════════════

class FastAGIRequestHandler(socketserver.StreamRequestHandler):
    """
    Handles a single call from Asterisk.
    StreamRequestHandler gives us self.rfile (readable) and self.wfile (writable)
    automatically from the TCP socket.
    """

    def setup(self):
        super().setup()
        self.call_id = f"{self.client_address[0]}:{self.client_address[1]}"
        log.info("New call connection from Asterisk: %s", self.call_id)

    def handle(self):
        """Entry point — called by socketserver for every new connection."""
        try:
            # Build an AGI interface that talks over our TCP socket
            agi = SocketAGI(
                rfile=self.rfile,
                wfile=self.wfile,
                call_id=self.call_id,
            )

            # Read the script name Asterisk sends (e.g. "voice_bot")
            script_name = agi.env.get("agi_network_script", "voice_bot").strip("/")
            log.info("Script requested: %s  |  caller: %s",
                     script_name, agi.caller_id)

            # Route to the correct handler
            if script_name in ("voice_bot", ""):
                self._run_voice_bot(agi)
            else:
                log.warning("Unknown script: %s — hanging up", script_name)
                agi.verbose(f"Unknown script: {script_name}")
                agi.hangup()

        except ConnectionResetError:
            log.info("Asterisk closed connection (call ended): %s", self.call_id)
        except BrokenPipeError:
            log.info("Pipe broken (caller hung up early): %s", self.call_id)
        except Exception as exc:
            log.exception("Unhandled error in FastAGI handler: %s", exc)

    def finish(self):
        log.info("Call connection closed: %s", self.call_id)
        super().finish()

    # ── Script routers ────────────────────────────────────────────────────────

    def _run_voice_bot(self, agi):
        """Run the main voice bot conversation loop."""
        # Import here to avoid circular imports at module load time
        from agi.voice_bot import VoiceBot
        bot = VoiceBot(agi)
        bot.run()


# ═══════════════════════════════════════════════════════════════════════════════
#  SOCKET AGI  — AGI interface over a TCP socket (not stdin/stdout)
#  This is almost identical to SimpleAGI in voice_bot.py but uses
#  the TCP socket's rfile/wfile instead of sys.stdin/sys.stdout.
# ═══════════════════════════════════════════════════════════════════════════════

class SocketAGI:
    """
    AGI interface over a TCP socket connection.
    Replaces SimpleAGI (stdin/stdout) for FastAGI mode.
    """

    def __init__(self, rfile, wfile, call_id: str = ""):
        self._rfile   = rfile
        self._wfile   = wfile
        self.call_id  = call_id
        self.env      = {}
        self._read_env()

    def _read_env(self):
        """Read the AGI environment block that Asterisk sends on connection."""
        while True:
            try:
                line = self._rfile.readline()
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="replace")
                line = line.strip()
                if not line:
                    break
                if ":" in line:
                    key, _, val = line.partition(":")
                    self.env[key.strip()] = val.strip()
            except Exception as exc:
                log.warning("Error reading AGI env: %s", exc)
                break
        log.debug("AGI env keys: %s", list(self.env.keys()))

    def _send(self, cmd: str) -> dict:
        """Send a command and parse the response from Asterisk."""
        try:
            line = cmd.rstrip() + "\n"
            self._wfile.write(line.encode("utf-8"))
            self._wfile.flush()

            response = self._rfile.readline()
            if isinstance(response, bytes):
                response = response.decode("utf-8", errors="replace")
            response = response.strip()
            log.debug("[%s] > %s | < %s", self.call_id, cmd.strip(), response)
            return self._parse_response(response)

        except (BrokenPipeError, ConnectionResetError):
            log.info("Connection lost during command: %s", cmd.strip())
            return {"code": 0, "result": "-1", "raw": ""}

    @staticmethod
    def _parse_response(line: str) -> dict:
        result = {"code": 0, "result": "-1", "raw": line}
        if line.startswith("200"):
            result["code"] = 200
            for part in line.split():
                if part.startswith("result="):
                    result["result"] = part.split("=", 1)[1]
        elif line and line[0].isdigit():
            result["code"] = int(line[:3])
        return result

    # ── AGI commands (same interface as SimpleAGI) ────────────────────────────

    def answer(self) -> dict:
        return self._send("ANSWER")

    def hangup(self) -> dict:
        return self._send("HANGUP")

    def stream_file(self, filename: str, escape_digits: str = "") -> dict:
        """Play audio file. filename = path WITHOUT extension."""
        return self._send(f'STREAM FILE "{filename}" "{escape_digits}"')

    def record_file(
        self,
        filename: str,
        fmt: str = "wav",
        escape_digits: str = "#",
        timeout_ms: int = 15000,
        offset: int = 0,
        beep: bool = False,
        silence_sec: int = 2,
    ) -> dict:
        beep_str    = "BEEP" if beep else ""
        silence_str = f"s={silence_sec}"
        return self._send(
            f'RECORD FILE "{filename}" {fmt} "{escape_digits}" '
            f"{timeout_ms} {offset} {beep_str} {silence_str}"
        )

    def get_variable(self, name: str) -> str:
        r = self._send(f"GET VARIABLE {name}")
        raw = r.get("raw", "")
        if "(" in raw:
            return raw.split("(", 1)[1].rstrip(")")
        return r.get("result", "")

    def set_variable(self, name: str, value: str) -> dict:
        return self._send(f'SET VARIABLE {name} "{value}"')

    def verbose(self, msg: str, level: int = 1) -> dict:
        # Sanitise message — no newlines allowed in AGI VERBOSE
        msg = msg.replace("\n", " ").replace("\r", "")
        return self._send(f'VERBOSE "{msg}" {level}')

    def exec_app(self, app: str, options: str = "") -> dict:
        """Run an Asterisk dialplan application."""
        return self._send(f'EXEC {app} "{options}"')

    def play_digits(self, digits: str) -> dict:
        """Play DTMF digits to the caller."""
        return self._send(f"SAY DIGITS {digits} \"\"")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def unique_id(self) -> str:
        return self.env.get("agi_uniqueid", self.call_id)

    @property
    def caller_id(self) -> str:
        return self.env.get("agi_callerid", "unknown")

    @property
    def channel(self) -> str:
        return self.env.get("agi_channel", "")

    @property
    def extension(self) -> str:
        return self.env.get("agi_extension", "")

    @property
    def network_script(self) -> str:
        return self.env.get("agi_network_script", "")


# ═══════════════════════════════════════════════════════════════════════════════
#  THREADED TCP SERVER
# ═══════════════════════════════════════════════════════════════════════════════

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Each call runs in its own thread.
    ThreadingMixIn handles the thread creation automatically.
    """
    allow_reuse_address  = True    # restart server without waiting for TIME_WAIT
    daemon_threads       = True    # threads die when main process exits
    request_queue_size   = 50      # backlog queue for incoming connections


# ═══════════════════════════════════════════════════════════════════════════════
#  PRE-LOAD ENGINES  (run once at startup, before first call arrives)
# ═══════════════════════════════════════════════════════════════════════════════

def preload_engines(language: str = "en") -> None:
    """
    Load Vosk model and MeloTTS model into memory at server startup.
    This means the FIRST caller does NOT pay the model-loading penalty.

    Vosk model load time:  ~1-3 seconds  (small model)
    MeloTTS model load:    ~5-15 seconds (downloads on first run)
    """
    log.info("Pre-loading voice engines (language=%s)...", language)
    start = time.monotonic()

    try:
        stt = get_stt_engine(language)
        log.info("  ✓ Vosk STT ready  (%.1fs)", time.monotonic() - start)
    except Exception as exc:
        log.error("  ✗ Vosk STT failed: %s", exc)

    try:
        tts = get_tts_engine(language)
        # Warm-up: synthesize a short phrase so first call gets instant TTS
        _warmup_path = tts.synthesize("System ready.", output_path="/tmp/_agi_warmup.wav")
        import os as _os
        try:
            _os.unlink(_warmup_path)
        except Exception:
            pass
        log.info("  ✓ MeloTTS TTS ready (%.1fs)", time.monotonic() - start)
    except Exception as exc:
        log.error("  ✗ MeloTTS TTS failed: %s", exc)

    log.info("Engine pre-load complete in %.1fs", time.monotonic() - start)


# ═══════════════════════════════════════════════════════════════════════════════
#  SERVER LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

def start_server(host: str = FASTAGI_HOST, port: int = FASTAGI_PORT) -> None:
    """Start the FastAGI server (blocking)."""

    # 1. Pre-load all engines BEFORE accepting connections
    preload_engines(LANGUAGE)

    # 2. Start the TCP server
    server = ThreadedTCPServer((host, port), FastAGIRequestHandler)

    log.info("=" * 60)
    log.info("FastAGI server started")
    log.info("  Listening on : %s:%d", host, port)
    log.info("  Max workers  : %d", MAX_WORKERS)
    log.info("  Language     : %s", LANGUAGE)
    log.info("")
    log.info("Asterisk dialplan entry:")
    log.info("  exten => 9000,1,Answer()")
    log.info("  exten => 9000,n,AGI(agi://%s:%d/voice_bot)", host, port)
    log.info("  exten => 9000,n,Hangup()")
    log.info("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("FastAGI server shutting down...")
        server.shutdown()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/fastagi.log", mode="a"),
        ],
    )

    parser = argparse.ArgumentParser(description="VICIdial Bot — FastAGI Server")
    parser.add_argument("--host", default=FASTAGI_HOST,
                        help=f"Bind host (default: {FASTAGI_HOST})")
    parser.add_argument("--port", type=int, default=FASTAGI_PORT,
                        help=f"Bind port (default: {FASTAGI_PORT})")
    parser.add_argument("--test-engines", action="store_true",
                        help="Test STT + TTS engines then exit (no server)")
    args = parser.parse_args()

    if args.test_engines:
        _test_engines()
        return

    # Make sure log directory exists
    Path("logs").mkdir(exist_ok=True)

    start_server(args.host, args.port)


def _test_engines():
    """Quick engine test — runs STT + TTS and prints results."""
    print("\n=== ENGINE TEST ===")

    print("\n[1] Testing MeloTTS...")
    try:
        tts  = get_tts_engine("en")
        path = tts.synthesize("Hello! The voice pipeline is working correctly.")
        print(f"    ✓ TTS output saved to: {path}")
    except Exception as exc:
        print(f"    ✗ TTS FAILED: {exc}")

    print("\n[2] Testing Vosk STT...")
    try:
        stt  = get_stt_engine("en")
        ready = stt.is_ready()
        print(f"    ✓ Vosk model loaded: {ready}")
    except Exception as exc:
        print(f"    ✗ STT FAILED: {exc}")

    print("\n=== TEST COMPLETE ===\n")


if __name__ == "__main__":
    main()