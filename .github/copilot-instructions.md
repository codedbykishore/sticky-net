# Sticky-Net: AI Agentic Honey-Pot System

# Important Note:
Remember that your context window is limited - especially the output size. So you should ALWAYS work in discrete steps and run each step using #runSubagent

## Project Overview

An AI-powered honeypot system that detects scam messages and autonomously engages scammers to extract actionable intelligence (bank accounts, UPI IDs, phishing links) through multi-turn conversations.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+ |
| **API Framework** | FastAPI |
| **LLM Orchestration** | LangChain / LangGraph |
| **LLM Provider** | Google Vertex AI (Gemini 3 Pro/Flash) |
| **Database** | Firestore (conversation state & intelligence) |
| **Containerization** | Docker |
| **Deployment** | Google Cloud Run |
| **Local Dev** | Docker Compose |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Public API Endpoint                       │
│                    (x-api-key authentication)                    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Request Handler (FastAPI)                   │
│   • Validate JSON schema                                         │
│   • Extract message + conversationHistory                        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Scam Detection Module                       │
│   • Analyze message for fraud indicators                         │
│   • Check urgency tactics, payment requests, phishing patterns   │
│   • Return: scamDetected (bool) + confidence score               │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
            [Not Scam]                    [Scam Detected]
                    │                           │
                    ▼                           ▼
        ┌───────────────────┐     ┌─────────────────────────────┐
        │   Return neutral  │     │   AI Agent Controller       │
        │     response      │     │   (LangChain/LangGraph)     │
        └───────────────────┘     │   • Maintain human persona   │
                                  │   • Adaptive responses       │
                                  │   • Extract intelligence     │
                                  └─────────────┬───────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────────┐
                                  │   Intelligence Extractor    │
                                  │   • Bank account patterns   │
                                  │   • UPI ID patterns         │
                                  │   • Phishing URL detection  │
                                  └─────────────┬───────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────────┐
                                  │   Response Builder          │
                                  │   • Format JSON response    │
                                  │   • Include metrics         │
                                  │   • Persist to Firestore    │
                                  └─────────────────────────────┘
