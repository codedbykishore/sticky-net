"""Orchestrates the multi-turn scammer ↔ honeypot conversation.

Sends requests to the target honeypot endpoint, drives the conversation
using the AI scammer agent, and collects the final output.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .scammer_agent import ScammerAgent
from .scenarios import Scenario

logger = logging.getLogger(__name__)

# How long to wait after last turn before requesting final output
FINAL_OUTPUT_WAIT_SECONDS = 12


class ConversationRunner:
    """Drives a multi-turn honeypot evaluation session."""

    def __init__(
        self,
        target_url: str,
        api_key: str | None,
        scammer_agent: ScammerAgent,
        request_timeout: float = 30.0,
    ) -> None:
        self.target_url = target_url.rstrip("/")
        self.api_key = api_key
        self.scammer_agent = scammer_agent
        self.request_timeout = request_timeout

    async def run(
        self,
        scenario: Scenario,
        session_id: str | None = None,
        on_turn: Any | None = None,
    ) -> tuple[list[dict], dict, float]:
        """Run a full scenario conversation.

        Args:
            scenario: The scam scenario to simulate.
            session_id: Optional session ID (generated if not provided).
            on_turn: Optional async callback(turn_num, msg) for real-time updates.

        Returns:
            Tuple of (conversation_history, final_output_dict, elapsed_seconds)
        """
        session_id = session_id or str(uuid.uuid4())
        conversation_history: list[dict] = []
        start_time = time.monotonic()

        logger.info(
            "Starting scenario '%s' – session %s (max %d turns)",
            scenario.name,
            session_id,
            scenario.max_turns,
        )

        # ── Turn 1: Send initial scam message ────────────────────────────────
        current_message = scenario.initial_message
        final_output: dict = {}

        for turn in range(1, scenario.max_turns + 1):
            ts = self._now_ts()

            # Add scammer message to history
            scammer_entry = {
                "sender": "scammer",
                "text": current_message,
                "timestamp": ts,
            }
            conversation_history.append(scammer_entry)

            if on_turn:
                await on_turn(turn, "scammer", current_message)

            logger.debug("Turn %d  SCAMMER: %s", turn, current_message[:80])

            # Send to honeypot
            payload = {
                "sessionId": session_id,
                "message": {
                    "sender": "scammer",
                    "text": current_message,
                    "timestamp": ts,
                },
                "conversationHistory": conversation_history[:-1],  # Exclude current
                "metadata": scenario.metadata,
            }

            try:
                reply, raw_response = await self._call_honeypot(payload)
            except Exception as exc:
                logger.error("Honeypot call failed on turn %d: %s", turn, exc)
                reply = "[ERROR: No response from honeypot]"
                raw_response = {"error": str(exc)}

            # Add agent reply to history
            agent_ts = self._now_ts()
            agent_entry = {
                "sender": "user",
                "text": reply,
                "timestamp": agent_ts,
            }
            conversation_history.append(agent_entry)

            if on_turn:
                await on_turn(turn, "honeypot", reply)

            logger.debug("Turn %d  HONEYPOT: %s", turn, reply[:80])

            # Stop if this is the last turn
            if turn >= scenario.max_turns:
                break

            # Generate next scammer message via Gemini
            try:
                current_message = self.scammer_agent.generate_followup(
                    scenario=scenario,
                    conversation_history=conversation_history,
                    honeypot_reply=reply,
                    turn_number=turn + 1,
                )
            except Exception as exc:
                logger.error("Scammer generation failed: %s", exc)
                break

        # ── Collect final output ──────────────────────────────────────────────
        logger.info(
            "Conversation ended after %d turns. Waiting %ds for finalOutput…",
            len([m for m in conversation_history if m["sender"] == "scammer"]),
            FINAL_OUTPUT_WAIT_SECONDS,
        )
        await asyncio.sleep(FINAL_OUTPUT_WAIT_SECONDS)

        # Try to get finalOutput from the honeypot (some implementations POST it)
        # We also accept it from the last API response
        final_output = await self._request_final_output(
            session_id=session_id,
            conversation_history=conversation_history,
            metadata=scenario.metadata,
            elapsed=time.monotonic() - start_time,
        )

        elapsed = time.monotonic() - start_time
        logger.info(
            "Session %s complete in %.1fs – finalOutput: %s",
            session_id,
            elapsed,
            bool(final_output),
        )
        return conversation_history, final_output, elapsed

    # ─────────────────────────────────────────────────────────────────────────
    # HTTP helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _call_honeypot(self, payload: dict) -> tuple[str, dict]:
        """POST payload to the honeypot and return (reply_text, raw_response)."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(self.target_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Accept reply / message / text fields per evaluation spec
        reply = (
            data.get("reply")
            or data.get("message")
            or data.get("text")
            or "[no reply field in response]"
        )
        return str(reply), data

    async def _request_final_output(
        self,
        session_id: str,
        conversation_history: list[dict],
        metadata: dict,
        elapsed: float,
    ) -> dict:
        """Send a final-turn request to collect the honeypot's finalOutput.

        The evaluation system waits 10s then scores whatever the honeypot
        has submitted.  We mimic this by sending one more "end" request.
        """
        # Build a synthetic end message
        end_payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": "[CONVERSATION_END]",
                "timestamp": self._now_ts(),
            },
            "conversationHistory": conversation_history,
            "metadata": {**metadata, "finalTurn": "true"},
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                resp = await client.post(
                    self.target_url, json=end_payload, headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # If the response itself looks like finalOutput, use it directly
                    if "scamDetected" in data or "extractedIntelligence" in data:
                        return data
                    # Otherwise wrap with session defaults
                    return self._build_default_final(
                        session_id, data, conversation_history, elapsed
                    )
        except Exception as exc:
            logger.warning("Final output request failed: %s", exc)

        # Return a minimal structure so scoring can still run
        return self._build_default_final(
            session_id, {}, conversation_history, elapsed
        )

    @staticmethod
    def _build_default_final(
        session_id: str,
        base: dict,
        history: list[dict],
        elapsed: float,
    ) -> dict:
        """Build a default finalOutput from whatever we have."""
        agent_msgs = [m for m in history if m.get("sender") == "user"]
        total = len(history)
        return {
            "sessionId": session_id,
            "scamDetected": base.get("scamDetected", False),
            "totalMessagesExchanged": base.get("totalMessagesExchanged", total),
            "engagementDurationSeconds": base.get(
                "engagementDurationSeconds", int(elapsed)
            ),
            "extractedIntelligence": base.get("extractedIntelligence", {}),
            "agentNotes": base.get("agentNotes", ""),
            "scamType": base.get("scamType", ""),
            "confidenceLevel": base.get("confidenceLevel", 0.0),
            "reply": base.get("reply", base.get("message", base.get("text", ""))),
        }

    @staticmethod
    def _now_ts() -> str:
        return datetime.now(timezone.utc).isoformat()
