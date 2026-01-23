# Sticky-Net 🕸️

AI-powered honeypot system that detects scam messages and autonomously engages scammers to extract actionable intelligence.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- GCP Service Account (for Vertex AI & Firestore)

### Local Development

1. **Clone and setup environment:**
   ```bash
   git clone <repo-url>
   cd sticky-net
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Place GCP service account key:**
   ```bash
   mkdir -p secrets
   cp /path/to/service-account.json secrets/
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Or run locally with Python:**
   ```bash
   pip install -e ".[dev]"
   uvicorn src.main:app --reload --port 8080
   ```

### API Usage

```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked. Send OTP now!",
      "timestamp": "2026-01-21T10:15:30Z"
    },
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```

### Running Tests

```bash
pytest --cov=src tests/
```

## Architecture

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed architecture documentation.

## License

MIT
