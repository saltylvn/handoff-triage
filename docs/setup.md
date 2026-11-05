# Setup

The demo and tests need no accounts. These steps connect the real services. Use free test accounts, not a workspace with real customers.

## 1. Install

```bash
brew install uv
```

```bash
uv sync
```

## 2. Gemini key

Create a key at [Google AI Studio](https://aistudio.google.com/apikey), ideally in a project of its own, then save it. The script hides what you paste and keeps it out of shell history.

```bash
sh scripts/set-secret.sh GEMINI_API_KEY
```

## 3. Local secrets

Generate two values with `openssl rand -hex 32` (webhook) and `openssl rand -base64 32` (token encryption), and save each one.

```bash
sh scripts/set-secret.sh WEBHOOK_SECRET
```

```bash
sh scripts/set-secret.sh TOKEN_ENCRYPTION_KEY
```

## 4. HubSpot (OAuth)

1. Create a free developer account and a test account at [developers.hubspot.com](https://developers.hubspot.com).
2. Create an app with the redirect URL `http://localhost:3000/oauth/hubspot/callback` and the scopes `crm.objects.contacts.read` and `crm.objects.contacts.write`.
3. Save `HUBSPOT_CLIENT_ID` and `HUBSPOT_CLIENT_SECRET` with the script.
4. With the API running, connect:

```bash
uv run python -m triage.connect_hubspot
```

## 5. Slack

1. Create a free workspace, then a channel for triage.
2. Slack needs a public address to deliver button clicks, so start a tunnel to port 3000, for example with `cloudflared tunnel --url http://localhost:3000`.
3. At [api.slack.com/apps](https://api.slack.com/apps), choose **Create New App > From a manifest** and paste `slack-app-manifest.yaml`, using your tunnel's address.
4. Install the app, invite it to the channel, and save `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_CHANNEL_ID` and `SLACK_APPROVER_IDS` (your member ID).

## 6. Run

Each of these runs in its own terminal.

```bash
uv run uvicorn triage.asgi:app --port 3000
```

```bash
uv run python -m triage.worker
```

```bash
uv run python -m triage.send_sample
```

Inspect any item's audit trail:

```bash
uv run python -m triage.trace ITEM_ID
```

## 7. Evals

Tune on the dev split (about 4 minutes). Run `--split all` (about 12 minutes) only once the prompt is final. Runs resume if interrupted.

```bash
uv run --env-file .env.local python -m triage.evals.run
```
