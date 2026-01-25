"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class SenderType(str, Enum):
    """Message sender type."""

    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Communication channel type."""

    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class Message(BaseModel):
    """Incoming message model."""

    sender: SenderType
    text: Annotated[str, Field(min_length=1, max_length=5000)]
    timestamp: datetime


class ConversationMessage(BaseModel):
    """Message in conversation history."""

    sender: SenderType
    text: str
    timestamp: datetime


class Metadata(BaseModel):
    """Request metadata."""

    channel: ChannelType = ChannelType.SMS
    language: str = "English"
    locale: str = "IN"


class AnalyzeRequest(BaseModel):
    """Main API request model."""

    message: Message
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": {
                        "sender": "scammer",
                        "text": "Your bank account will be blocked today. Verify immediately.",
                        "timestamp": "2026-01-21T10:15:30Z",
                    },
                    "conversationHistory": [],
                    "metadata": {
                        "channel": "SMS",
                        "language": "English",
                        "locale": "IN",
                    },
                }
            ]
        }
    }


class EngagementMetrics(BaseModel):
    """Engagement metrics model."""

    engagementDurationSeconds: int = 0
    totalMessagesExchanged: int = 0


class OtherIntelItem(BaseModel):
    """Ad-hoc intelligence item for data that doesn't fit standard fields."""

    label: str  # e.g., "Crypto Wallet", "TeamViewer ID", "WhatsApp Group Link"
    value: str  # The actual extracted value


class ExtractedIntelligence(BaseModel):
    """Extracted intelligence model."""

    bankAccounts: list[str] = Field(default_factory=list)
    upiIds: list[str] = Field(default_factory=list)
    phoneNumbers: list[str] = Field(default_factory=list)
    phishingLinks: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    beneficiaryNames: list[str] = Field(default_factory=list)
    bankNames: list[str] = Field(default_factory=list)
    ifscCodes: list[str] = Field(default_factory=list)
    whatsappNumbers: list[str] = Field(default_factory=list)
    other_critical_info: list[OtherIntelItem] = Field(default_factory=list)


class AgentJsonResponse(BaseModel):
    """Structured response from the honeypot agent (One-Pass JSON)."""

    reply_text: str  # The message to send back to the scammer
    emotional_tone: str  # The emotion expressed (e.g., "panicked", "confused")
    extracted_intelligence: ExtractedIntelligence  # Intelligence found in this turn
    scam_analysis: dict = Field(default_factory=dict)  # Optional analysis metadata


class StatusType(str, Enum):
    """Response status type."""

    SUCCESS = "success"
    ERROR = "error"


class ScamType(str, Enum):
    """Types of scams that can be detected."""

    JOB_OFFER = "job_offer"
    BANKING_FRAUD = "banking_fraud"
    LOTTERY_REWARD = "lottery_reward"
    IMPERSONATION = "impersonation"
    OTHERS = "others"


class AnalyzeResponse(BaseModel):
    """Main API response model."""

    status: StatusType = StatusType.SUCCESS
    scamDetected: bool
    scamType: ScamType | None = None  # Type of scam detected
    confidence: float = 0.0  # Detection confidence (0.0 to 1.0)
    engagementMetrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    extractedIntelligence: ExtractedIntelligence = Field(default_factory=ExtractedIntelligence)
    agentNotes: str = ""
    agentResponse: str | None = None  # The response to send back to the scammer

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "scamDetected": True,
                    "scamType": "banking_fraud",
                    "confidence": 0.92,
                    "engagementMetrics": {
                        "engagementDurationSeconds": 420,
                        "totalMessagesExchanged": 18,
                    },
                    "extractedIntelligence": {
                        "bankAccounts": ["XXXX-XXXX-XXXX"],
                        "upiIds": ["scammer@upi"],
                        "phoneNumbers": ["9876543210"],
                        "phishingLinks": ["http://malicious-link.example"],
                        "emails": ["scammer@example.com"],
                        "beneficiaryNames": ["John Doe"],
                        "bankNames": ["State Bank of India"],
                        "ifscCodes": ["SBIN0001234"],
                        "whatsappNumbers": ["919876543210"],
                    },
                    "agentNotes": "Scammer used urgency tactics and payment redirection",
                    "agentResponse": "Oh no! What do I need to do to verify?",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""

    status: StatusType = StatusType.ERROR
    error: str
    detail: str | None = None
