"""All SQL lives here. A new short-lived connection per call keeps it safe across the API's threads
and the separate worker process; WAL mode lets them read and write at the same time."""

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from typing import Any

from pydantic import BaseModel

from triage.domain.models import Item, Submission


class StepRow(BaseModel):
    status: str
    result: str | None
    started_at: float


class TokenRow(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: float


def _dump(detail: dict[str, Any]) -> str:
    return json.dumps(detail, sort_keys=True)


class Store:
    def __init__(self, path: str) -> None:
        self._path = path
        self._migrate()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _migrate(self) -> None:
        files = sorted(
            (f for f in resources.files("triage.migrations").iterdir() if f.name.endswith(".sql")),
            key=lambda f: f.name,
        )
        conn = sqlite3.connect(self._path, timeout=5.0)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            for number, file in enumerate(files, start=1):
                if number > version:
                    conn.executescript(
                        f"BEGIN;{file.read_text()};PRAGMA user_version={number};COMMIT;"
                    )
        finally:
            conn.close()

    @staticmethod
    def _log(
        conn: sqlite3.Connection,
        item_id: str,
        now: float,
        kind: str,
        actor: str,
        detail: dict[str, Any],
    ) -> None:
        conn.execute(
            "INSERT INTO decisions (item_id, at, kind, actor, detail) VALUES (?,?,?,?,?)",
            (item_id, now, kind, actor, _dump(detail)),
        )

    def log(self, item_id: str, now: float, kind: str, actor: str, detail: dict[str, Any]) -> None:
        with self._tx() as conn:
            self._log(conn, item_id, now, kind, actor, detail)

    def enqueue(self, key: str, submission: Submission, now: float) -> tuple[str, bool]:
        """Returns (item id, created). The UNIQUE key makes a replayed webhook a no-op."""
        with self._tx() as conn:
            row = conn.execute("SELECT id FROM items WHERE idempotency_key = ?", (key,)).fetchone()
            if row:
                self._log(conn, row["id"], now, "duplicate_ignored", "system", {"key": key})
                return str(row["id"]), False
            item_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO items (id, idempotency_key, payload, status, next_attempt_at,
                   created_at, updated_at) VALUES (?,?,?,'queued',?,?,?)""",
                (item_id, key, submission.model_dump_json(), now, now, now),
            )
            self._log(conn, item_id, now, "received", "system", {"key": key})
            return item_id, True

    @staticmethod
    def _item(row: sqlite3.Row) -> Item:
        return Item(
            id=row["id"],
            payload=Submission.model_validate_json(row["payload"]),
            status=row["status"],
            attempts=row["attempts"],
            approved_by=row["approved_by"],
        )

    def get_item(self, item_id: str) -> Item | None:
        with self._tx() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            return self._item(row) if row else None

    def claim_next(self, now: float, lease_s: float) -> Item | None:
        """Atomically takes one ready item. An expired lease means a worker died mid-item."""
        with self._tx() as conn:
            row = conn.execute(
                """UPDATE items SET status='processing', lease_until=?, attempts=attempts+1,
                   updated_at=?
                   WHERE id = (SELECT id FROM items
                     WHERE (status='queued' AND next_attempt_at <= ?)
                        OR (status='processing' AND lease_until < ?)
                     ORDER BY next_attempt_at LIMIT 1)
                   RETURNING *""",
                (now + lease_s, now, now, now),
            ).fetchone()
            return self._item(row) if row else None

    def get_step(self, item_id: str, step: str) -> StepRow | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT status, result, started_at FROM steps WHERE item_id=? AND step=?",
                (item_id, step),
            ).fetchone()
            return StepRow(**dict(row)) if row else None

    def start_step(self, item_id: str, step: str, now: float) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO steps (item_id, step, status, started_at) "
                "VALUES (?,?,'started',?)",
                (item_id, step, now),
            )

    def complete_step(
        self,
        item_id: str,
        step: str,
        result_json: str,
        now: float,
        decision: tuple[str, dict[str, Any]] | None,
    ) -> None:
        """The result and its log entry commit together: never one without the other."""
        with self._tx() as conn:
            conn.execute(
                "UPDATE steps SET status='done', result=?, completed_at=? "
                "WHERE item_id=? AND step=?",
                (result_json, now, item_id, step),
            )
            if decision:
                self._log(conn, item_id, now, decision[0], "system", decision[1])

    def set_status(self, item_id: str, status: str, now: float, kind: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE items SET status=?, lease_until=NULL, updated_at=? WHERE id=?",
                (status, now, item_id),
            )
            self._log(conn, item_id, now, kind, "system", {"status": status})

    def retry_later(self, item_id: str, at: float, error: str, now: float) -> None:
        with self._tx() as conn:
            conn.execute(
                """UPDATE items SET status='queued', next_attempt_at=?, lease_until=NULL,
                   last_error=?, updated_at=? WHERE id=?""",
                (at, error, now, item_id),
            )
            self._log(conn, item_id, now, "retry_scheduled", "system", {"error": error, "at": at})

    def dead_letter(self, item_id: str, error: str, now: float) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE items SET status='failed', lease_until=NULL, last_error=?, updated_at=? "
                "WHERE id=?",
                (error, now, item_id),
            )
            self._log(conn, item_id, now, "dead_lettered", "system", {"error": error})

    def resolve_approval(self, item_id: str, approved: bool, actor: str, now: float) -> bool:
        """Compare-and-set: only the first click wins, so a double-click can't act twice."""
        with self._tx() as conn:
            status = "queued" if approved else "rejected"
            changed = conn.execute(
                """UPDATE items SET status=?, approved_by=?, attempts=0, next_attempt_at=?,
                   updated_at=? WHERE id=? AND status='awaiting_approval'""",
                (status, actor if approved else None, now, now, item_id),
            ).rowcount
            if changed:
                kind = "human_approved" if approved else "human_rejected"
                self._log(conn, item_id, now, kind, actor, {})
            return bool(changed)

    def trace(self, item_id: str) -> list[dict[str, Any]]:
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT at, kind, actor, detail FROM decisions WHERE item_id=? ORDER BY seq",
                (item_id,),
            ).fetchall()
            return [
                {
                    "at": r["at"],
                    "kind": r["kind"],
                    "actor": r["actor"],
                    "detail": json.loads(r["detail"]),
                }
                for r in rows
            ]

    def save_tokens(
        self, provider: str, access_sealed: str, refresh_sealed: str, expires_at: float
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO oauth_tokens VALUES (?,?,?,?)",
                (provider, access_sealed, refresh_sealed, expires_at),
            )

    def load_tokens(self, provider: str) -> TokenRow | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE provider=?",
                (provider,),
            ).fetchone()
            return TokenRow(**dict(row)) if row else None

    def save_oauth_state(self, state: str, expires_at: float) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO oauth_states VALUES (?,?)",
                (hashlib.sha256(state.encode()).hexdigest(), expires_at),
            )

    def consume_oauth_state(self, state: str, now: float) -> bool:
        """Single use and expiring. Stored only as a hash."""
        with self._tx() as conn:
            changed = conn.execute(
                "DELETE FROM oauth_states WHERE state_hash=? AND expires_at>=?",
                (hashlib.sha256(state.encode()).hexdigest(), now),
            ).rowcount
            return bool(changed)
