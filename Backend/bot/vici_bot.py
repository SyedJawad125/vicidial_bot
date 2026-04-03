"""
bot/vici_bot.py
===============
The VICIdial Bot — ties AMI events + API calls together.

This is the brain. It:
  - Listens to ALL AMI events from VICIdial in real-time
  - Reacts to events: call placed, answered, hung up, agent login/logout, etc.
  - Logs everything to a database via Django ORM
  - Exposes status via a shared state object (read by the DRF API)
  - Can be commanded: originate calls, send DTMF, transfer calls, etc.

Usage (standalone or via Django management command):
    bot = VICIBot(settings)
    bot.start()
    bot.wait()   # blocks until Ctrl-C
"""

import threading
import time
import logging
import queue
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from .ami_client import AMIClient, AMIEvent
from .vicidial_api import VICIdialAPI, VICIdialAPIError

log = logging.getLogger("vicidial_bot.vici_bot")


@dataclass
class BotConfig:
    """All settings the bot needs."""
    # Asterisk AMI
    ami_host:   str = "127.0.0.1"
    ami_port:   int = 5038
    ami_user:   str = "admin"
    ami_secret: str = "amp111"

    # VICIdial HTTP API
    vicidial_url:      str = "http://127.0.0.1"
    vicidial_api_user: str = "admin"
    vicidial_api_pass: str = "password"

    # Behaviour
    log_all_events:  bool = True    # log every AMI event to DB
    auto_dnc:        bool = True    # auto-add "REMOVE" dispositions to DNC


@dataclass
class ActiveCall:
    """Snapshot of a live call from AMI events."""
    unique_id:   str
    channel:     str
    caller_id:   str   = ""
    destination: str   = ""
    state:       str   = "RINGING"     # RINGING → ANSWERED → HUNGUP
    started_at:  datetime = field(default_factory=datetime.now)
    answered_at: Optional[datetime] = None
    ended_at:    Optional[datetime] = None
    campaign_id: str   = ""
    agent_user:  str   = ""

    @property
    def duration_sec(self) -> int:
        if self.answered_at and self.ended_at:
            return int((self.ended_at - self.answered_at).total_seconds())
        return 0


class BotState:
    """
    Thread-safe snapshot of the bot's current state.
    Read by the DRF API views without touching the bot directly.
    """
    def __init__(self):
        self._lock        = threading.Lock()
        self.running      = False
        self.connected    = False
        self.started_at:  Optional[datetime] = None
        self.active_calls: dict[str, ActiveCall] = {}   # unique_id → ActiveCall
        self.event_count  = 0
        self.error_count  = 0
        self.last_event:  Optional[str] = None
        self.last_event_at: Optional[datetime] = None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running":        self.running,
                "connected":      self.connected,
                "started_at":     self.started_at.isoformat() if self.started_at else None,
                "active_calls":   len(self.active_calls),
                "event_count":    self.event_count,
                "error_count":    self.error_count,
                "last_event":     self.last_event,
                "last_event_at":  self.last_event_at.isoformat() if self.last_event_at else None,
                "calls": [
                    {
                        "unique_id":   c.unique_id,
                        "channel":     c.channel,
                        "caller_id":   c.caller_id,
                        "destination": c.destination,
                        "state":       c.state,
                        "duration_sec": c.duration_sec,
                        "campaign_id": c.campaign_id,
                        "agent_user":  c.agent_user,
                    }
                    for c in self.active_calls.values()
                ],
            }

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def record_event(self, event_name: str):
        with self._lock:
            self.event_count  += 1
            self.last_event    = event_name
            self.last_event_at = datetime.now()

    def add_call(self, call: ActiveCall):
        with self._lock:
            self.active_calls[call.unique_id] = call

    def update_call(self, unique_id: str, **kwargs):
        with self._lock:
            if unique_id in self.active_calls:
                for k, v in kwargs.items():
                    setattr(self.active_calls[unique_id], k, v)

    def remove_call(self, unique_id: str) -> Optional[ActiveCall]:
        with self._lock:
            return self.active_calls.pop(unique_id, None)


# Global state — shared between bot thread and DRF views
bot_state = BotState()


