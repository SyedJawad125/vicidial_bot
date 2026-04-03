#!/usr/bin/env python3
"""
run_standalone.py
=================
Run the VICIdial Bot WITHOUT Django — pure Python, no DB, no web server.
Useful for testing AMI connectivity before setting up Django.

Usage:
    python run_standalone.py

All config is read from environment variables or the .env file.
"""

import os
import sys
import logging
import time
import json
from pathlib import Path

# Load .env manually (no django-decouple needed here)
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# Simple logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/standalone.log"),
    ],
)
log = logging.getLogger("standalone_bot")


def main():
    # Import after path setup
    sys.path.insert(0, str(Path(__file__).parent))
    from bot.ami_client import AMIClient, AMIEvent
    from bot.vicidial_api import VICIdialAPI, VICIdialAPIError

    AMI_HOST   = os.getenv("VICIDIAL_AMI_HOST",   "127.0.0.1")
    AMI_PORT   = int(os.getenv("VICIDIAL_AMI_PORT", "5038"))
    AMI_USER   = os.getenv("VICIDIAL_AMI_USER",   "admin")
    AMI_SECRET = os.getenv("VICIDIAL_AMI_SECRET", "amp111")

    VICI_URL   = os.getenv("VICIDIAL_URL",      "http://127.0.0.1")
    VICI_USER  = os.getenv("VICIDIAL_API_USER", "admin")
    VICI_PASS  = os.getenv("VICIDIAL_API_PASS", "password")

    print("\n" + "═" * 52)
    print("  VICIdial Bot — Standalone Mode")
    print("═" * 52)
    print(f"  AMI:      {AMI_HOST}:{AMI_PORT} (user={AMI_USER})")
    print(f"  VICIdial: {VICI_URL}")
    print("═" * 52 + "\n")

    # ── AMI Client ──────────────────────────────────────
    ami = AMIClient(AMI_HOST, AMI_PORT, AMI_USER, AMI_SECRET)

    # ── Register event handlers ──────────────────────────

    @ami.on("_Connected")
    def on_connected(e):
        print("  ✓ AMI connected to VICIdial!")

        # Test: ping
        if ami.ping():
            print("  ✓ Ping OK")

        # Test: list active channels
        ami.core_show_channels()

    @ami.on("_Disconnected")
    def on_disconnected(e):
        print("  ✗ AMI disconnected — reconnecting…")

    @ami.on("Newchannel")
    def on_newchannel(e):
        print(f"  📞 NEW CALL: channel={e.get('Channel')} "
              f"cid={e.get('CallerIDNum')} uid={e.get('Uniqueid')}")

    @ami.on("Hangup")
    def on_hangup(e):
        cause = e.get("Cause-txt", e.get("Cause", "?"))
        print(f"  📵 HANGUP: channel={e.get('Channel')} cause={cause}")

    @ami.on("AgentLogin")
    def on_agent_login(e):
        print(f"  👤 AGENT LOGIN: {e.get('Agent', e.get('User', '?'))}")

    @ami.on("AgentLogoff")
    def on_agent_logoff(e):
        print(f"  👤 AGENT LOGOUT: {e.get('Agent', e.get('User', '?'))}")

    @ami.on("DialBegin")
    def on_dial(e):
        print(f"  🔔 DIALING: {e.get('Channel')} → {e.get('DestCallerIDNum', '?')}")

    @ami.on("DialEnd")
    def on_dial_end(e):
        print(f"  {'✅' if e.get('DialStatus') == 'ANSWER' else '❌'} "
              f"DIAL END: status={e.get('DialStatus')}")

    @ami.on("VarSet")
    def on_varset(e):
        var = e.get("Variable", "")
        if var.startswith("VICIDIAL_"):
            print(f"  📋 VICIDIAL VAR: {var}={e.get('Value')}")

    @ami.on("*")
    def log_all(e):
        if e.name and not e.name.startswith("_"):
            log.debug(f"EVENT: {e.name} {dict(e)}")

    # ── Start AMI ────────────────────────────────────────
    ami.start()
    print("  Connecting to VICIdial…")

    if not ami.wait_until_connected(timeout=15):
        print("  ✗ Could not connect. Check:")
        print(f"    - Is VICIdial running at {AMI_HOST}:{AMI_PORT}?")
        print(f"    - Is AMI enabled in /etc/asterisk/manager.conf?")
        print(f"    - Is user '{AMI_USER}' allowed in manager.conf?")
        print()
    else:
        # ── Test VICIdial HTTP API ────────────────────────
        print("\n  Testing VICIdial HTTP API…")
        api = VICIdialAPI(VICI_URL, VICI_USER, VICI_PASS)
        try:
            campaigns = api.get_campaigns()
            print(f"  ✓ API connected. Found {len(campaigns)} campaigns.")
            for c in campaigns[:5]:
                print(f"    - {c}")
        except VICIdialAPIError as e:
            print(f"  ⚠ API error: {e}")

    print("\n  Listening for AMI events (Ctrl+C to stop)…\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping…")
        ami.stop()
        print("  Done. Bye!")


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    main()
