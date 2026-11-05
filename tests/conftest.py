from dataclasses import dataclass
from pathlib import Path

import pytest

from triage.domain.routing import Policy
from triage.fakes import FakeChat, FakeClassifier, FakeCrm, FakeDomains
from triage.pipeline import Deps
from triage.store import Store


@dataclass
class World:
    deps: Deps
    store: Store
    crm: FakeCrm
    chat: FakeChat
    clock: list[float]


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(str(tmp_path / "test.sqlite"))


@pytest.fixture
def world(store: Store) -> World:
    return make_world(store, FakeClassifier())


def make_world(
    store: Store, classifier: FakeClassifier, domains: FakeDomains | None = None
) -> World:
    clock = [1_000_000.0]
    crm, chat = FakeCrm(), FakeChat()
    deps = Deps(
        store=store,
        classifier=classifier,
        domains=domains or FakeDomains(),
        crm=crm,
        chat=chat,
        policy=Policy(),
        now=lambda: clock[0],
    )
    return World(deps, store, crm, chat, clock)
