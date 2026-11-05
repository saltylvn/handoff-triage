"""python -m triage.send_sample [--risky] signs and posts one test message to the local webhook.

Uses reserved example.com and example.org addresses: HubSpot rejects the .example domain."""

import json
import sys
import time

import httpx

from triage.config import Settings
from triage.infra.signature import sign

ROUTINE = {
    "email": "morgan.reyes@example.com",
    "name": "Morgan Reyes",
    "company": "Harborline HVAC",
    "subject": "Pricing for 40 technicians",
    "message": "We run 40 technicians and want a demo and pricing this month.",
}

# A very large deal, so the routing rules send it to a person.
RISKY = {
    "email": "riley.chen@example.org",
    "name": "Riley Chen",
    "company": "Ironbridge Services",
    "subject": "Enterprise rollout",
    "message": "Ironbridge Services has 1,200 technicians and a budget near $250,000. "
    "We need SSO and a security review before rollout.",
}


def main() -> None:
    settings = Settings()
    body = json.dumps(RISKY if "--risky" in sys.argv else ROUTINE).encode()
    timestamp = str(int(time.time()))
    response = httpx.post(
        f"{settings.public_base_url.rstrip('/')}/webhooks/inbound",
        content=body,
        headers={
            "content-type": "application/json",
            "x-timestamp": timestamp,
            "x-signature": sign(settings.webhook_secret, timestamp, body),
        },
    )
    print(response.status_code, response.text)


if __name__ == "__main__":
    main()
