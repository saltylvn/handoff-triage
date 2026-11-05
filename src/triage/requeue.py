"""python -m triage.requeue <item-id> retries a failed item once its cause has been fixed."""

import os
import sys
import time

from triage.store import Store


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m triage.requeue <item-id>")
    store = Store(os.environ.get("DATABASE_PATH", "./triage.sqlite"))
    if store.requeue(sys.argv[1], "cli", time.time()):
        print("Requeued. The worker will pick it up.")
    else:
        sys.exit("No failed item has that ID.")


if __name__ == "__main__":
    main()