class VICIBot:
    """
    The main bot class.

    Start it once at Django startup (AppConfig.ready or management command).
    The bot runs in background threads — Django views interact via bot_state
    and the command_queue.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.state  = bot_state

        self.ami = AMIClient(
            host=config.ami_host,
            port=config.ami_port,
            username=config.ami_user,
            secret=config.ami_secret,
        )
        self.api = VICIdialAPI(
            server=config.vicidial_url,
            user=config.vicidial_api_user,
            password=config.vicidial_api_pass,
        )

        # Commands from DRF views → bot thread
        self.command_queue: queue.Queue = queue.Queue()

        self._register_handlers()

    # ──────────────────────────────────────────────────────
    #  Lifecycle
    # ──────────────────────────────────────────────────────

    def start(self):
        """Start bot: AMI connection + command processor."""
        log.info("VICIBot starting…")
        self.state.update(running=True, started_at=datetime.now())

        self.ami.start()

        # Command processor thread
        threading.Thread(
            target=self._command_loop,
            daemon=True,
            name="bot-commands",
        ).start()

        log.info("VICIBot running")

    def stop(self):
        self.ami.stop()
        self.state.update(running=False, connected=False)
        log.info("VICIBot stopped")

    def wait(self):
        """Block forever (use in management command)."""
        try:
            while self.state.running:
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("Shutting down…")
            self.stop()

    # ──────────────────────────────────────────────────────
    #  AMI Event Handlers
    # ──────────────────────────────────────────────────────

    def _register_handlers(self):
        ami = self.ami

        @ami.on("_Connected")
        def on_connected(event):
            self.state.update(connected=True)
            log.info("✓ AMI connected to VICIdial")
            self._db_log("SYSTEM", "AMI connected to VICIdial")

        @ami.on("_Disconnected")
        def on_disconnected(event):
            self.state.update(connected=False)
            log.warning("✗ AMI disconnected from VICIdial")
            self._db_log("SYSTEM", "AMI disconnected from VICIdial")

        @ami.on("Newchannel")
        def on_new_channel(event):
            """New outbound call initiated."""
            uid     = event.get("Uniqueid", "")
            channel = event.get("Channel", "")
            cid     = event.get("CallerIDNum", "")
            if not uid:
                return
            call = ActiveCall(unique_id=uid, channel=channel, caller_id=cid, state="RINGING")
            self.state.add_call(call)
            self.state.record_event("Newchannel")
            log.info(f"📞 New call: {channel} CID={cid}")
            self._db_log("CALL_STARTED", f"New channel: {channel}", event=event)

        @ami.on("DialBegin")
        def on_dial_begin(event):
            uid  = event.get("Uniqueid", "")
            dest = event.get("DestCallerIDNum", event.get("Destination", ""))
            self.state.update_call(uid, destination=dest, state="DIALING")
            self.state.record_event("DialBegin")
            log.info(f"🔔 Dialing: {event.get('Channel')} → {dest}")

        @ami.on("DialEnd")
        def on_dial_end(event):
            uid      = event.get("Uniqueid", "")
            dial_status = event.get("DialStatus", "")
            if dial_status == "ANSWER":
                self.state.update_call(uid, state="ANSWERED", answered_at=datetime.now())
                log.info(f"✅ Answered: {event.get('Channel')}")
                self._db_log("CALL_ANSWERED", f"Call answered", event=event)
            else:
                self.state.update_call(uid, state=dial_status or "FAILED")
                log.info(f"❌ Dial ended: {dial_status} — {event.get('Channel')}")

        @ami.on("Hangup")
        def on_hangup(event):
            uid   = event.get("Uniqueid", "")
            cause = event.get("Cause-txt", event.get("Cause", ""))
            call  = self.state.remove_call(uid)
            self.state.record_event("Hangup")
            if call:
                call.ended_at = datetime.now()
                log.info(f"📵 Hung up: {call.channel} duration={call.duration_sec}s cause={cause}")
                self._db_log("CALL_ENDED", f"Hangup cause={cause} duration={call.duration_sec}s", event=event)
                self._save_call_record(call, cause)
            else:
                log.debug(f"Hangup for unknown UID {uid}")

        @ami.on("AgentLogin")
        def on_agent_login(event):
            agent = event.get("Agent", event.get("User", ""))
            log.info(f"👤 Agent logged in: {agent}")
            self._db_log("AGENT", f"Agent login: {agent}", event=event)
            self.state.record_event("AgentLogin")

        @ami.on("AgentLogoff")
        def on_agent_logoff(event):
            agent = event.get("Agent", event.get("User", ""))
            log.info(f"👤 Agent logged out: {agent}")
            self._db_log("AGENT", f"Agent logout: {agent}", event=event)
            self.state.record_event("AgentLogoff")

        @ami.on("AgentCalled")
        def on_agent_called(event):
            """Agent is being connected to a customer."""
            agent   = event.get("AgentCalled", "")
            uid     = event.get("Uniqueid", "")
            cid     = event.get("CallerIDNum", "")
            self.state.update_call(uid, agent_user=agent)
            log.info(f"📡 Agent called: {agent} for caller {cid}")
            self.state.record_event("AgentCalled")

        @ami.on("AgentComplete")
        def on_agent_complete(event):
            """Call between agent and customer completed."""
            agent    = event.get("MemberName", "")
            talk_sec = event.get("TalkTime", "0")
            wait_sec = event.get("WaitTime", "0")
            log.info(f"✓ Agent completed: {agent} talk={talk_sec}s wait={wait_sec}s")
            self._db_log("AGENT", f"Call complete: agent={agent} talk={talk_sec}s", event=event)
            self.state.record_event("AgentComplete")

        @ami.on("VarSet")
        def on_var_set(event):
            """VICIdial sets channel variables — useful for disposition tracking."""
            var   = event.get("Variable", "")
            value = event.get("Value", "")
            uid   = event.get("Uniqueid", "")

            if var == "VICIDIAL_CAMPAIGN":
                self.state.update_call(uid, campaign_id=value)
            elif var == "VICIDIAL_DISPOSITION" and self.config.auto_dnc:
                if value in ("DNC", "DNCL", "REMOVE"):
                    phone = event.get("CallerIDNum", "")
                    if phone:
                        self._handle_dnc(phone, value)

        @ami.on("*")
        def on_all(event):
            """Log every event to state counters."""
            if event.name not in ("", "_Connected", "_Disconnected"):
                self.state.record_event(event.name)
                if self.config.log_all_events:
                    self._db_log_event_raw(event)

    # ──────────────────────────────────────────────────────
    #  Command Interface (called from DRF views via queue)
    # ──────────────────────────────────────────────────────

    def send_command(self, command: str, **kwargs) -> dict:
        """
        Send a command to the bot from outside (DRF views).
        Returns immediately with a task_id; result is async.
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]
        self.command_queue.put({"cmd": command, "kwargs": kwargs, "task_id": task_id})
        log.info(f"Command queued: {command} {kwargs}")
        return {"task_id": task_id, "status": "queued"}

    def execute_now(self, command: str, **kwargs) -> dict:
        """
        Execute a command synchronously (blocks, returns result).
        Use only from within bot thread or management commands.
        """
        return self._execute(command, kwargs)

    def _command_loop(self):
        """Process commands from the queue."""
        while True:
            try:
                item = self.command_queue.get(timeout=1)
                result = self._execute(item["cmd"], item.get("kwargs", {}))
                log.info(f"Command {item['cmd']} result: {result}")
            except queue.Empty:
                continue
            except Exception as e:
                log.error(f"Command error: {e}", exc_info=True)

    def _execute(self, command: str, kwargs: dict) -> dict:
        """Route command to the right method."""
        handlers = {
            "originate":        self._cmd_originate,
            "hangup":           self._cmd_hangup,
            "transfer":         self._cmd_transfer,
            "dtmf":             self._cmd_dtmf,
            "add_lead":         self._cmd_add_lead,
            "update_lead":      self._cmd_update_lead,
            "logout_agent":     self._cmd_logout_agent,
            "dnc_add":          self._cmd_dnc_add,
            "campaign_pause":   self._cmd_campaign_pause,
            "campaign_activate":self._cmd_campaign_activate,
            "ping":             self._cmd_ping,
        }
        fn = handlers.get(command)
        if not fn:
            return {"error": f"Unknown command: {command}"}
        try:
            return fn(**kwargs) or {"status": "ok"}
        except Exception as e:
            log.error(f"Command {command} failed: {e}", exc_info=True)
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────
    #  Command implementations
    # ──────────────────────────────────────────────────────

    def _cmd_originate(self, phone: str, campaign_id: str = "", caller_id: str = "", **_):
        """Dial a phone number via Asterisk."""
        trunk = campaign_id or "default"
        resp = self.ami.originate(
            channel=f"SIP/{trunk}/{phone}",
            context="vicidial-auto-dial",
            exten="s",
            priority="1",
            caller_id=caller_id or f"<{phone}>",
            variables={"CAMPAIGN_ID": campaign_id},
        )
        log.info(f"Originate {phone}: {resp}")
        return {"status": "originated", "response": dict(resp) if resp else {}}

    def _cmd_hangup(self, channel: str, **_):
        resp = self.ami.hangup(channel)
        return {"status": "hungup", "response": dict(resp) if resp else {}}

    def _cmd_transfer(self, channel: str, destination: str, context: str = "default", **_):
        resp = self.ami.redirect(channel, context, destination)
        return {"status": "transferred"}

    def _cmd_dtmf(self, channel: str, digit: str, **_):
        resp = self.ami.send_action({
            "Action":  "PlayDTMF",
            "Channel": channel,
            "Digit":   digit,
        })
        return {"status": "dtmf_sent", "digit": digit}

    def _cmd_add_lead(self, phone: str, campaign_id: str,
                      first_name: str = "", last_name: str = "",
                      email: str = "", **kwargs):
        try:
            result = self.api.add_lead(
                phone_number=phone,
                campaign_id=campaign_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
            return result
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_update_lead(self, lead_id: str, status: str, **_):
        try:
            return self.api.update_lead_status(lead_id, status)
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_logout_agent(self, agent_user: str, **_):
        try:
            return self.api.logout_agent(agent_user)
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_dnc_add(self, phone: str, **_):
        try:
            return self.api.add_to_dnc(phone)
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_campaign_pause(self, campaign_id: str, **_):
        try:
            return self.api.update_campaign_dial_status(campaign_id, "PAUSED")
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_campaign_activate(self, campaign_id: str, **_):
        try:
            return self.api.update_campaign_dial_status(campaign_id, "ACTIVE")
        except VICIdialAPIError as e:
            return {"error": str(e)}

    def _cmd_ping(self, **_):
        alive = self.ami.ping()
        return {"ami_alive": alive, "connected": self.state.connected}

    # ──────────────────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────────────────

    def _handle_dnc(self, phone: str, disposition: str):
        """Auto-add phone to DNC list when agent dispositions it."""
        try:
            self.api.add_to_dnc(phone)
            log.info(f"Auto-DNC: {phone} (disposition={disposition})")
            self._db_log("DNC", f"Auto-added to DNC: {phone} (dispo={disposition})")
        except Exception as e:
            log.error(f"Auto-DNC failed for {phone}: {e}")

    def _save_call_record(self, call: ActiveCall, cause: str):
        """Save completed call to Django DB (non-blocking)."""
        try:
            from .db_writer import save_call_log
            save_call_log(call, cause)
        except Exception as e:
            log.warning(f"Could not save call record: {e}")

    def _db_log(self, event_type: str, message: str, event: AMIEvent = None):
        """Write a log entry to the Django DB (non-blocking)."""
        try:
            from .db_writer import write_event_log
            write_event_log(event_type, message, dict(event) if event else {})
        except Exception as e:
            log.debug(f"DB log skipped: {e}")

    def _db_log_event_raw(self, event: AMIEvent):
        """Log raw AMI event to DB (only if log_all_events=True)."""
        try:
            from .db_writer import write_raw_event
            write_raw_event(event)
        except Exception as e:
            log.debug(f"Raw event log skipped: {e}")
