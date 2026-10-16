from laya import Router
import json

router = Router()

state = {
    "subject": "Duplicate charge",
    "body": "I was charged twice for the same purchase. Please refund one of the charges."
}

questions = {
    "department": {
        "type": "choice",
        "instructions": "Which department should handle this request?",
        "criteria": {
            "billing": "Payments, refunds, invoices",
            "technical": "Technical problems, bugs, outages",
            "sales": "New purchases and pricing"
        }
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is this request?",
        "criteria": [
            "Not urgent",
            "Needs attention soon",
            "Critical"
        ]
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "Is the customer requesting a refund?"
    }
}

result = router.predict(state, questions)

json_string = json.dumps(result, indent=2)

print(json_string)