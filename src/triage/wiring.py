"""Builds the real dependency graph, used by the API, the worker and the CLI commands."""

import time

import httpx

from triage.adapters.gemini import GeminiClassifier
from triage.adapters.hubspot import HubSpotAuth, HubSpotCrm
from triage.adapters.rdap import RdapDomainInfo
from triage.adapters.slack import SlackChat
from triage.config import Settings
from triage.domain.routing import Policy
from triage.pipeline import Deps
from triage.store import Store


def build_auth(settings: Settings, client: httpx.Client, store: Store) -> HubSpotAuth:
    return HubSpotAuth(
        client,
        store,
        settings.hubspot_client_id,
        settings.hubspot_client_secret,
        settings.hubspot_redirect_uri,
        settings.token_encryption_key,
    )


def build_deps(settings: Settings) -> tuple[Deps, HubSpotAuth]:
    client = httpx.Client(headers={"User-Agent": "multi_agent_triage/0.1"}, follow_redirects=False)
    rdap_client = httpx.Client(
        headers={"User-Agent": "multi_agent_triage/0.1"}, follow_redirects=True
    )  # rdap.org redirects to the registry for that domain
    store = Store(settings.database_path)
    auth = build_auth(settings, client, store)
    deps = Deps(
        store=store,
        classifier=GeminiClassifier(client, settings.gemini_api_key, settings.gemini_model),
        domains=RdapDomainInfo(rdap_client),
        crm=HubSpotCrm(client, auth),
        chat=SlackChat(client, settings.slack_bot_token, settings.slack_channel_id),
        policy=Policy(confidence_threshold=settings.confidence_threshold),
        now=time.time,
    )
    return deps, auth