```

## Project Structure

```
sticky-net/
├── .github/
│   ├── copilot-instructions.md          # This file
│   ├── workflows/
│   │   └── ci.yml                        # CI/CD pipeline
│   └── instructions/
│       ├── milestone-1-project-setup.instructions.md
│       ├── milestone-2-api-layer.instructions.md
│       ├── milestone-3-scam-detection.instructions.md
│       ├── milestone-4-agent-engagement.instructions.md
│       ├── milestone-5-intelligence-extraction.instructions.md
│       └── milestone-6-deployment.instructions.md
├── docs/
│   ├── DOCUMENTATION.md                  # API spec
│   └── PROBLEM_STATEMENT.md              # Requirements
├── src/
│   ├── __init__.py
│   ├── main.py                           # FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                     # API endpoints
│   │   ├── middleware.py                 # API key auth
│   │   └── schemas.py                    # Pydantic models
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── detector.py                   # Scam detection logic
│   │   └── patterns.py                   # Fraud indicator patterns
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── honeypot_agent.py             # Main LangChain agent
│   │   ├── persona.py                    # Human persona management
│   │   └── prompts.py                    # Agent system prompts
│   └── intelligence/
│       ├── __init__.py
│       └── extractor.py                  # Entity extraction
├── config/
│   ├── __init__.py
│   └── settings.py                       # Configuration management
├── tests/
│   ├── __init__.py
│   ├── conftest.py                       # Pytest fixtures
│   ├── test_api.py
│   ├── test_detection.py
│   ├── test_agent.py
│   └── test_extractor.py
├── pyproject.toml                        # Python dependencies
├── Dockerfile                            # Container config
├── docker-compose.yml                    # Local development
├── .env.example                          # Environment template
├── .gitignore
└── README.md
```

## API Contract

### Request Format
```json
{
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify immediately.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

### Response Format
```json
{
  "status": "success",
  "scamDetected": true,
  "engagementMetrics": {
    "engagementDurationSeconds": 420,
    "totalMessagesExchanged": 18
  },
  "extractedIntelligence": {
    "bankAccounts": ["XXXX-XXXX-XXXX"],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://malicious-link.example"]
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection"
}
```

## Development Milestones

| # | Milestone | Description | Instruction File |
|---|-----------|-------------|------------------|
| 1 | **Project Setup** | Scaffold structure, dependencies, Docker, local dev | `milestone-1-project-setup.instructions.md` |
| 2 | **API Layer** | FastAPI endpoints, authentication, request validation | `milestone-2-api-layer.instructions.md` |
| 3 | **Scam Detection** | Fraud indicator analysis, confidence scoring | `milestone-3-scam-detection.instructions.md` |
| 4 | **Agent Engagement** | LangChain agent with human persona, multi-turn | `milestone-4-agent-engagement.instructions.md` |
| 5 | **Intelligence Extraction** | Bank/UPI/URL pattern extraction | `milestone-5-intelligence-extraction.instructions.md` |
| 6 | **Deployment** | GCP Cloud Run deployment, CI/CD pipeline | `milestone-6-deployment.instructions.md` |

## Coding Standards

### Python Style
- Use Python 3.11+ features (type hints, match statements)
- Follow PEP 8 with 100 char line limit
- Use `async/await` for I/O operations
- Type hints required for all function signatures
- Docstrings for all public functions (Google style)

### File Organization
- One class per file (generally)
- Keep modules focused and small (<300 lines)
- Use `__all__` for explicit exports

### Error Handling
- Use custom exceptions in `src/exceptions.py`
- Never expose internal errors to API responses
- Log errors with structured context

### Testing
- Minimum 80% coverage target
- Use pytest with async support
- Mock external services (Vertex AI, Firestore)

## Environment Variables

```bash
# API Configuration
API_KEY=your-secret-api-key
PORT=8080

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Firestore
FIRESTORE_COLLECTION=conversations

# Agent Configuration
LLM_MODEL=gemini-3-pro
LLM_TEMPERATURE=0.7
MAX_ENGAGEMENT_TURNS=50
```

## Key Patterns

### Intelligence Extraction Regex
```python
# Bank accounts: 9-18 digits, optionally formatted
BANK_ACCOUNT_PATTERN = r'\b\d{9,18}\b|\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{0,6}\b'

# UPI IDs: username@provider format
UPI_PATTERN = r'\b[\w.-]+@[a-zA-Z]+\b'

# Phishing URLs: http/https with suspicious indicators
URL_PATTERN = r'https?://[^\s<>"{}|\\^`\[\]]+'
```

### Scam Detection Indicators
- **Urgency**: "immediately", "today", "within 24 hours", "urgent"
- **Authority**: "RBI", "bank", "government", "police"
- **Threats**: "blocked", "suspended", "legal action", "arrested"
- **Requests**: "OTP", "PIN", "password", "verify", "update KYC"

## Agent Behavior Rules

1. **Never reveal detection** — Maintain believable human persona at all times
2. **Adaptive responses** — Vary tactics based on scammer's approach
3. **Natural extraction** — Ask clarifying questions that prompt intelligence sharing
4. **Context awareness** — Use full `conversationHistory` for coherent responses
5. **Safety limits** — Max engagement turns, timeout handling

## Ethical Constraints

- ❌ No impersonation of real individuals
- ❌ No illegal instructions or encouragement
- ❌ No harassment or threats
- ✅ Responsible data handling only
- ✅ Log all extracted intelligence securely

## Resources

- **LangChain Docs** — Use MCP: `docs-langchain` (see `.vscode/mcp.json`)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Vertex AI Docs](https://cloud.google.com/vertex-ai/docs)
- [Firestore Docs](https://firebase.google.com/docs/firestore)
