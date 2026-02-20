"""Scoring engine based on the hackathon evaluation rubric.

Implements all 5 scoring categories:
    1. Scam Detection      – 20 pts
    2. Extracted Intelligence – 30 pts
    3. Conversation Quality  – 30 pts
    4. Engagement Quality    – 10 pts
    5. Response Structure    – 10 pts
"""

import re
from dataclasses import dataclass, field

from .scenarios import FakeData, Scenario


# ─────────────────────────────────────────────────────────────────────────────
# Result models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    # Category scores
    scam_detection: float = 0.0        # /20
    intelligence: float = 0.0          # /30
    conversation_quality: float = 0.0  # /30
    engagement_quality: float = 0.0    # /10
    response_structure: float = 0.0    # /10

    # Detail fields
    scam_detected: bool = False
    extracted_items: dict = field(default_factory=dict)
    missed_items: dict = field(default_factory=dict)
    turn_count: int = 0
    questions_asked: int = 0
    relevant_questions: int = 0
    red_flags_found: int = 0
    elicitation_attempts: int = 0
    engagement_duration_seconds: int = 0
    total_messages: int = 0
    structure_issues: list[str] = field(default_factory=list)
    intelligence_detail: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (
            self.scam_detection
            + self.intelligence
            + self.conversation_quality
            + self.engagement_quality
            + self.response_structure
        )


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation helpers
# ─────────────────────────────────────────────────────────────────────────────

_INVESTIGATIVE_KEYWORDS = [
    "employee id", "id number", "worker id", "staff id",
    "company name", "organisation", "department",
    "address", "location", "office",
    "website", "official site", "portal",
    "license", "registered",
    "your name", "who are you", "identity",
    "callback number", "phone number", "contact",
    "supervisor", "manager",
    "complaint", "report", "escalate",
    "rbi", "sebi", "trai", "ncib",
]

_RED_FLAG_KEYWORDS = [
    "urgent", "urgently", "immediately", "hurry", "deadline",
    "otp", "one time password", "passcode",
    "suspicious", "compromised", "hacked", "blocked",
    "fee", "charge", "pay", "payment", "transfer",
    "prize", "reward", "cashback", "lottery", "won", "winner",
    "kyc", "verify", "verification",
    "phishing", "fake", "fraud", "scam",
    "avoid", "prevent", "protect",
    "claim now", "limited time", "expires",
    "bank account", "upi", "account number",
    "unverified", "suspicious link",
]

_ELICITATION_PATTERNS = [
    r"\bwhat.{0,30}(name|number|account|upi|phone|email|address|id|link|website)\b",
    r"\b(can you|could you|please|kindly).{0,20}(share|send|provide|give|tell).{0,20}"
    r"(number|account|upi|phone|email|address|id|link)\b",
    r"\b(share|send|provide).{0,30}(details|information|info|data)\b",
    r"\bwhere.{0,30}(send|transfer|pay|click)\b",
    r"\b(how|what).{0,20}(transfer|pay|send)\b",
    r"\b(verify|confirm).{0,30}(identity|account|details)\b",
]

_QUESTION_PATTERN = re.compile(r"\?")


