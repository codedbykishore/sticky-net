"""Custom exceptions for Sticky-Net."""


class StickyNetError(Exception):
    """Base exception for Sticky-Net."""

    pass


class ScamDetectionError(StickyNetError):
    """Error during scam detection."""

    pass


class AgentEngagementError(StickyNetError):
    """Error during agent engagement."""

    pass


class IntelligenceExtractionError(StickyNetError):
    """Error during intelligence extraction."""

    pass


class ConfigurationError(StickyNetError):
    """Configuration or environment error."""

    pass
