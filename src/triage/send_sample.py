"""python -m triage.send_sample signs and posts one test submission to the local webhook."""

import json
import time

import httpx

from triage.config import Settings
from triage.infra.signature import sign


def main() -> None:
    settings = Settings()
    body = json.dumps(
        {
            "email": "morgan@harborline-hvac.example",
            "name": "Morgan Reyes",
            "company": "Harborline HVAC",
            "subject": "Pricing for 40 technicians",
            "message": "We run 40 technicians and want a demo and pricing this month.",
        }
    ).encode()
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
