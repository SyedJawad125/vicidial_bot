"""
bot/ami_client.py
=================
Persistent, thread-safe AMI (Asterisk Manager Interface) client.

VICIdial uses Asterisk internally. AMI is a TCP socket on port 5038.
This client:
  - Maintains a persistent connection (auto-reconnects on drop)
  - Reads events in a background thread
  - Dispatches events to registered handlers
  - Sends actions (originate, hangup, transfer, etc.)

Protocol:
  - Connect → read banner line
  - Login → Action: Login\r\n Username: x\r\n Secret: x\r\n\r\n
  - Server sends packets: key: value\r\n ... \r\n (blank line = end)
  - You send packets the same way
"""

import socket
import threading
import time
import logging
import queue
from typing import Callable, Dict, List, Optional

log = logging.getLogger("vicidial_bot.ami")


class AMIEvent(dict):
    """An AMI event packet — just a dict with helper properties."""

    @property
    def name(self) -> str:
        return self.get("Event", "")

    @property
    def action_id(self) -> str:
        return self.get("ActionID", "")

    def __repr__(self):
        return f"<AMIEvent {self.name} {dict(self)}>"


class AMIClient:
    """
    Persistent AMI connection with:
      - Auto-reconnect on disconnect
      - Event listener registration
      - Thread-safe action sending
      - Response matching by ActionID
    """

    RECONNECT_DELAY = 5   # seconds between reconnect attempts
    RECV_TIMEOUT    = 1   # socket read timeout (allows clean shutdown)

    def __init__(self, host: str, port: int, username: str, secret: str):
        self.host     = host
        self.port     = port
        self.username = username
        self.secret   = secret

        self._sock:   Optional[socket.socket] = None
        self._lock    = threading.Lock()          # guards _sock sends
        self._stop    = threading.Event()

        # Registered event handlers: {"EventName": [fn, fn, ...], "*": [...]}
        self._handlers: Dict[str, List[Callable]] = {"*": []}

        # Pending responses: {action_id: queue}
        self._pending: Dict[str, queue.Queue] = {}
        self._pending_lock = threading.Lock()

        self.connected = False
        self._reader_thread: Optional[threading.Thread] = None

    # ──────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────

    def on(self, event_name: str, handler: Callable):
        """
        Register a handler for an AMI event.

        event_name: exact name like "Hangup", "DialBegin", "AgentLogin"
                    or "*" for ALL events.

        handler(event: AMIEvent) is called in the reader thread.
        Keep handlers fast — offload heavy work to a thread pool.

        Example:
            @client.on("Hangup")
            def handle_hangup(event):
                print(f"Call ended: {event['Channel']}")
        """
        self._handlers.setdefault(event_name, []).append(handler)
        return handler   # allow use as decorator

    def send_action(self, action: dict, timeout: float = 5.0) -> Optional[AMIEvent]:
        """
        Send an AMI action and wait for its response.

        Returns the response packet or None on timeout/error.

        Example:
            resp = client.send_action({
                "Action": "Originate",
                "Channel": "SIP/trunk/09001234567",
                "Application": "Playback",
                "Data": "hello-world",
                "Async": "true",
            })
        """
        import uuid
        action_id = action.get("ActionID") or str(uuid.uuid4())[:8]
        action["ActionID"] = action_id

        resp_queue: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[action_id] = resp_queue

        try:
            self._send_raw(action)
            try:
                return resp_queue.get(timeout=timeout)
            except queue.Empty:
                log.warning(f"Action {action['Action']} timed out (ActionID={action_id})")
                return None
        finally:
            with self._pending_lock:
                self._pending.pop(action_id, None)

    def start(self):
        """Connect and start the background reader thread."""
        self._stop.clear()
        self._reader_thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ami-reader"
        )
        self._reader_thread.start()
        log.info("AMI client started")

    def stop(self):
        """Gracefully disconnect."""
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        if self._reader_thread:
            self._reader_thread.join(timeout=5)
        self.connected = False
        log.info("AMI client stopped")

    def wait_until_connected(self, timeout: float = 30.0) -> bool:
        """Block until connected or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.connected:
                return True
            time.sleep(0.2)
        return False

    # ──────────────────────────────────────────────────────
    #  Common actions (convenience wrappers)
    # ──────────────────────────────────────────────────────

    def originate(
        self,
        channel: str,
        context: str = "default",
        exten: str = "s",
        priority: str = "1",
        caller_id: str = "",
        variables: dict = None,
        application: str = None,
        data: str = None,
        timeout_ms: int = 30000,
        async_: bool = True,
    ) -> Optional[AMIEvent]:
        """Originate (dial out) a call."""
        action = {
            "Action":   "Originate",
            "Channel":  channel,
            "Timeout":  str(timeout_ms),
            "CallerID": caller_id,
            "Async":    "true" if async_ else "false",
        }
        if application:
            action["Application"] = application
            if data:
                action["Data"] = data
        else:
            action["Context"]  = context
            action["Exten"]    = exten
            action["Priority"] = priority

        if variables:
            action["Variable"] = ",".join(f"{k}={v}" for k, v in variables.items())

        return self.send_action(action)

    def hangup(self, channel: str, cause: int = 16) -> Optional[AMIEvent]:
        """Hang up a channel."""
        return self.send_action({
            "Action":  "Hangup",
            "Channel": channel,
            "Cause":   str(cause),
        })

    def redirect(self, channel: str, context: str, exten: str, priority: str = "1"):
        """Redirect (transfer) a channel to a new dialplan location."""
        return self.send_action({
            "Action":   "Redirect",
            "Channel":  channel,
            "Context":  context,
            "Exten":    exten,
            "Priority": priority,
        })

    def get_var(self, channel: str, variable: str) -> str:
        """Get a channel variable value."""
        resp = self.send_action({
            "Action":   "GetVar",
            "Channel":  channel,
            "Variable": variable,
        })
        return resp.get("Value", "") if resp else ""

    def set_var(self, channel: str, variable: str, value: str):
        """Set a channel variable."""
        return self.send_action({
            "Action":   "Setvar",
            "Channel":  channel,
            "Variable": variable,
            "Value":    value,
        })

    def core_show_channels(self) -> Optional[AMIEvent]:
        """Request list of active channels."""
        return self.send_action({"Action": "Status"})

    def ping(self) -> bool:
        """Check if AMI connection is alive."""
        resp = self.send_action({"Action": "Ping"}, timeout=3.0)
        return resp is not None and resp.get("Response") == "Success"

    # ──────────────────────────────────────────────────────
    #  Internal — connection loop
    # ──────────────────────────────────────────────────────

    def _run_loop(self):
        """Main loop: connect → read → reconnect on failure."""
        while not self._stop.is_set():
            try:
                self._connect()
                self._read_loop()
            except Exception as exc:
                log.error(f"AMI connection error: {exc}")
                self.connected = False
            finally:
                if self._sock:
                    try:
                        self._sock.close()
                    except Exception:
                        pass
                    self._sock = None

            if not self._stop.is_set():
                log.info(f"Reconnecting in {self.RECONNECT_DELAY}s…")
                time.sleep(self.RECONNECT_DELAY)

    def _connect(self):
        log.info(f"Connecting to AMI {self.host}:{self.port}")
        sock = socket.create_connection((self.host, self.port), timeout=10)
        sock.settimeout(self.RECV_TIMEOUT)
        self._sock = sock

        # Read banner
        banner = self._readline()
        log.debug(f"AMI banner: {banner}")

        # Login
        self._send_raw({
            "Action":   "Login",
            "Username": self.username,
            "Secret":   self.secret,
        })
        resp = self._read_packet()
        if resp.get("Response") != "Success":
            raise ConnectionError(f"AMI login failed: {resp}")

        self.connected = True
        log.info("AMI connected and authenticated ✓")
        self._dispatch(AMIEvent({"Event": "_Connected"}))

    def _read_loop(self):
        """Read packets forever until disconnected or stop signalled."""
        while not self._stop.is_set():
            try:
                packet = self._read_packet()
            except socket.timeout:
                continue   # normal — allows checking _stop
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                log.warning(f"AMI connection lost: {e}")
                self.connected = False
                self._dispatch(AMIEvent({"Event": "_Disconnected"}))
                break

            if not packet:
                continue

            event = AMIEvent(packet)

            # If it has an ActionID, it's a response to a pending action
            if "ActionID" in event:
                with self._pending_lock:
                    q = self._pending.get(event["ActionID"])
                if q:
                    try:
                        q.put_nowait(event)
                    except queue.Full:
                        pass
                    continue

            # Otherwise it's an unsolicited event
            if "Event" in event:
                self._dispatch(event)

    def _dispatch(self, event: AMIEvent):
        """Call all registered handlers for this event."""
        handlers = (
            self._handlers.get(event.name, []) +
            self._handlers.get("*", [])
        )
        for fn in handlers:
            try:
                fn(event)
            except Exception as exc:
                log.error(f"Handler error for {event.name}: {exc}", exc_info=True)

    # ──────────────────────────────────────────────────────
    #  Internal — I/O
    # ──────────────────────────────────────────────────────

    def _send_raw(self, packet: dict):
        data = "".join(f"{k}: {v}\r\n" for k, v in packet.items()) + "\r\n"
        with self._lock:
            if not self._sock:
                raise ConnectionError("Not connected")
            self._sock.sendall(data.encode())

    def _read_packet(self) -> dict:
        packet = {}
        while True:
            line = self._readline()
            if line == "":         # blank line = end of packet
                break
            if ":" in line:
                k, _, v = line.partition(":")
                packet[k.strip()] = v.strip()
        return packet

    def _readline(self) -> str:
        buf = b""
        while True:
            ch = self._sock.recv(1)
            if not ch:
                raise ConnectionResetError("Socket closed")
            buf += ch
            if buf.endswith(b"\r\n"):
                return buf[:-2].decode(errors="replace")
