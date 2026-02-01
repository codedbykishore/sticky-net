"""Hybrid intelligence extraction from conversation messages.

Combines fast regex patterns with AI-powered extraction during engagement
for maximum intelligence capture.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.api.schemas import ExtractedIntelligence, OtherIntelItem
from src.intelligence.validators import (
    ExtractionSource,
    INDIAN_BANK_NAMES,
    UPI_PROVIDERS,
    SUSPICIOUS_URL_INDICATORS,
    is_suspicious_url,
    validate_phone_number,
    validate_upi_id,
    validate_bank_account,
    validate_ifsc,
    validate_email,
    validate_beneficiary_name,
)

logger = structlog.get_logger()


# =============================================================================
# REGEX PATTERNS FOR SCANNING (Extraction from raw text)
# These are different from validators - they FIND patterns in text
# =============================================================================

# Bank Account Patterns (for scanning text)
BANK_ACCOUNT_SCAN_PATTERNS = [
    # Plain 9-18 digit number
    re.compile(r"\b\d{9,18}\b"),
    # Formatted with spaces/hyphens: XXXX-XXXX-XXXX-XXXX
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{0,6}\b"),
    # Hyphenated single digits: "1-2-3-4-5-6-7-8-9-0-1-2-3-4"
    re.compile(r"\b\d(?:-\d){8,17}\b"),
    # Spaced out digits: "1 2 3 4 5 6 7 8 9 0 1 2 3" (9-18 digits with spaces)
    re.compile(r"\b(?:\d\s+){8,17}\d\b"),
    # Account number with prefix like "A/C" or "Account:"
    re.compile(r"(?:a/c|account|acc)[\s:]*#?\s*(\d{9,18})", re.IGNORECASE),
]

# UPI ID Patterns (for scanning text)
UPI_KNOWN_PROVIDER_PATTERN = re.compile(
    rf"\b[\w.-]+@(?:{'|'.join(UPI_PROVIDERS)})\b",
    re.IGNORECASE,
)
UPI_GENERIC_SCAN_PATTERN = re.compile(r"\b[\w.-]{3,}@[a-zA-Z]{2,15}\b")

# Phone Number Patterns (for scanning text)
PHONE_SCAN_PATTERNS = [
    # +91 prefix with 10 digits
    re.compile(r"\+91[-\s]?\d{10}\b"),
    # 12 digits: 91 followed by 10 digits starting with 6-9
    re.compile(r"\b91[6-9]\d{9}\b"),
    # 10 digits starting with 6-9
    re.compile(r"\b[6-9]\d{9}\b"),
    # Formatted with spaces/hyphens
    re.compile(r"\b[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b"),
    # 91 followed by formatted 10 digits
    re.compile(r"\b91[-\s]?[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b"),
    # 91-XXXX-XXX-XXX format (hyphens between groups)
    re.compile(r"\b91[-\s]\d{4}[-\s]\d{3}[-\s]\d{3}\b"),
]

# URL Pattern (for scanning text)
# Captures URLs with various TLDs including country codes (.in, .co.in), 
# new gTLDs (.work, .xyz, .online), and multi-part TLDs (.claim.in)
URL_SCAN_PATTERN = re.compile(
    r"https?://[\w.-]+(?:\.[a-z]{2,10})+(?:/[^\s<>\"'{}|\\^`\[\]]*)?",
    re.IGNORECASE,
)

# URL without protocol pattern - catches bit.ly/xyz, domain.com/path, sbi-bank.pay.in/xyz
URL_WITHOUT_PROTOCOL_PATTERN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s<>\"'{}|\\^`\[\]]*)?",
    re.IGNORECASE,
)

# Email Pattern (for scanning text)
EMAIL_SCAN_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# IFSC Code Pattern (for scanning text)
# Primary pattern: standalone IFSC codes
IFSC_SCAN_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)

# Additional IFSC patterns with context
IFSC_WITH_LABEL_PATTERNS = [
    # "IFSC: CODE" or "IFSC Code: CODE" or "ifsc code CODE" (don't capture the label 'code')
    re.compile(r"(?:ifsc\s+code|ifsc\s+number|ifsc)[\s:]+([A-Z]{4}0[A-Z0-9]{6})\b", re.IGNORECASE),
    # "code: CODE" or "code is CODE" (ensure we capture after the label)
    re.compile(r"(?:bank\s+)?code(?:\s+is)?[\s:]+([A-Z]{4}0[A-Z0-9]{6})\b", re.IGNORECASE),
    # Spaced out IFSC: "S B I N 0 0 0 1 2 3 4" (11 chars with spaces)
    re.compile(r"(?:ifsc\s+code|ifsc|code)[\s:]+([A-Z](?:\s+[A-Z0-9]){10})\b", re.IGNORECASE),
]

# Bank Name Pattern (for scanning text)
BANK_NAME_SCAN_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(name) for name in INDIAN_BANK_NAMES) + r")\b",
    re.IGNORECASE,
)

# Beneficiary Name Patterns (for scanning text)
# Name pattern allows letters, dots, hyphens: "Ramesh.Kumar", "Suresh-Kumar", "joeljohn"
# Made case-insensitive to capture lowercase names
NAME_PATTERN = r"[A-Za-z][a-z]*(?:[.-]?[A-Za-z][a-z]*)*"

BENEFICIARY_NAME_SCAN_PATTERNS = [
    # "name will show as 'Name'" or "name shows as Name"
    re.compile(
        rf"(?:name\s+(?:will\s+)?(?:show|display|appear)s?\s+(?:as)?[\s:]*['\"]?)({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})(?=['\"]|\s*[-–]|$|\.|,)",
        re.IGNORECASE,
    ),
    # "Account Holder: Name" or "A/C Holder Name: XYZ"
    re.compile(
        rf"(?:account\s+holder|a/c\s+holder|beneficiary|payee)[\s:]+(?:name)?[\s:]*['\"]?({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})(?=['\"]|\n|$|\.|,)",
        re.IGNORECASE,
    ),
    # "Transfer to Name" or "Send to Name" or "Pay to Name" (flexible version)
    re.compile(
        rf"(?:transfer|send|pay)\s+(?:money\s+|it\s+|amount\s+|rs\.?\s*\d+\s+)?(?:to|for)\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})(?:\s*[-–.,]|\s+(?:sir|madam|ji|sahab|or)|$|\n)",
        re.IGNORECASE,
    ),
    # "Name - Title" pattern like "Rahul Kumar - KYC Support"
    re.compile(
        rf"['\"]({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})\s*[-–]\s*(?:KYC|Support|Officer|Manager|Executive|Agent|Verification)",
        re.IGNORECASE,
    ),
    # "or just 'Name'" pattern
    re.compile(
        rf"(?:or\s+)?just\s+['\"]({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})['\"]",
        re.IGNORECASE,
    ),
    # "name is Name" or "my name is Name" or "naam Name hai" (Hindi)
    # Updated to better capture names immediately after "is"
    re.compile(
        rf"(?:my\s+)?(?:name|naam)\s+is\s+['\"]?({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})['\"]?(?:\s*[-–.,;]|$|\n|\s+(?:and|sir|madam|ji|from|please|pls))",
        re.IGNORECASE,
    ),
    # "mera naam Name" (Hindi: "my name is Name")
    re.compile(
        rf"mera\s+naam\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})",
        re.IGNORECASE,
    ),
    # Alternative: "name Name" without "is" (for Hindi patterns)
    re.compile(
        rf"(?:my\s+)?naam\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})\s+hai",
        re.IGNORECASE,
    ),
    # "ka naam Name hai" pattern (Hindi: "his/her name is Name")
    re.compile(
        rf"(?:ka|ki)\s+naam\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})\s+hai",
        re.IGNORECASE,
    ),
    # "name: Name" (colon required, not "is")
    re.compile(
        rf"(?:^|[\s,])name:\s*['\"]?({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,3}})['\"]?(?:\s*[-–.,]|$|\n|\s+(?:and|sir|madam|ji))",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "receiver: Name" or "receiver name: Name"
    re.compile(
        rf"(?:receiver|recipient)[\s:]+(?:name)?[\s:]*['\"]?({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,3}})['\"]?(?=$|\n|\.|,)",
        re.IGNORECASE,
    ),
    # "contact Name" or "call Name" (capturing only the name, not following words)
    re.compile(
        rf"(?:contact|call|reach|message)\s+(?:mr\.?\s+|mrs\.?\s+|ms\.?\s+)?({NAME_PATTERN}(?:\s+{NAME_PATTERN})?)(?=\s+(?:sir|madam|ji|on|at|via|for|my)|$|\n|\.|,)",
        re.IGNORECASE,
    ),
    # "my associate Name" or "my colleague Name"
    re.compile(
        rf"(?:my|our)\s+(?:associate|colleague|partner|friend|representative)\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN})?)(?=\s+(?:sir|madam|ji|phone|will|can)|$|\n|\.|,)",
        re.IGNORECASE,
    ),
    # "this is Name" or "I am Name" patterns (capturing only the name)
    re.compile(
        rf"(?:this\s+is|i\s+am|i'm|myself)\s+({NAME_PATTERN})(?:\s+{NAME_PATTERN})?(?=\s+(?:from|here|speaking|sir|madam|ji|and)|$|\n|\.|,)",
        re.IGNORECASE,
    ),
    # "Mr/Mrs/Shri Name" patterns
    re.compile(
        rf"(?:mr\.?|mrs\.?|ms\.?|shri|smt\.?|dr\.?)\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})(?:\s+(?:sir|madam|ji)|$|\n|\.|,)",
        re.IGNORECASE,
    ),
    # "- Name" or "– Name" at end of message (signature style)
    re.compile(
        rf"(?:^|\n)\s*[-–]\s*({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})\s*$",
        re.MULTILINE,
    ),
    # "Regards, Name" or "Thanks, Name" or "From, Name"
    re.compile(
        rf"(?:regards|thanks|thank\s+you|from|sincerely|best)[,:\s]+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "colleague/friend/associate Name" patterns
    re.compile(
        rf"(?:colleague|friend|associate|partner|manager|supervisor|team\s+member)\s+({NAME_PATTERN}(?:\s+{NAME_PATTERN}){{0,2}})(?=\s+(?:at|who|will|can|is|se\b)|$|\n|\.|,)",
        re.IGNORECASE,
    ),
]

# WhatsApp Number Patterns (for scanning text)
WHATSAPP_SCAN_PATTERNS = [
    # "WhatsApp: +91 98765 43210" or "WhatsApp Number: 9876543210"
    re.compile(
        r"(?:whatsapp|wa|whats\s*app)[:\s]*(?:no\.?|number|num)?[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
        re.IGNORECASE,
    ),
    # "message/contact on WhatsApp +91..."
    re.compile(
        r"(?:message|contact|call|reach)\s+(?:me\s+)?(?:on\s+)?whatsapp[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
        re.IGNORECASE,
    ),
    # "send to WhatsApp +91..."
    re.compile(
        r"(?:send|share)\s+(?:it\s+|screenshot\s+)?(?:to\s+|on\s+)?(?:my\s+)?whatsapp[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
        re.IGNORECASE,
    ),
    # WhatsApp link: wa.me/919876543210
    re.compile(r"wa\.me/(?:\+?91)?([6-9]\d{9})", re.IGNORECASE),
]

logger = structlog.get_logger()


@dataclass
class ExtractedEntity:
    """A single extracted intelligence entity."""

    value: str
    intel_type: str  # Type name (e.g., "bank_account", "upi_id", etc.)
    source: ExtractionSource = ExtractionSource.REGEX
    confidence: float = 1.0
    is_suspicious: bool = False
    context: str = ""


@dataclass
class ExtractionResult:
    """Complete extraction result from a conversation."""

    bank_accounts: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    phishing_links: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    beneficiary_names: list[str] = field(default_factory=list)
    bank_names: list[str] = field(default_factory=list)
    ifsc_codes: list[str] = field(default_factory=list)
    whatsapp_numbers: list[str] = field(default_factory=list)
    all_entities: list[ExtractedEntity] = field(default_factory=list)
    source: ExtractionSource = ExtractionSource.REGEX

    @property
    def has_intelligence(self) -> bool:
        """Check if any intelligence was extracted."""
        return bool(
            self.bank_accounts or
            self.upi_ids or
            self.phone_numbers or
            self.phishing_links or
            self.emails or
            self.beneficiary_names or
            self.bank_names or
            self.ifsc_codes or
            self.whatsapp_numbers
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "bankAccounts": self.bank_accounts,
            "upiIds": self.upi_ids,
            "phoneNumbers": self.phone_numbers,
            "phishingLinks": self.phishing_links,
            "emails": self.emails,
            "beneficiaryNames": self.beneficiary_names,
            "bankNames": self.bank_names,
            "ifscCodes": self.ifsc_codes,
            "whatsappNumbers": self.whatsapp_numbers,
        }

    def merge_with(self, other: "ExtractionResult") -> "ExtractionResult":
        """Merge with another extraction result, deduplicating entities."""
        return ExtractionResult(
            bank_accounts=list(set(self.bank_accounts + other.bank_accounts)),
            upi_ids=list(set(self.upi_ids + other.upi_ids)),
            phone_numbers=list(set(self.phone_numbers + other.phone_numbers)),
            phishing_links=list(set(self.phishing_links + other.phishing_links)),
            emails=list(set(self.emails + other.emails)),
            beneficiary_names=list(set(self.beneficiary_names + other.beneficiary_names)),
            bank_names=list(set(self.bank_names + other.bank_names)),
            ifsc_codes=list(set(self.ifsc_codes + other.ifsc_codes)),
            whatsapp_numbers=list(set(self.whatsapp_numbers + other.whatsapp_numbers)),
            all_entities=self.all_entities + other.all_entities,
            source=ExtractionSource.MERGED,
        )


class IntelligenceExtractor:
    """
    Hybrid intelligence extractor combining regex and AI extraction.

    Regex extraction:
    - Fast (~1ms), deterministic
    - Catches standard formats
    - Always runs on every message

    AI extraction:
    - Piggybacks on engagement LLM call (no extra cost)
    - Catches obfuscated data, contextual references
    - Returns structured output alongside response
    """

    def __init__(self) -> None:
        """Initialize extractor with patterns."""
        self.logger = logger.bind(component="IntelligenceExtractor")

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract all intelligence from text using regex patterns.

        Args:
            text: Text to extract from (single message or full conversation)

        Returns:
            ExtractionResult with all extracted entities
        """
        result = ExtractionResult(source=ExtractionSource.REGEX)

        # Extract phone numbers first (they overlap with bank account pattern)
        result.phone_numbers = self._extract_phone_numbers(text)
        phone_set = set(result.phone_numbers)
        
        # Extract each type of intelligence
        result.bank_accounts = self._extract_bank_accounts(text, phone_set)
        result.upi_ids = self._extract_upi_ids(text)
        result.phishing_links = self._extract_urls(text)
        result.emails = self._extract_emails(text)
        
        # Extract new intelligence types
        result.beneficiary_names = self._extract_beneficiary_names(text)
        result.bank_names = self._extract_bank_names(text)
        result.ifsc_codes = self._extract_ifsc_codes(text)
        result.whatsapp_numbers = self._extract_whatsapp_numbers(text)

        self.logger.info(
            "Regex extraction complete",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
            beneficiary_names=len(result.beneficiary_names),
            bank_names=len(result.bank_names),
            ifsc_codes=len(result.ifsc_codes),
            whatsapp_numbers=len(result.whatsapp_numbers),
        )

        return result

    def extract_from_conversation(
        self,
        messages: list[dict[str, Any]],
    ) -> ExtractionResult:
        """
        Extract intelligence from a full conversation using regex.
        
        IMPORTANT: Only extracts from scammer messages, not honeypot agent messages.

        Args:
            messages: List of message dicts with 'sender' and 'text' fields

        Returns:
            ExtractionResult with deduplicated entities
        """
        # Only extract from scammer messages, not honeypot agent messages
        # Filter out messages from 'agent', 'honeypot', 'assistant', 'pushpa', 'system'
        scammer_keywords = ["agent", "honeypot", "assistant", "pushpa", "system", "bot"]
        
        scammer_messages = [
            msg for msg in messages
            if msg.get("sender", "").lower() not in scammer_keywords
        ]
        
        # Combine only scammer message texts
        full_text = " ".join(msg.get("text", "") for msg in scammer_messages)
        return self.extract(full_text)

    def parse_ai_extraction(
        self,
        ai_extracted: dict[str, Any] | None,
    ) -> ExtractionResult:
        """
        Parse AI-extracted intelligence from structured output.

        Args:
            ai_extracted: Dict from AI structured output with intelligence fields

        Returns:
            ExtractionResult from AI extraction
        """
        if not ai_extracted:
            return ExtractionResult(source=ExtractionSource.AI)

        result = ExtractionResult(source=ExtractionSource.AI)

        # Parse and validate each field
        raw_accounts = ai_extracted.get("bank_accounts", [])
        for acc in raw_accounts:
            clean = self._clean_number(str(acc))
            if self._is_valid_bank_account(clean):
                result.bank_accounts.append(clean)

        raw_upi = ai_extracted.get("upi_ids", [])
        for upi in raw_upi:
            if "@" in str(upi):
                result.upi_ids.append(str(upi).lower())

        raw_phones = ai_extracted.get("phone_numbers", [])
        for phone in raw_phones:
            clean = self._clean_number(str(phone))
            if self._is_valid_phone(clean):
                result.phone_numbers.append(clean)

        raw_urls = ai_extracted.get("urls", [])
        for url in raw_urls:
            # In honeypot context, all URLs are suspicious - no filtering needed
            url_str = str(url).strip()
            if url_str:  # Only check non-empty
                result.phishing_links.append(url_str)

        raw_emails = ai_extracted.get("emails", [])
        for email in raw_emails:
            if "@" in str(email) and "." in str(email):
                result.emails.append(str(email).lower())

        # Parse new intelligence types
        raw_beneficiaries = ai_extracted.get("beneficiary_names", [])
        for name in raw_beneficiaries:
            clean_name = str(name).strip()
            if self._is_valid_name(clean_name):
                result.beneficiary_names.append(clean_name)

        raw_banks = ai_extracted.get("bank_names", [])
        for bank in raw_banks:
            clean_bank = str(bank).strip()
            if clean_bank:
                result.bank_names.append(clean_bank)

        raw_ifsc = ai_extracted.get("ifsc_codes", [])
        for ifsc in raw_ifsc:
            clean_ifsc = str(ifsc).strip().upper()
            if self._is_valid_ifsc(clean_ifsc):
                result.ifsc_codes.append(clean_ifsc)

        raw_whatsapp = ai_extracted.get("whatsapp_numbers", [])
        for wa_num in raw_whatsapp:
            clean = self._clean_number(str(wa_num))
            if self._is_valid_phone(clean):
                result.whatsapp_numbers.append(clean)

        self.logger.info(
            "AI extraction parsed",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
            beneficiary_names=len(result.beneficiary_names),
            bank_names=len(result.bank_names),
            ifsc_codes=len(result.ifsc_codes),
            whatsapp_numbers=len(result.whatsapp_numbers),
        )

        return result

    def merge_extractions(
        self,
        regex_result: ExtractionResult,
        ai_result: ExtractionResult,
    ) -> ExtractionResult:
        """
        Merge regex and AI extraction results.

        Args:
            regex_result: Result from regex extraction
            ai_result: Result from AI extraction

        Returns:
            Merged and deduplicated ExtractionResult
        """
        merged = regex_result.merge_with(ai_result)

        self.logger.info(
            "Extractions merged",
            total_bank_accounts=len(merged.bank_accounts),
            total_upi_ids=len(merged.upi_ids),
            total_phone_numbers=len(merged.phone_numbers),
            total_urls=len(merged.phishing_links),
            total_emails=len(merged.emails),
            total_beneficiary_names=len(merged.beneficiary_names),
            total_bank_names=len(merged.bank_names),
            total_ifsc_codes=len(merged.ifsc_codes),
            total_whatsapp_numbers=len(merged.whatsapp_numbers),
        )

        return merged

    def _extract_bank_accounts(self, text: str, phone_numbers: set[str] | None = None) -> list[str]:
        """Extract bank account numbers, excluding phone numbers."""
        accounts = set()
        phone_set = phone_numbers or set()

        for pattern in BANK_ACCOUNT_SCAN_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                # Clean and validate
                clean = self._clean_number(match)
                if self._is_valid_bank_account(clean):
                    # Exclude if it's a valid phone number (10 digits starting with 6-9)
                    if len(clean) == 10 and clean[0] in "6789" and clean in phone_set:
                        continue
                    accounts.add(clean)

        return list(accounts)

    def _extract_upi_ids(self, text: str) -> list[str]:
        """Extract UPI IDs - ONLY from known UPI providers."""
        upi_ids = set()

        # Normalize spaces around @ to handle "name @ provider" format
        normalized_text = re.sub(r'\s*@\s*', '@', text)

        # ONLY use known provider pattern - strict matching to avoid false positives
        # This prevents emails like "name@example.com" from being detected as UPI
        matches = UPI_KNOWN_PROVIDER_PATTERN.findall(normalized_text)
        upi_ids.update(m.lower() for m in matches)

        return list(upi_ids)

    def _extract_phone_numbers(self, text: str) -> list[str]:
        """Extract phone numbers."""
        phones = set()

        for pattern in PHONE_SCAN_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                clean = self._clean_number(match)
                if self._is_valid_phone(clean):
                    phones.add(clean)

        return list(phones)

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs from scammer messages, excluding UPI/email fragments."""
        urls = set()

        # Extract URLs with protocol (http/https)
        matches = URL_SCAN_PATTERN.findall(text)
        for url in matches:
            # Clean trailing punctuation
            clean_url = url.rstrip(".,;:!?)")
            urls.add(clean_url)

        # Extract URLs without protocol (bit.ly/xyz, sbi-bank.pay.in/abc)
        protocol_less_matches = URL_WITHOUT_PROTOCOL_PATTERN.findall(text)
        for url in protocol_less_matches:
            # Clean trailing punctuation
            clean_url = url.rstrip(".,;:!?)")
            
            # Skip if already found with protocol
            if any(clean_url in existing for existing in urls):
                continue
            
            # Skip if it's part of a UPI ID or email (contains @ symbol in context)
            # Check if this URL fragment is part of "something@domain" pattern
            escaped_url = re.escape(clean_url)
            if re.search(rf'\S+@{escaped_url}', text) or re.search(rf'{escaped_url}@\S+', text):
                continue
                
            # Skip common false positives (file extensions, version numbers)
            if clean_url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.txt')):
                continue
            if re.match(r'^v?\d+\.\d+', clean_url):  # version numbers like v1.2.3
                continue
            
            # Skip single-word domains without path (likely email/UPI fragments)
            # e.g., "example.com" without http:// or a path is suspicious
            if not clean_url.startswith('http') and '/' not in clean_url and clean_url.count('.') <= 1:
                # Check if it's an actual domain with suspicious keywords
                suspicious_keywords = ['bank', 'pay', 'kyc', 'verify', 'update', 'secure', 'claim']
                if not any(keyword in clean_url.lower() for keyword in suspicious_keywords):
                    continue
            
            # In honeypot context, domain-looking URLs with paths are intelligence
            urls.add(clean_url)

        return list(urls)

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses."""
        emails = set()

        matches = EMAIL_SCAN_PATTERN.findall(text)
        for email in matches:
            # Exclude UPI IDs that look like emails
            if not self._is_upi_provider(email):
                emails.add(email.lower())

        return list(emails)

    def _extract_beneficiary_names(self, text: str) -> list[str]:
        """Extract beneficiary/account holder names."""
        names = set()

        for pattern in BENEFICIARY_NAME_SCAN_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                # Clean the name
                clean_name = str(match).strip().strip("'\"")
                if self._is_valid_name(clean_name):
                    # Title case the name for consistency
                    names.add(clean_name.title())

        return list(names)

    def _extract_bank_names(self, text: str) -> list[str]:
        """Extract Indian bank names."""
        banks = set()

        matches = BANK_NAME_SCAN_PATTERN.findall(text)
        for match in matches:
            # Normalize bank name (uppercase for abbreviations, title case for full names)
            clean_bank = str(match).strip()
            # Standardize common abbreviations
            upper_bank = clean_bank.upper()
            if upper_bank in ["SBI", "PNB", "BOB", "BOI", "UCO", "PSB", "IOB", "HDFC", "ICICI", "IDBI", "RBL", "IDFC"]:
                banks.add(upper_bank)
            elif upper_bank in ["AXIS", "KOTAK", "FEDERAL", "BANDHAN", "CANARA", "EQUITAS", "UJJIVAN", "INDUSIND"]:
                banks.add(clean_bank.title())
            else:
                banks.add(clean_bank.title())

        return list(banks)

    def _extract_ifsc_codes(self, text: str) -> list[str]:
        """Extract IFSC codes."""
        ifsc_codes = set()
        
        # Word to number mapping for spelled out numbers
        word_to_num = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
        }

        # Try primary pattern (standalone IFSC codes)
        matches = IFSC_SCAN_PATTERN.findall(text)
        for match in matches:
            clean_ifsc = str(match).strip().upper()
            if self._is_valid_ifsc(clean_ifsc):
                ifsc_codes.add(clean_ifsc)
        
        # Try patterns with labels ("ifsc code XXXX")
        for pattern in IFSC_WITH_LABEL_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                # Remove all spaces from the match (handles "H D F C 0 0 0 1 2 3 4")
                clean_ifsc = str(match).replace(' ', '').strip().upper()
                
                # Convert spelled out numbers: "SBIN zero zero zero" -> "SBIN000"
                for word, digit in word_to_num.items():
                    clean_ifsc = re.sub(word, digit, clean_ifsc, flags=re.IGNORECASE)
                
                if self._is_valid_ifsc(clean_ifsc):
                    ifsc_codes.add(clean_ifsc)

        return list(ifsc_codes)

    def _extract_whatsapp_numbers(self, text: str) -> list[str]:
        """Extract WhatsApp phone numbers."""
        whatsapp_nums = set()

        for pattern in WHATSAPP_SCAN_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                clean = self._clean_number(str(match))
                if self._is_valid_phone(clean):
                    whatsapp_nums.add(clean)

        return list(whatsapp_nums)

    def _clean_number(self, number: str) -> str:
        """Remove formatting from numbers (spaces, hyphens, parentheses, dots)."""
        return re.sub(r"[-\s().+]", "", number)

    def _is_valid_bank_account(self, number: str) -> bool:
        """Validate bank account number."""
        # Must be 9-18 digits
        if not number.isdigit():
            return False
        if len(number) < 9 or len(number) > 18:
            return False
        # Exclude obviously fake patterns
        if number == "0" * len(number):
            return False
        if len(set(number)) == 1:  # All same digit
            return False
        
        # Exclude phone-like numbers (10-12 digits that look like phones)
        if self._looks_like_phone(number):
            return False
        
        return True
    
    def _looks_like_phone(self, number: str) -> bool:
        """
        Check if a number looks like a phone number.
        
        Phone patterns:
        - 10 digits starting with 6, 7, 8, or 9
        - 12 digits starting with 91 followed by 6, 7, 8, or 9
        - 11 digits starting with 91 (less common but possible)
        """
        if not number.isdigit():
            return False
        
        # 10 digits starting with 6-9 = phone
        if len(number) == 10 and number[0] in "6789":
            return True
        
        # 12 digits: 91 + 10 digits starting with 6-9 = phone with country code
        if len(number) == 12 and number.startswith("91") and number[2] in "6789":
            return True
        
        # 11 digits: 91 + 9 digits (less common, but could be truncated)
        # Being conservative here - only if starts with 91 and next digit is 6-9
        if len(number) == 11 and number.startswith("91") and number[2] in "6789":
            return True
        
        return False

    def _is_valid_phone(self, number: str) -> bool:
        """Validate Indian phone number."""
        # Remove +91 prefix if present
        clean = number
        if clean.startswith("+91"):
            clean = clean[3:]
        elif clean.startswith("91") and len(clean) in (11, 12):
            clean = clean[2:]
        # Remove any remaining non-digits
        clean = re.sub(r"\D", "", clean)
        if len(clean) != 10:
            return False
        if clean[0] not in "6789":  # Indian mobile starts with 6-9
            return False
        return True

    def _looks_like_email(self, text: str) -> bool:
        """Check if text looks like an email address."""
        email_tlds = [".com", ".org", ".net", ".in", ".co", ".edu", ".gov"]
        return any(text.lower().endswith(tld) for tld in email_tlds)

    def _is_upi_provider(self, email: str) -> bool:
        """Check if email domain is actually a UPI provider."""
        upi_providers = ["ybl", "paytm", "okicici", "oksbi", "upi"]
        domain = email.split("@")[-1].split(".")[0].lower()
        return domain in upi_providers

    def _is_valid_name(self, name: str) -> bool:
        """Validate beneficiary name using centralized validation with blocklist."""
        return validate_beneficiary_name(name)

    def _is_valid_ifsc(self, ifsc: str) -> bool:
        """Validate IFSC code format."""
        # IFSC format: 4 letters (bank code) + 0 + 6 alphanumeric
        if not ifsc or len(ifsc) != 11:
            return False
        # First 4 characters must be letters
        if not ifsc[:4].isalpha():
            return False
        # 5th character must be 0
        if ifsc[4] != '0':
            return False
        # Last 6 characters must be alphanumeric
        if not ifsc[5:].isalnum():
            return False
        return True

    # -------------------------------------------------------------------------
    # LLM Intelligence Validation (Hybrid Approach)
    # -------------------------------------------------------------------------

    def validate_llm_extraction(self, llm_intel: ExtractedIntelligence) -> ExtractedIntelligence:
        """
        Validate and clean LLM-extracted intelligence using regex patterns.

        This is the hybrid approach: LLM extracts (flexible), regex validates (reliable).
        - UPI IDs: Must match known provider patterns
        - Bank accounts: Must be valid length (9-18 digits)
        - IFSC codes: Must match format [A-Z]{4}0[A-Z0-9]{6}
        - Phone numbers: Light validation (keep LLM flexibility for formatting)
        - Beneficiary names, URLs, other_critical_info: Keep as-is (LLM is better)
        """
        validated = ExtractedIntelligence(
            bankAccounts=[acc for acc in llm_intel.bankAccounts if self._validate_bank_account(acc)],
            upiIds=[upi for upi in llm_intel.upiIds if self._validate_upi_id(upi)],
            phoneNumbers=llm_intel.phoneNumbers,  # Keep LLM's phone extraction (more flexible)
            phishingLinks=llm_intel.phishingLinks,  # Keep as-is (LLM understands context)
            emails=llm_intel.emails,  # Keep as-is
            beneficiaryNames=llm_intel.beneficiaryNames,  # Keep as-is
            bankNames=llm_intel.bankNames,  # Keep as-is
            ifscCodes=[code for code in llm_intel.ifscCodes if self._validate_ifsc(code)],
            whatsappNumbers=llm_intel.whatsappNumbers,  # Keep as-is
            other_critical_info=llm_intel.other_critical_info,  # Keep as-is (LLM is better)
        )

        self.logger.info(
            "LLM extraction validated",
            bank_accounts_in=len(llm_intel.bankAccounts),
            bank_accounts_out=len(validated.bankAccounts),
            upi_ids_in=len(llm_intel.upiIds),
            upi_ids_out=len(validated.upiIds),
            ifsc_codes_in=len(llm_intel.ifscCodes),
            ifsc_codes_out=len(validated.ifscCodes),
        )

        return validated

    def _validate_bank_account(self, account: str) -> bool:
        """Validate bank account number (9-18 digits)."""
        digits = re.sub(r'\D', '', account)
        return 9 <= len(digits) <= 18

    def _validate_upi_id(self, upi: str) -> bool:
        """Validate UPI ID matches known provider patterns."""
        # Use simplified check for user@provider format
        return bool(re.match(r'[\w.-]+@[a-zA-Z]+', upi))

    def _validate_ifsc(self, code: str) -> bool:
        """Validate IFSC code format."""
        return bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', code.upper()))

    # -------------------------------------------------------------------------
    # Intelligence Merging (Regex + LLM)
    # -------------------------------------------------------------------------

    def merge_intelligence(
        self,
        regex_intel: ExtractionResult,
        llm_intel: ExtractedIntelligence | None,
    ) -> ExtractedIntelligence:
        """
        Merge regex-extracted and LLM-extracted intelligence.

        Args:
            regex_intel: Result from regex extraction (ExtractionResult)
            llm_intel: Result from LLM extraction (ExtractedIntelligence), may be None

        Returns:
            Merged and deduplicated ExtractedIntelligence
        """
        # Start with regex results converted to ExtractedIntelligence format
        merged = ExtractedIntelligence(
            bankAccounts=list(set(regex_intel.bank_accounts)),
            upiIds=list(set(regex_intel.upi_ids)),
            phoneNumbers=list(set(regex_intel.phone_numbers)),
            phishingLinks=list(set(regex_intel.phishing_links)),
            emails=list(set(regex_intel.emails)),
            beneficiaryNames=list(set(regex_intel.beneficiary_names)),
            bankNames=list(set(regex_intel.bank_names)),
            ifscCodes=list(set(regex_intel.ifsc_codes)),
            whatsappNumbers=list(set(regex_intel.whatsapp_numbers)),
            other_critical_info=[],
        )

        if llm_intel is None:
            return merged

        # Validate LLM extraction before merging
        validated_llm = self.validate_llm_extraction(llm_intel)

        # Merge and deduplicate
        merged.bankAccounts = list(set(merged.bankAccounts + validated_llm.bankAccounts))
        merged.upiIds = list(set(merged.upiIds + validated_llm.upiIds))
        merged.phoneNumbers = list(set(merged.phoneNumbers + validated_llm.phoneNumbers))
        merged.phishingLinks = list(set(merged.phishingLinks + validated_llm.phishingLinks))
        merged.emails = list(set(merged.emails + validated_llm.emails))
        merged.beneficiaryNames = list(set(merged.beneficiaryNames + validated_llm.beneficiaryNames))
        merged.bankNames = list(set(merged.bankNames + validated_llm.bankNames))
        merged.ifscCodes = list(set(merged.ifscCodes + validated_llm.ifscCodes))
        merged.whatsappNumbers = list(set(merged.whatsappNumbers + validated_llm.whatsappNumbers))

        # Merge other_critical_info (deduplicate by label+value)
        seen_other = {(item.label, item.value) for item in merged.other_critical_info}
        for item in validated_llm.other_critical_info:
            if (item.label, item.value) not in seen_other:
                merged.other_critical_info.append(item)
                seen_other.add((item.label, item.value))

        self.logger.info(
            "Intelligence merged (regex + LLM)",
            total_bank_accounts=len(merged.bankAccounts),
            total_upi_ids=len(merged.upiIds),
            total_phone_numbers=len(merged.phoneNumbers),
            total_urls=len(merged.phishingLinks),
            total_other_info=len(merged.other_critical_info),
        )

        return merged


# Singleton instance
_extractor_instance: IntelligenceExtractor | None = None


def get_extractor() -> IntelligenceExtractor:
    """Get or create extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = IntelligenceExtractor()
    return _extractor_instance