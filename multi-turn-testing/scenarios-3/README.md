# Test Scenarios - Set 3

## Overview
This set of test scenarios validates recent system improvements and edge cases:
- Non-scam message handling with normal responses
- Intelligence extraction filtering (scammer-only, not agent)
- Enhanced name extraction patterns
- URL detection without http/https protocol
- Long message handling and UI scrolling
- Mixed scam/non-scam conversations
- Special characters and formatting resilience
- Hinglish code-switching support

## Test Scenarios

### Category A: System Feature Tests (01-08)
Tests for specific system improvements and edge cases.

### 01. Non-Scam Normal Conversation
**Purpose:** Validates friendly responses for innocent messages
- Tests: "Hi", "Hello", "Good morning", "Thank you"
- Expected: Normal responses, no scam detection, no false positives
- Confidence should be <0.3

### 02. Intelligence Extraction Filtering Test
**Purpose:** Ensures only scammer data is extracted, not honeypot agent data
- Scammer provides: Ramesh Kumar, 9876543210, ramesh.verify@paytm, 123456789012
- Agent (Pushpa) provides: 999888777666, pushpa@ybl, 7777777777
- **Critical:** Agent data must NOT be extracted

### 03. Enhanced Name Extraction Patterns
**Purpose:** Tests improved name extraction in various contexts
- Patterns: "my name is X", "account holder: X", "send to X", "Mr. X", "Regards, X"
- Should extract: Hiruthik, Vijay Singh, Rajesh Patel, Suresh, Amit, Deepak Kumar, Rohit Sharma
- Validates signature styles and formal/informal introductions

### 04. URL Detection Without Protocol
**Purpose:** Catches phishing links without http/https prefix
- Tests: sbi-bank.pay.in/xY7834, hdfc-verify.secure.co.in, bit.ly/hdfc-kyc
- Should detect URLs with hyphens, multi-level subdomains, suspicious patterns
- URL shorteners (bit.ly, tinyurl.com, cutt.ly) should be flagged

### 05. Long Message Handling Test
**Purpose:** Validates extraction from lengthy paragraphs (>500 chars)
- Multiple intelligence points scattered throughout long text
- UI should handle multi-line textarea expansion (3 lines max, then scroll)
- No information loss in long messages

### 06. Mixed Scam and Non-Scam Messages
**Purpose:** Dynamic detection within same conversation
- Alternates between innocent ("Hello", "Thanks") and scam messages
- Should respond normally to greetings, engage for scam attempts
- Persistent intelligence extraction across turns

### 07. Special Characters and Formatting
**Purpose:** Resilience to evasion tactics
- Tests: Emojis (🚨💳⚡), extra spaces, hyphens, underscores, parentheses
- Formats: "91-9876543210", "ramesh @ paytm", "1234 5678 9012", "Name→Value"
- Should normalize and extract correctly

### 08. Multi-Language Hinglish Code-Switching
**Purpose:** Extraction from Hindi-English mixed messages
- Natural Hinglish: "Main Rajesh bol raha hoon", "UPI pe bhejo", "Call karo"
- Should extract names, UPIs, phones, accounts despite language mix
- Common in Indian scam scenarios

---

### Category B: Social Engineering Tests (09-13)
Tests for sophisticated scams that start with casual conversation.

### 09. Casual Conversation to Investment Scam
**Purpose:** Detects gradual transition from benign chat to scam
- Starts: "Hello! How are you?" (innocent)
- Middle: Stock market discussion, investment opportunity mention
- End: Unrealistic returns (18%), payment demands with full details
- Tests: Progressive confidence increase, social engineering detection

### 10. Friendly Chat to Loan Scam
**Purpose:** Friend/networking approach leading to fake loan offer
- Hinglish conversation about life and work
- Pivots to offering instant loans with minimal documentation
- Demands upfront processing fee (₹2000)
- Tests: Trust-building detection, upfront fee red flag

### 11. Job Discussion to Training Fee Scam
**Purpose:** Career advice morphing into employment fraud
- Sympathetic job market discussion
- Offers remote job with high salary, no experience needed
- Requires paid training (₹4999) with "refundable" promise
- Tests: Job scam detection, too-good-to-be-true indicators

### 12. Tech Discussion to Fake Support Scam
**Purpose:** Legitimate tech talk becoming tech support fraud
- Android update discussion, security tips (innocent)
- Claims virus detected, offers remote scan
- Demands payment (₹999) for cleaning/protection
- Tests: Fear tactics detection, remote access warning signs

### 13. Product Recommendation to Fake Payment Scam
**Purpose:** Shopping tips leading to e-commerce fraud
- Casual chat about Amazon/Flipkart sales
- Offers iPhone at 20-25k below market price
- Requires 50% advance to personal account
- Tests: Unrealistic discou (13 scenarios total)
python judge_simulator.py --scenarios-dir scenarios-3

# Run specific test
python judge_simulator.py --scenarios-dir scenarios-3 --scenario 02_extraction_filtering_test.json

# Run only feature tests (scenarios 01-08)
for i in {01..08}; do python judge_simulator.py --scenarios-dir scenarios-3 --scenario ${i}_*.json; done

# Run only social engineering tests (scenarios 09-13)
for i in {09..13}; do python judge_simulator.py --scenarios-dir scenarios-3 --scenario ${i}_*.json; done
# Run all scenarios-3 tests
python judge_simulator.py --scenarios-dir scenarios-3

# Run specific test
python judge_simulator.py --scenarios-dir scenarios-3 --scenario 02_extraction_filtering_test.json

# Verbose output with extraction details
python judge_simulator.py --scenarios-dir scenarios-3 --verbose
```

## Validation Criteria

### Extraction Accuracy
- Precision: >95% (no false positives)
- Recall: >90% (catch most intelligence)
- Agent data: 0% extraction (complete filtering)

### Response Quality
- Non-scam messages: Friendly, natural responses
- Scam messages: Believable engagement without revealing detection
- Context awareness: Maintain conversation flow


### Feature Tests (01-08)
- All 8 scenarios should pass validation
- No agent/honeypot data leakage (Scenario 02)
- URL detection with/without protocol (Scenario 04)
- Name extraction from 10+ patterns (Scenario 03)
- Normal conversation support without false positives (Scenario 01)

### Social Engineering Tests (09-13)
- Gradual confidence increase detection (starts <0.3, ends >0.9)
- Early turns classified as non-scam or low confidence
- Later turns after "pivot" classified as high confidence scam
- Trust-building phase should not trigger false positives
- Clear detection once payment demands or suspicious details emerge

### Overall Success Criteria
- **13/13 scenarios pass** with correct classifications
- **No false positives** in casual conversation phases
- **No false negatives** once scam indicators appear
- **Complete intelligence extraction** in final turns (6+ items)
- **Appropriate responses** matching conversation context
## Success Metrics
- All 8 scenarios should pass validation
- No agent/honeypot data leakage
- URL detection with/without protocol
- Name extraction from signatures, greetings, payment instructions
- Normal conversation support without false positives
