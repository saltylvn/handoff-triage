CREATE TABLE items (
  id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('queued','processing','awaiting_approval','done','discarded','rejected','failed')),
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at REAL NOT NULL,
  lease_until REAL,
  approved_by TEXT,
  last_error TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX items_ready ON items (status, next_attempt_at);

-- One row per side effect or decision. A retry skips anything already 'done'.
CREATE TABLE steps (
  item_id TEXT NOT NULL REFERENCES items (id) ON DELETE CASCADE,
  step TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('started','done')),
  result TEXT,
  started_at REAL NOT NULL,
  completed_at REAL,
  PRIMARY KEY (item_id, step)
);

-- The audit trail. Append-only, enforced by the database rather than by convention.
CREATE TABLE decisions (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL,
  at REAL NOT NULL,
  kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  detail TEXT NOT NULL
);
CREATE INDEX decisions_item ON decisions (item_id, seq);
CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decisions
BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decisions
BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;

CREATE TABLE oauth_tokens (
  provider TEXT PRIMARY KEY,
  access_token TEXT NOT NULL,   -- encrypted
  refresh_token TEXT NOT NULL,  -- encrypted
  expires_at REAL NOT NULL
);

CREATE TABLE oauth_states (
  state_hash TEXT PRIMARY KEY,
  expires_at REAL NOT NULL
);