def _normalize(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    norm = _normalize(text)
    return [kw for kw in keywords if kw in norm]


def _count_questions(texts: list[str]) -> int:
    return sum(bool(_QUESTION_PATTERN.search(t)) for t in texts)


def _count_relevant_questions(texts: list[str]) -> int:
    count = 0
    for text in texts:
        norm = _normalize(text)
        if "?" in norm and _contains_any(text, _INVESTIGATIVE_KEYWORDS):
            count += 1
    return count


def _count_elicitation(texts: list[str]) -> int:
    count = 0
    for text in texts:
        norm = _normalize(text)
        for pattern in _ELICITATION_PATTERNS:
            if re.search(pattern, norm):
                count += 1
                break  # Count each message once
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Intelligence extraction matching
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_phone(p: str) -> str:
    return re.sub(r"[\s\-\+\(\)]", "", p.strip())


def _normalize_url(u: str) -> str:
    return u.lower().strip().rstrip("/")


def _match_items(
    expected: list[str],
    extracted: list[str],
    normalizer=lambda x: x.lower().strip(),
) -> tuple[list[str], list[str]]:
    """Returns (matched, missed)."""
    matched, missed = [], []
    extracted_norm = [normalizer(e) for e in extracted]
    for item in expected:
        norm = normalizer(item)
        if any(norm in e or e in norm for e in extracted_norm):
            matched.append(item)
        else:
            missed.append(item)
    return matched, missed


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluator
# ─────────────────────────────────────────────────────────────────────────────

class Evaluator:
    """Scores a completed honeypot session against a test scenario."""

    def score(
        self,
        scenario: Scenario,
        conversation_history: list[dict],
        final_output: dict,
        elapsed_seconds: float,
    ) -> ScoreBreakdown:
        """Evaluate a completed conversation.

        Args:
            scenario: The test scenario that was run.
            conversation_history: Full list of {sender, text, timestamp} dicts.
            final_output: The finalOutput submitted by the honeypot.
            elapsed_seconds: Total wall-clock time of the session.

        Returns:
            ScoreBreakdown with individual category scores.
        """
        result = ScoreBreakdown()

        # Separate agent (honeypot) replies from scammer messages
        agent_msgs = [
            m["text"] for m in conversation_history if m.get("sender") == "user"
        ]
        scammer_msgs = [
            m["text"] for m in conversation_history if m.get("sender") == "scammer"
        ]

        result.turn_count = len(agent_msgs)
        result.engagement_duration_seconds = int(elapsed_seconds)
        result.total_messages = len(conversation_history)

        # 1. Scam Detection (20 pts)
        result.scam_detected = bool(final_output.get("scamDetected", False))
        result.scam_detection = 20.0 if result.scam_detected else 0.0

        # 2. Extracted Intelligence (30 pts)
        result.intelligence, result.extracted_items, result.missed_items, result.intelligence_detail = (
            self._score_intelligence(scenario.fake_data, final_output)
        )

        # 3. Conversation Quality (30 pts)
        result.questions_asked = _count_questions(agent_msgs)
        result.relevant_questions = _count_relevant_questions(agent_msgs)
        result.red_flags_found = len(
            set(_contains_any(" ".join(agent_msgs), _RED_FLAG_KEYWORDS))
        )
        result.elicitation_attempts = _count_elicitation(agent_msgs)
        result.conversation_quality = self._score_conv_quality(result)

        # 4. Engagement Quality (10 pts)
        result.engagement_quality = self._score_engagement(
            elapsed_seconds, len(conversation_history)
        )

        # 5. Response Structure (10 pts)
        result.response_structure, result.structure_issues = self._score_structure(
            final_output
        )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Category scorers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _score_intelligence(
        fake_data: FakeData,
        final_output: dict,
    ) -> tuple[float, dict, dict, list[str]]:
        extracted_intel = final_output.get("extractedIntelligence", {})
        total_fields = fake_data.total_fields()
        if total_fields == 0:
            return 30.0, {}, {}, ["No fake data in scenario – full marks awarded"]

        points_per_item = 30.0 / total_fields
        total_score = 0.0
        extracted_summary: dict[str, list[str]] = {}
        missed_summary: dict[str, list[str]] = {}
        details: list[str] = []

        checks = [
            ("phoneNumbers",  fake_data.phone_numbers,  _normalize_phone),
            ("bankAccounts",  fake_data.bank_accounts,  lambda x: re.sub(r"\s", "", x)),
            ("upiIds",        fake_data.upi_ids,        lambda x: x.lower().strip()),
            ("phishingLinks", fake_data.phishing_links, _normalize_url),
            ("emailAddresses",fake_data.email_addresses,lambda x: x.lower().strip()),
            ("caseIds",       fake_data.case_ids,       lambda x: x.lower().strip()),
            ("policyNumbers", fake_data.policy_numbers, lambda x: x.lower().strip()),
            ("orderNumbers",  fake_data.order_numbers,  lambda x: x.lower().strip()),
        ]

        for field_name, expected, normalizer in checks:
            if not expected:
                continue
            submitted = extracted_intel.get(field_name, [])
            matched, missed = _match_items(expected, submitted, normalizer)
            pts = points_per_item * len(matched)
            total_score += pts
            if matched:
                extracted_summary[field_name] = matched
                details.append(f"✅ {field_name}: {matched} (+{pts:.1f} pts)")
            if missed:
                missed_summary[field_name] = missed
                details.append(f"❌ {field_name}: missed {missed}")

        return min(total_score, 30.0), extracted_summary, missed_summary, details

    @staticmethod
    def _score_conv_quality(result: ScoreBreakdown) -> float:
        score = 0.0

        # Turn count (8 pts)
        if result.turn_count >= 8:
            score += 8.0
        elif result.turn_count >= 6:
            score += 6.0
        elif result.turn_count >= 4:
            score += 3.0

        # Questions asked (4 pts)
        if result.questions_asked >= 5:
            score += 4.0
        elif result.questions_asked >= 3:
            score += 2.0
        elif result.questions_asked >= 1:
            score += 1.0

        # Relevant questions (3 pts)
        if result.relevant_questions >= 3:
            score += 3.0
        elif result.relevant_questions >= 2:
            score += 2.0
        elif result.relevant_questions >= 1:
            score += 1.0

        # Red flags identified (8 pts)
        if result.red_flags_found >= 5:
            score += 8.0
        elif result.red_flags_found >= 3:
            score += 5.0
        elif result.red_flags_found >= 1:
            score += 2.0

        # Information elicitation (7 pts, 1.5 per attempt max 7)
        score += min(result.elicitation_attempts * 1.5, 7.0)

        return min(score, 30.0)

    @staticmethod
    def _score_engagement(elapsed_seconds: float, total_messages: int) -> float:
        score = 0.0

        # Duration
        if elapsed_seconds > 0:
            score += 1.0
        if elapsed_seconds > 60:
            score += 2.0
        if elapsed_seconds > 180:
            score += 1.0

        # Messages
        if total_messages > 0:
            score += 2.0
        if total_messages >= 5:
            score += 3.0
        if total_messages >= 10:
            score += 1.0

        return min(score, 10.0)

    @staticmethod
    def _score_structure(final_output: dict) -> tuple[float, list[str]]:
        score = 0.0
        issues: list[str] = []

        required_fields = {
            "sessionId": 2.0,
            "scamDetected": 2.0,
            "extractedIntelligence": 2.0,
        }
        optional_fields = {
            ("totalMessagesExchanged", "engagementDurationSeconds"): 1.0,
            ("agentNotes",): 1.0,
            ("scamType",): 1.0,
            ("confidenceLevel",): 1.0,
        }

        for field_name, pts in required_fields.items():
            if field_name in final_output:
                score += pts
            else:
                score -= 1.0  # Penalty for missing required field
                issues.append(f"MISSING required field: '{field_name}' (-1 pt penalty)")

        for fields, pts in optional_fields.items():
            if any(f in final_output for f in fields):
                score += pts

        return max(score, 0.0), issues


# ─────────────────────────────────────────────────────────────────────────────
# Suite scorer
# ─────────────────────────────────────────────────────────────────────────────

def calculate_final_score(
    scenario_scores: list[tuple[Scenario, ScoreBreakdown]],
    code_quality_score: float = 0.0,
) -> dict:
    """Calculate the weighted final score across all scenarios.

    Args:
        scenario_scores: List of (scenario, score_breakdown) tuples.
        code_quality_score: Optional code quality score out of 10.

    Returns:
        Dict with final_score, scenario_portion, weighted_breakdown.
    """
    weighted_total = 0.0
    breakdown = []

    for scenario, score in scenario_scores:
        contribution = score.total * (scenario.weight / 100.0)
        weighted_total += contribution
        breakdown.append({
            "scenario": scenario.name,
            "scam_type": scenario.scam_type,
            "weight": scenario.weight,
            "raw_score": round(score.total, 2),
            "contribution": round(contribution, 2),
        })

    scenario_portion = round(weighted_total * 0.9, 2)
    final_score = round(scenario_portion + code_quality_score, 2)

    return {
        "final_score": final_score,
        "scenario_portion": scenario_portion,
        "weighted_scenario_score": round(weighted_total, 2),
        "code_quality_score": code_quality_score,
        "breakdown": breakdown,
    }
