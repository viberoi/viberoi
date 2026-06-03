"""Notification service entry — runs the SQS consumer loop."""

import asyncio

from viberoi_shared.logging import configure_logging, get_logger

from notification.app.consumer import run

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    logger.info("notification_main_start")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("notification_main_interrupted")


if __name__ == "__main__":
    main()
