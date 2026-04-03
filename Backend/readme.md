# 📞 VICIdial Bot

Connect to VICIdial in real-time via **AMI** (live events) + **HTTP API** (campaign control).
Built with Python + Django REST Framework. No LLM. No external AI services.

---

## What the Bot Does

```
VICIdial Server (Asterisk)
         │
         │  TCP port 5038 (AMI)
         ▼
  ┌─────────────────┐
  │   VICIdial Bot  │  ← This project
  │                 │
  │  AMI Client     │  Listens to ALL events in real-time:
  │  (persistent    │  • Newchannel   → new call started
  │   TCP socket)   │  • Hangup       → call ended
  │                 │  • AgentLogin   → agent came online
  │                 │  • AgentLogoff  → agent went offline
  │                 │  • DialBegin    → dialing customer
  │                 │  • VarSet       → disposition set
  │                 │  • + 50 more...
  │                 │
  │  HTTP API       │  Controls VICIdial:
  │  Client         │  • Add leads
  │                 │  • Update dispositions
  │                 │  • List campaigns / agents
  │                 │  • Pause / activate campaigns
  │                 │  • Add to DNC list
  │                 │
  │  Django DRF     │  Your apps talk to the bot via REST:
  │  API            │  • GET  /api/status/        → live status
  │                 │  • POST /api/commands/originate/ → dial a number
  │                 │  • GET  /api/calls/          → call history
  │                 │  • GET  /api/events/         → event log
  └─────────────────┘
```

---

## Quick Start

### Option A — Standalone (Test AMI connection, no Django needed)

```bash
pip install requests python-decouple
cp .env.example .env
# Edit .env: set VICIDIAL_AMI_HOST, VICIDIAL_AMI_USER, VICIDIAL_AMI_SECRET

mkdir logs
python run_standalone.py
```

You will see live AMI events printed in real-time:
```
  ✓ AMI connected to VICIdial!
  ✓ Ping OK
  📞 NEW CALL: channel=SIP/trunk-00000001 cid=09001234567
  👤 AGENT LOGIN: admin
  🔔 DIALING: SIP/trunk-0000001 → 09009876543
  ✅ DIAL END: status=ANSWER
  📵 HANGUP: channel=SIP/trunk-0000001 cause=Normal Clearing
```

### Option B — Full Django Setup

```bash
# Install
pip install -r requirements.txt

# Database
sudo -u postgres psql -c "CREATE DATABASE vicidial_bot_db;"
sudo -u postgres psql -c "CREATE USER botuser WITH PASSWORD 'pass';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE vicidial_bot_db TO botuser;"

# Configure
cp .env.example .env
nano .env   # fill in your VICIdial server details

# Setup Django
mkdir -p logs media
python manage.py makemigrations vicidial_bot
python manage.py migrate
python manage.py createsuperuser

# Run Django API server (Terminal 1)
python manage.py runserver 0.0.0.0:8000

# Run the Bot (Terminal 2)
python manage.py run_bot
```

---

## Configure VICIdial AMI

On your VICIdial server, edit `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = amp111
permit = 0.0.0.0/0.0.0.0        ; or restrict to bot server IP
read = all
write = all
```

Reload:
```bash
asterisk -rx "manager reload"
```

Test from command line:
```bash
telnet your-vicidial-ip 5038
# You should see: Asterisk Call Manager/x.x
```

---

## API Reference

Get token first:
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
     -d "username=admin&password=yourpassword"
# {"token": "abc123..."}
```

Use as header: `Authorization: Token abc123...`

### Bot Status
```bash
GET /api/status/
```
```json
{
  "running": true,
  "connected": true,
  "active_calls": 3,
  "event_count": 1547,
  "last_event": "VarSet",
  "calls": [
    {"unique_id": "...", "channel": "SIP/...", "state": "ANSWERED", "duration_sec": 45}
  ]
}
```

### Dial a Number
```bash
POST /api/commands/originate/
{"phone": "09001234567", "campaign_id": "CAMP1", "caller_id": "Company <1000>"}
```

### Hang Up a Call
```bash
POST /api/commands/hangup/
{"channel": "SIP/trunk-0000001"}
```

### Transfer a Call
```bash
POST /api/commands/transfer/
{"channel": "SIP/trunk-0000001", "destination": "1001", "context": "default"}
```

### Send DTMF
```bash
POST /api/commands/dtmf/
{"channel": "SIP/trunk-0000001", "digit": "5"}
```

### Add to DNC
```bash
POST /api/commands/dnc/
{"phone": "09001234567"}
```

### Ping AMI
```bash
GET /api/commands/ping/
# {"ami_alive": true, "connected": true}
```

### List VICIdial Campaigns
```bash
GET /api/vicidial/campaigns/
```

### List Agent Statuses
```bash
GET /api/vicidial/agents/
```

### Add a Lead to VICIdial
```bash
POST /api/vicidial/add_lead/
{"phone": "09001234567", "campaign_id": "CAMP1", "first_name": "Ahmed", "last_name": "Khan"}
```

### Update Lead Disposition
```bash
POST /api/vicidial/update_lead/
{"lead_id": "12345", "status": "SALE"}
# status options: SALE | NI | DNC | CALLBACK | NA | B
```

### Pause / Activate Campaign
```bash
POST /api/vicidial/campaign/CAMP1/pause/
POST /api/vicidial/campaign/CAMP1/activate/
```

### View Event Log
```bash
GET /api/events/?type=CALL_ENDED&limit=50
GET /api/events/?type=AGENT
```

### View Call History
```bash
GET /api/calls/?campaign_id=CAMP1&limit=100
GET /api/calls/?agent_user=admin
```

---

## Adding Your Own Event Handlers

In `bot/vici_bot.py`, inside `_register_handlers()`:

```python
@ami.on("AgentLogin")
def on_agent_login(event):
    agent = event.get("Agent", "")
    # Send a Slack notification, update a dashboard, etc.
    send_slack_message(f"Agent {agent} logged in!")

@ami.on("Hangup")
def on_hangup(event):
    cause = event.get("Cause-txt", "")
    uid   = event.get("Uniqueid", "")
    # Your custom logic here
```

All 50+ AMI events are available. Common ones:

| Event | When it fires |
|-------|---------------|
| `Newchannel` | New call channel opened |
| `DialBegin` | Dialing started |
| `DialEnd` | Dial attempt finished (ANSWER/BUSY/NOANSWER) |
| `Hangup` | Channel hung up |
| `AgentLogin` | Agent logged into VICIdial |
| `AgentLogoff` | Agent logged out |
| `AgentCalled` | Agent being connected to customer |
| `AgentComplete` | Agent-customer call finished |
| `VarSet` | Channel variable set (e.g. VICIDIAL_DISPOSITION) |
| `Parked` | Call parked |
| `QueueMemberAdded` | Agent added to queue |

---

## Project Files

```
vicidial_bot/
├── bot/
│   ├── ami_client.py      ← Persistent AMI TCP socket, auto-reconnect, event dispatch
│   ├── vicidial_api.py    ← VICIdial HTTP API client (leads, campaigns, agents)
│   ├── vici_bot.py        ← Main bot: event handlers + command queue
│   └── db_writer.py       ← Thread-safe Django ORM writes
├── api/
│   ├── views.py           ← DRF API views (status, commands, VICIdial proxy)
│   └── urls.py
├── management/commands/
│   └── run_bot.py         ← `python manage.py run_bot`
├── models.py              ← BotEventLog, CallLog, BotCommand
├── admin.py
├── run_standalone.py      ← Test without Django
└── requirements.txt       ← Only 6 packages, no AI libs
```
