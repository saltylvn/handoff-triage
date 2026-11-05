"""Entry point: uvicorn triage.asgi:app --port 3000"""

import time

from triage.api import create_app
from triage.config import Settings
from triage.wiring import build_deps

_settings = Settings()
_deps, _auth = build_deps(_settings)

app = create_app(
    store=_deps.store,
    chat=_deps.chat,
    auth=_auth,
    webhook_secret=_settings.webhook_secret,
    slack_signing_secret=_settings.slack_signing_secret,
    approvers=_settings.approvers,
    now=time.time,
)
