import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import laya

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
HOST, PORT = "127.0.0.1", 7860

with open(BASE_DIR / "data" / "banking_fraud_call_transcripts.json", encoding="utf-8") as f:
    DATASET = json.load(f)

QUESTIONS = {
    "fraud_category": {
        "type": "choice",
        "instructions": "What is the most appropriate category for the risk pattern in this banking call?",
        "criteria": {
            "legitimate": "No meaningful fraud indicator; the customer's issue appears legitimate.",
            "phishing": "A suspicious message, link, or request attempts to collect banking information.",
            "social_engineering": "A person manipulates the customer into revealing information or performing a risky action.",
            "account_takeover": "There are indicators that someone is attempting to gain or has gained unauthorized access to the customer's account.",
            "unauthorized_transaction": "The conversation indicates a transaction the customer says they did not authorize.",
            "remote_access_scam": "The customer was asked to install remote-access software or allow remote control of a device.",
        },
    },
    "risk_level": {
        "type": "score",
        "instructions": "How serious is the fraud risk described in this call?",
        "criteria": ["Low", "Medium", "High", "Critical"],
    },
    "otp_involved": {
        "type": "noul",
        "instructions": "Was an OTP or verification code requested or shared in a suspicious context?",
    },
    "unauthorized_transaction": {
        "type": "noul",
        "instructions": "Does the customer report a transaction they did not authorize?",
    },
    "social_engineering": {
        "type": "noul",
        "instructions": "Does the conversation contain social-engineering or manipulation tactics?",
    },
    "escalation_required": {
        "type": "noul",
        "instructions": "Should this case be escalated for fraud or security review?",
    },
}

AGENT = None
AGENT_LOCK = threading.Lock()


def get_agent():
    global AGENT
    if AGENT is None:
        AGENT = laya.load("convaiinnovations/laya")
    return AGENT


def pct(x):
    return f"{float(x) * 100:.1f}%"


def yes_no(answer):
    return "YES" if answer.get("noul", 0.0) >= 0.5 else "NO"


def distribution(answer, legend=None):
    legend = legend or {}
    return [
        {
            "label": legend.get(str(key), str(key).replace("_", " ").title()),
            "value": float(value),
        }
        for key, value in answer.get("probabilities", {}).items()
    ]


def analyze(transcript):
    if not transcript or not transcript.strip():
        raise ValueError("Empty transcript.")
    state = {
        "subject": "Banking customer-agent call",
        "body": transcript.strip(),
    }
    with AGENT_LOCK:
        result = get_agent().system_one(state, QUESTIONS)
    return result, build_summary(result)


def build_summary(result):
    a = result["answers"]
    risk = a["risk_level"]
    score = float(risk.get("score", 0))
    labels = ["Low", "Medium", "High", "Critical"]
    risk_label = labels[max(0, min(3, round(score)))]
    escalation = a["escalation_required"]
    return {
        "fraud_category": a["fraud_category"].get("choice", "Unknown").replace("_", " ").title(),
        "fraud_distribution": distribution(a["fraud_category"]),
        "risk_label": risk_label,
        "risk_score": round(score, 3),
        "risk_distribution": distribution(risk, risk.get("legend", {})),
        "otp": yes_no(a["otp_involved"]),
        "otp_prob": pct(a["otp_involved"].get("noul", 0)),
        "unauthorized_transaction": yes_no(a["unauthorized_transaction"]),
        "unauthorized_transaction_prob": pct(a["unauthorized_transaction"].get("noul", 0)),
        "social_engineering": yes_no(a["social_engineering"]),
        "social_engineering_prob": pct(a["social_engineering"].get("noul", 0)),
        "escalate": escalation.get("noul", 0) >= 0.5,
    }


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    def _send_bytes(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code, payload):
        self._send_bytes(code, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    def _static(self, filename):
        path = STATIC_DIR / filename
        if not path.is_file():
            self._send_json(404, {"error": "Not found"})
            return
        content_type = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self._send_bytes(200, content_type, path.read_bytes())

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._static("index.html")
        elif path == "/style.css":
            self._static("style.css")
        elif path == "/api/samples":
            self._send_json(200, [
                {"index": i, "id": x["id"], "title": x["title"]}
                for i, x in enumerate(DATASET)
            ])
        elif path.startswith("/api/samples/"):
            try:
                sample = DATASET[int(path.rsplit("/", 1)[1])]
                self._send_json(200, {"transcript": sample["transcript"]})
            except (ValueError, IndexError):
                self._send_json(404, {"error": "Unknown sample"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/analyze":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            transcript = data.get("transcript", "")
            if not transcript.strip():
                self._send_json(400, {"ok": False, "error": "Empty transcript."})
                return
            result, summary = analyze(transcript)
            self._send_json(200, {"ok": True, "summary": summary, "raw": result})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Laya Banking Fraud Risk Engine -> http://{HOST}:{PORT}")
    print("Model loads on the first analysis.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
