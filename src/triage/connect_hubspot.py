"""python -m triage.connect_hubspot prints a one-time link to authorize HubSpot. A CLI rather than a
public /start route, so a stranger can't connect their own HubSpot account to this system."""

import secrets
import time

import httpx

from triage.config import Settings
from triage.store import Store
from triage.wiring import build_auth


def main() -> None:
    settings = Settings()
    store = Store(settings.database_path)
    state = secrets.token_urlsafe(32)
    store.save_oauth_state(state, time.time() + 600)
    url = build_auth(settings, httpx.Client(), store).authorize_url(state)
    print(f"Open this link within 10 minutes (the API must be running):\n\n{url}\n")


if __name__ == "__main__":
    main()
