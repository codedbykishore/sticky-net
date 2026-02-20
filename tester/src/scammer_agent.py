"""Gemini-powered automated scammer agent.

Simulates the evaluation system's AI that generates realistic scammer
follow-up messages based on the honeypot's responses.
"""

import logging
import os
import time

import google.genai as genai
from google.genai import types

from .scenarios import Scenario

logger = logging.getLogger(__name__)

_SCAMMER_SYSTEM_PROMPT = """
You are simulating a convincing scammer for a honeypot security testing system.
Your role is to generate REALISTIC scammer follow-up messages to test an AI honeypot.

RULES:
1. Stay in character as the scammer described in Persona Context
2. Respond naturally to what the "victim" (honeypot) says
3. Gradually reveal the fake data items when it feels natural or when asked
4. Use typical scammer tactics: urgency, authority, fear, excitement
5. Keep messages short and authentic (like real SMS/WhatsApp scam messages)
6. If the victim asks for your phone number / email / ID, provide it from the fake data
7. If asked for account/UPI details to "transfer money", provide them
8. Do NOT break character. Do NOT admit you are a scammer or AI
9. Maximum 3 sentences per response (scammers are brief and punchy)
10. If the victim resists, increase pressure or try a different angle
11. If you have already revealed all fake data, wrap up the conversation naturally

OUTPUT: Only the scammer's message text. No labels, no explanations.
""".strip()


class ScammerAgent:
    """Uses Gemini to generate scammer follow-up messages."""

    def __init__(
        self,
        project: str,
        location: str = "global",
        model: str = "gemini-2.5-flash",
        use_vertexai: bool = True,
    ) -> None:
        self.project = project
        self.location = location
        self.model = model
        self.use_vertexai = use_vertexai
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if self.use_vertexai:
                self._client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location,
                )
            else:
                api_key = os.environ.get("GEMINI_API_KEY", "")
                self._client = genai.Client(api_key=api_key)
        return self._client

    def generate_followup(
        self,
        scenario: Scenario,
        conversation_history: list[dict],
        honeypot_reply: str,
        turn_number: int,
    ) -> str:
        """Generate the next scammer message.

        Args:
            scenario: The active test scenario.
            conversation_history: Full conversation so far.
            honeypot_reply: The latest response from the honeypot.
            turn_number: Current turn number (1-indexed).

        Returns:
            The scammer's follow-up message text.
        """
        client = self._get_client()

        # Build a concise conversation summary for context
        history_text = self._format_history(conversation_history)

        # Combine system prompt with persona context
        system_instruction = (
            f"{_SCAMMER_SYSTEM_PROMPT}\n\n"
            f"PERSONA CONTEXT:\n{scenario.persona_context}\n\n"
            f"FAKE DATA AVAILABLE TO REVEAL:\n{self._format_fake_data(scenario)}\n\n"
            f"CURRENT TURN: {turn_number} of {scenario.max_turns}\n"
            f"(If this is the last 2 turns, try harder to reveal the remaining fake data)"
        )

        user_prompt = (
            f"CONVERSATION SO FAR:\n{history_text}\n\n"
            f"VICTIM'S LATEST MESSAGE: {honeypot_reply}\n\n"
            f"Generate your next scammer message:"
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.85,
                    max_output_tokens=200,
                ),
            )
            text = response.text.strip() if response.text else ""
            if not text:
                return self._fallback_message(turn_number, scenario.scam_type)
            return text
        except Exception as exc:
            logger.warning("Gemini scammer generation failed: %s – using fallback", exc)
            return self._fallback_message(turn_number, scenario.scam_type)

    @staticmethod
    def _format_history(history: list[dict]) -> str:
        if not history:
            return "(No previous messages)"
        lines = []
        for msg in history[-10:]:  # Last 10 messages
            sender = msg.get("sender", "unknown").upper()
            text = msg.get("text", "")
            lines.append(f"{sender}: {text}")
        return "\n".join(lines)

    @staticmethod
    def _format_fake_data(scenario: Scenario) -> str:
        fd = scenario.fake_data
        lines = []
        if fd.phone_numbers:
            lines.append(f"  Phone numbers: {', '.join(fd.phone_numbers)}")
        if fd.bank_accounts:
            lines.append(f"  Bank accounts: {', '.join(fd.bank_accounts)}")
        if fd.upi_ids:
            lines.append(f"  UPI IDs: {', '.join(fd.upi_ids)}")
        if fd.phishing_links:
            lines.append(f"  Phishing links: {', '.join(fd.phishing_links)}")
        if fd.email_addresses:
            lines.append(f"  Emails: {', '.join(fd.email_addresses)}")
        if fd.case_ids:
            lines.append(f"  Case IDs: {', '.join(fd.case_ids)}")
        if fd.policy_numbers:
            lines.append(f"  Policy numbers: {', '.join(fd.policy_numbers)}")
        if fd.order_numbers:
            lines.append(f"  Order numbers: {', '.join(fd.order_numbers)}")
        return "\n".join(lines) if lines else "  (none)"

    @staticmethod
    def _fallback_message(turn: int, scam_type: str) -> str:
        fallbacks = {
            "bank_fraud": [
                "Please act quickly! Your account will be blocked in 1 hour. Share the OTP now.",
                "Sir/Madam, this is urgent. Please cooperate or face account suspension.",
                "Call me back on the number provided. Time is running out.",
            ],
            "upi_fraud": [
                "Just send Re.1 for verification and get Rs.15,000 instantly!",
                "Your cashback offer expires soon. Complete verification now.",
                "Many people have already claimed. Don't miss this opportunity!",
            ],
            "phishing": [
                "Click the link to claim your reward before it expires!",
                "Your Amazon package is waiting. Verify your address now.",
                "Limited time offer! Click now to receive your gift.",
            ],
        }
        msgs = fallbacks.get(scam_type, ["Please respond urgently. This is important!"])
        return msgs[min(turn - 1, len(msgs) - 1)]
