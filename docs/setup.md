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

HubSpot stopped allowing new legacy public apps in June 2026, so the OAuth app is created with its CLI. Its settings live in `hubspot/`, with no secrets in them.

1. Create a free developer account and a test account at [developers.hubspot.com](https://developers.hubspot.com).
2. Install the CLI with `npm install -g @hubspot/cli@latest`, then sign in with `hs account auth`. It asks for a **personal access key**, not a service key.
3. From the `hubspot/` folder, upload the app with `hs project upload --force-create`.
4. In HubSpot, open the project and its app, then the **Auth** tab. Save `HUBSPOT_CLIENT_ID` and `HUBSPOT_CLIENT_SECRET` with the script. A value starting with `pat-` is an access token, which is the wrong value.
5. With the API running, connect:

```bash
uv run python -m triage.connect_hubspot
```

## 5. Slack

1. Create a free workspace, then a channel for triage.
2. Slack needs a public address to deliver button clicks, so start a tunnel to port 3000, for example with `cloudflared tunnel --url http://localhost:3000`. The address changes on each restart, so update the app's Request URL under **Interactivity & Shortcuts** to match. Stop the tunnel when you finish.
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

Add `--risky` to send a very large deal that waits for approval in Slack. The samples use reserved `example.com` and `example.org` addresses because HubSpot rejects the `.example` domain.

Inspect any item's audit trail:

```bash
uv run python -m triage.trace ITEM_ID
```

To retry an item that failed, after fixing the cause (Slack also posts an alert with this command):

```bash
uv run python -m triage.requeue ITEM_ID
```

Or run the API and worker together in Docker:

```bash
docker compose up --build
```

## 7. Evals

Tune on the dev split (about 4 minutes). Run `--split all` (about 12 minutes) only once the prompt is final. Runs resume if interrupted.

```bash
uv run --env-file .env.local python -m triage.evals.run
```
