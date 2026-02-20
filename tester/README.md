# Honeypot Tester 🍯

An automated **scammer simulator** that acts as the hackathon evaluation system —
it sends scam messages to your honeypot API, drives multi-turn conversations using
Gemini AI (Vertex AI), and scores the results using the **exact rubric from the
hackathon documentation**.

---

## What It Does

```
┌─────────────────────────────────────────────────────┐
│  Tester (you are the scammer)                       │
│                                                     │
│  1. Sends initial scam message → Honeypot API       │
│  2. Receives honeypot reply                         │
│  3. Uses Gemini to generate realistic follow-up     │
│  4. Repeats up to 10 turns                          │
│  5. Requests final output from honeypot             │
│  6. Scores everything against the rubric            │
│  7. Shows detailed breakdown in web UI              │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
cd tester/
./start.sh
```

Opens at **http://localhost:8090**

---

## Manual Setup

```bash
cd tester/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit if needed
uvicorn app:app --host 0.0.0.0 --port 8090 --reload
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | `sticky-net-485205` | GCP project for Vertex AI |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI region |
| `USE_VERTEXAI` | `true` | Use Vertex AI (needs `gcloud auth`) |
| `SCAMMER_MODEL` | `gemini-2.5-flash` | Gemini model for scammer agent |
| `PORT` | `8090` | Tester server port |
| `REQUEST_TIMEOUT` | `30` | Per-request timeout in seconds |

Vertex AI auth uses your existing `gcloud auth application-default credentials`.

---

## Built-in Scenarios

| ID | Name | Type | Weight | Fake Data |
|----|------|------|--------|-----------|
| `bank_fraud_001` | Bank Fraud – Account Compromise | bank_fraud | 35% | phone, bank acct, UPI, email |
| `upi_fraud_001` | UPI Cashback Scam | upi_fraud | 35% | phone, 2 UPI IDs, phishing link |
| `phishing_001` | Fake Product Offer / Phishing | phishing | 30% | phone, 2 links, email, order# |
| `insurance_fraud_001` | Fake Insurance Policy Scam | insurance_fraud | 0% | phone, bank, UPI, email, policy# |

> The insurance scenario has `weight: 0` by default — include it in a custom suite
> by setting a weight manually, or use it as a bonus stress test.

---

## Scoring Rubric (100 pts per scenario)

### 1. Scam Detection — 20 pts
- `scamDetected: true` in finalOutput → 20 pts

### 2. Extracted Intelligence — 30 pts
- `30 ÷ total_fake_items` per correctly extracted item

### 3. Conversation Quality — 30 pts
| Sub-metric | Max | Thresholds |
|------------|-----|------------|
| Turn count | 8 | ≥8→8, ≥6→6, ≥4→3 |
| Questions asked | 4 | ≥5→4, ≥3→2, ≥1→1 |
| Relevant questions | 3 | ≥3→3, ≥2→2, ≥1→1 |
| Red flags | 8 | ≥5→8, ≥3→5, ≥1→2 |
| Elicitation attempts | 7 | 1.5 each, cap 7 |

### 4. Engagement Quality — 10 pts
- Duration >0s: +1, >60s: +2, >180s: +1
- Messages >0: +2, ≥5: +3, ≥10: +1

### 5. Response Structure — 10 pts
- `sessionId`: 2 pts, `scamDetected`: 2 pts, `extractedIntelligence`: 2 pts
- `totalMessagesExchanged`/`engagementDurationSeconds`: 1 pt
- `agentNotes`: 1 pt, `scamType`: 1 pt, `confidenceLevel`: 1 pt
- Missing required field: **-1 pt penalty** each

### Final Score
```
Final = Σ(scenario_score × weight/100) × 0.9 + code_quality(0–10)
```

---

## REST API

### Run full suite (async)
```http
POST /api/run/suite
{
  "target_url": "https://your-api.com/detect",
  "api_key": "your-key",
  "scenario_ids": ["bank_fraud_001", "upi_fraud_001", "phishing_001"],
  "code_quality_score": 8
}
→ { "job_id": "uuid", "status": "queued" }
```

### Poll job status
```http
GET /api/jobs/{job_id}
→ { "status": "running/completed/failed", "final_score": {...}, "session_logs": [...] }
```

### Run single scenario (blocking)
```http
POST /api/run/single
{ "target_url": "…", "scenario_id": "bank_fraud_001" }
```

### Custom scenario
```http
POST /api/run/custom
{
  "target_url": "…",
  "name": "My Custom Scam",
  "scam_type": "custom",
  "initial_message": "URGENT: Your account…",
  "persona_context": "You are a scammer named X…",
  "phone_numbers": ["+91-9999999999"],
  "upi_ids": ["scam@upi"]
}
```

### List scenarios
```http
GET /api/scenarios
```

---

## Architecture

```
tester/
├── app.py                  # FastAPI app + REST endpoints + web UI serve
├── src/
│   ├── scenarios.py        # Pre-defined scam scenarios + fake data
│   ├── scammer_agent.py    # Gemini-powered automated scammer
│   ├── conversation.py     # Multi-turn conversation orchestrator
│   └── evaluator.py        # Scoring engine (exact hackathon rubric)
├── static/
│   └── index.html          # Single-page web UI
├── requirements.txt
├── .env.example
└── start.sh
```

---

## Notes

- **Does NOT touch the main application** — runs completely independently
- Uses `gcloud auth application-default credentials` already configured
- Gemini scammer agent reveals fake data naturally across the conversation
- Polling interval is 2.5s — page updates live as the suite runs
- All jobs are in-memory; restart clears them (add Redis for persistence)
