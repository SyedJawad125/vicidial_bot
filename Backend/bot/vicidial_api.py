"""
bot/vicidial_api.py
===================
VICIdial HTTP API client.

VICIdial exposes a PHP-based API at:
  http://<server>/vicidial/non_agent_api.php
  http://<server>/vicidial/admin_api.php   (admin operations)

This client wraps both endpoints with clean Python methods.

Docs: https://vicidial.org/docs/NON-AGENT-API.txt
      https://vicidial.org/docs/ADMIN-API.txt
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

log = logging.getLogger("vicidial_bot.api")


class VICIdialAPIError(Exception):
    pass


class VICIdialAPI:
    """
    Wrapper for VICIdial's HTTP API (non_agent_api.php).

    All methods return a dict on success or raise VICIdialAPIError.
    """

    def __init__(
        self,
        server: str,
        user: str,
        password: str,
        source: str = "vicidial_bot",
        timeout: int = 15,
    ):
        """
        server   : "http://192.168.1.100" (no trailing slash)
        user     : VICIdial admin username
        password : VICIdial admin password
        source   : label for logs in VICIdial (any string)
        """
        self.server   = server.rstrip("/")
        self.user     = user
        self.password = password
        self.source   = source
        self.timeout  = timeout

        self._non_agent_url = f"{self.server}/vicidial/non_agent_api.php"
        self._admin_url     = f"{self.server}/vicidial/admin_api.php"

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

    # ──────────────────────────────────────────────────────
    #  Campaign Management
    # ──────────────────────────────────────────────────────

    def get_campaigns(self) -> List[dict]:
        """Return list of all campaigns."""
        resp = self._non_agent("campaign_list", {})
        return self._parse_list(resp)

    def get_campaign_status(self, campaign_id: str) -> dict:
        """Get status and stats for a specific campaign."""
        return self._non_agent("campaign_stats", {"campaign_id": campaign_id})

    def update_campaign_dial_status(self, campaign_id: str, status: str) -> dict:
        """
        Set campaign dial status.
        status: 'ACTIVE' | 'INACTIVE' | 'PAUSED'
        """
        return self._admin(
            "update_campaign",
            {"campaign_id": campaign_id, "campaign_allow_inbound": status},
        )

    # ──────────────────────────────────────────────────────
    #  Lead / Contact Management
    # ──────────────────────────────────────────────────────

    def add_lead(
        self,
        phone_number: str,
        campaign_id: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        address1: str = "",
        city: str = "",
        state: str = "",
        postal_code: str = "",
        comments: str = "",
        custom_fields: dict = None,
    ) -> dict:
        """
        Add a single lead to VICIdial.
        Returns {"status": "SUCCESS", "lead_id": "12345", ...}
        """
        params = {
            "phone_number":  phone_number,
            "campaign_id":   campaign_id,
            "first_name":    first_name,
            "last_name":     last_name,
            "email":         email,
            "address1":      address1,
            "city":          city,
            "state":         state,
            "postal_code":   postal_code,
            "comments":      comments,
            "duplicate_check": "DUPMT",   # skip if already in campaign
        }
        if custom_fields:
            params.update(custom_fields)
        return self._non_agent("add_lead", params)

    def update_lead_status(self, lead_id: str, status: str) -> dict:
        """
        Update a lead's disposition status.
        Common statuses: 'CALLBACK', 'SALE', 'NI', 'DNC', 'DNCL'
        """
        return self._non_agent("update_lead", {
            "lead_id": lead_id,
            "status":  status,
        })

    def search_leads(
        self,
        phone_number: str = "",
        campaign_id: str = "",
        status: str = "",
    ) -> List[dict]:
        """Search for leads by phone, campaign, or status."""
        params = {}
        if phone_number:
            params["phone_number"] = phone_number
        if campaign_id:
            params["campaign_id"]  = campaign_id
        if status:
            params["status"]       = status
        resp = self._non_agent("lead_search", params)
        return self._parse_list(resp)

    def get_lead_info(self, lead_id: str) -> dict:
        """Get full info for a single lead by ID."""
        return self._non_agent("lead_info", {"lead_id": lead_id})

    # ──────────────────────────────────────────────────────
    #  Call / Dial Operations
    # ──────────────────────────────────────────────────────

    def dial_lead(self, lead_id: str, agent_user: str, campaign_id: str) -> dict:
        """
        Push a lead to a logged-in agent to dial immediately.
        Agent must be logged into the specified campaign.
        """
        return self._non_agent("dial_lead", {
            "lead_id":     lead_id,
            "user":        agent_user,
            "campaign_id": campaign_id,
        })

    def get_active_calls(self) -> List[dict]:
        """Return list of currently active calls."""
        resp = self._non_agent("active_calls", {})
        return self._parse_list(resp)

    def park_call(self, agent_user: str, channel: str) -> dict:
        """Park an active call in a parking lot."""
        return self._non_agent("park_call", {
            "user":    agent_user,
            "channel": channel,
        })

    # ──────────────────────────────────────────────────────
    #  Agent Management
    # ──────────────────────────────────────────────────────

    def get_agents_in_campaign(self, campaign_id: str) -> List[dict]:
        """List agents currently logged into a campaign."""
        resp = self._non_agent("agents_in_campaign", {"campaign_id": campaign_id})
        return self._parse_list(resp)

    def get_all_agent_status(self) -> List[dict]:
        """Get status of all agents (logged in, paused, on call, etc.)."""
        resp = self._non_agent("agent_status", {})
        return self._parse_list(resp)

    def logout_agent(self, agent_user: str) -> dict:
        """Force-logout an agent from their session."""
        return self._non_agent("logout_agent", {"user": agent_user})

    # ──────────────────────────────────────────────────────
    #  Reports / Stats
    # ──────────────────────────────────────────────────────

    def get_campaign_report(
        self,
        campaign_id: str,
        query_date: str = "",  # YYYY-MM-DD, blank = today
    ) -> dict:
        """Get daily stats report for a campaign."""
        params = {"campaign_id": campaign_id}
        if query_date:
            params["query_date"] = query_date
        return self._non_agent("campaign_report", params)

    def get_inbound_stats(self, group_id: str = "") -> dict:
        """Inbound call group statistics."""
        params = {}
        if group_id:
            params["group_id"] = group_id
        return self._non_agent("inbound_stats", params)

    # ──────────────────────────────────────────────────────
    #  DNC (Do Not Call)
    # ──────────────────────────────────────────────────────

    def add_to_dnc(self, phone_number: str, list_id: str = "DNCL") -> dict:
        """Add a phone number to the DNC list."""
        return self._non_agent("add_dnc", {
            "phone_number": phone_number,
            "list_id":      list_id,
        })

    def check_dnc(self, phone_number: str) -> bool:
        """Check if a phone number is on the DNC list."""
        resp = self._non_agent("check_dnc", {"phone_number": phone_number})
        return resp.get("dnc_status", "NOT_FOUND") != "NOT_FOUND"

    # ──────────────────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────────────────

    def _non_agent(self, action: str, params: dict) -> dict:
        return self._call(self._non_agent_url, action, params)

    def _admin(self, action: str, params: dict) -> dict:
        return self._call(self._admin_url, action, params)

    def _call(self, url: str, action: str, params: dict) -> dict:
        payload = {
            "source":   self.source,
            "user":     self.user,
            "pass":     self.password,
            "function": action,
            **params,
        }
        log.debug(f"VICIdial API → {action} {params}")
        try:
            r = self._session.post(url, data=payload, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise VICIdialAPIError(f"HTTP error calling {action}: {e}") from e

        # VICIdial returns pipe-delimited text: "SUCCESS|key=val|key=val|..."
        raw = r.text.strip()
        log.debug(f"VICIdial API ← {raw[:200]}")
        return self._parse_response(raw, action)

    def _parse_response(self, raw: str, action: str) -> dict:
        """Parse VICIdial pipe-delimited response into a dict."""
        if not raw:
            return {"status": "EMPTY"}

        parts = raw.split("|")
        status = parts[0].strip()

        if status.startswith("ERROR"):
            raise VICIdialAPIError(f"{action} failed: {raw}")

        result = {"status": status, "_raw": raw}
        for part in parts[1:]:
            if "=" in part:
                k, _, v = part.partition("=")
                result[k.strip()] = v.strip()
            elif part.strip():
                result[f"_val_{len(result)}"] = part.strip()

        return result

    def _parse_list(self, resp: dict) -> List[dict]:
        """Parse multi-record responses (newline-separated records)."""
        raw = resp.get("_raw", "")
        results = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line in ("SUCCESS", "ERROR"):
                continue
            record = {}
            for part in line.split("|"):
                if "=" in part:
                    k, _, v = part.partition("=")
                    record[k.strip()] = v.strip()
            if record:
                results.append(record)
        return results
