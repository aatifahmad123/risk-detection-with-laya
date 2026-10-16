# Laya Banking Fraud Risk Engine

Local prototype for using Laya as a structured decision layer over
banking customer-agent call transcripts. Minimal HTML/CSS frontend on a
small standard-library Python server — no web frameworks, no build step.

## Architecture

Banking call transcript -> Laya -> typed risk decisions -> HTML dashboard

Decisions:
- `fraud_category` — choice
- `risk_level` — score
- `otp_involved` — noul
- `unauthorized_transaction` — noul
- `social_engineering` — noul
- `escalation_required` — noul

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open http://127.0.0.1:7860

The server exposes:
- `GET /` — dashboard
- `GET /api/samples` — list of synthetic calls
- `GET /api/samples/{index}` — transcript for a sample
- `POST /api/analyze` — run Laya on `{"transcript": "..."}`

The English Laya checkpoint loads on the first analysis and then stays in
memory for subsequent calls.

## Files

- `app.py` — HTTP server + JSON API
- `static/index.html` — dashboard
- `static/style.css` — styles
- `laya_questions.json` — decision definitions
- `data/banking_fraud_call_transcripts.json` — machine-readable synthetic dataset
- `data/banking_fraud_call_transcripts.txt` — readable transcript collection

## Next step

Add speech-to-text before the Laya layer:

Audio -> STT -> rolling transcript -> Laya -> risk timeline -> agent alerts.

Keep automated actions human-reviewed for banking use cases.
