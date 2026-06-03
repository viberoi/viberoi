"""Process entry for `python -m integration.app.consumer_main`.

Launched alongside uvicorn by `entrypoint.sh`. Keeps the consumer's
process boundary separate from the FastAPI worker so a crash in one
doesn't take the other down (ECS notices either exit and restarts).
"""

from __future__ import annotations

import asyncio

from integration.app.consumer import run
from viberoi_shared.logging import configure_logging


def main() -> None:
    configure_logging()
    asyncio.run(run())


if __name__ == "__main__":
    main()
