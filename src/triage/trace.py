"""python -m triage.trace <item-id> prints every recorded decision for one item."""

import json
import os
import sys
from datetime import UTC, datetime

from triage.store import Store


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m triage.trace <item-id>")
    store = Store(os.environ.get("DATABASE_PATH", "./triage.sqlite"))
    for entry in store.trace(sys.argv[1]):
        when = datetime.fromtimestamp(entry["at"], UTC).isoformat(timespec="seconds")
        print(f"{when}  {entry['actor']:<16} {entry['kind']:<20} {json.dumps(entry['detail'])}")


if __name__ == "__main__":
    main()
