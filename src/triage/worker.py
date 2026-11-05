"""python -m triage.worker. A separate process, so slow APIs never delay webhook replies."""

import logging
import time

from triage.config import Settings
from triage.pipeline import run_once
from triage.wiring import build_deps


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    deps, _ = build_deps(Settings())
    logging.info("Worker started")
    while True:
        if not run_once(deps):
            time.sleep(1.0)


if __name__ == "__main__":
    main()
