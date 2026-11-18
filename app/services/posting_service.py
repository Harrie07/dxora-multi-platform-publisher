
"""Coordinate asynchronous publishing across platforms."""

import asyncio
import logging
from collections.abc import Sequence

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult


logger = logging.getLogger(__name__)


class PostingService:
    """Publish independently to multiple third-party platforms."""

    def __init__(
        self,
        publishers: Sequence[tuple[str, Publisher]]
    ):
        self.publishers = list(publishers)

    async def _publish_one(
        self,
        name: str,
        publisher: Publisher,
        message: str,
        client: httpx.AsyncClient
    ) -> PostingResult:

        try:
            result = await publisher.publish(message, client)

            if not isinstance(result, PostingResult):
                logger.error(
                    "Publisher %s returned an invalid result",
                    name
                )

                return PostingResult(
                    platform=name,
                    status="failed",
                    error="Invalid publisher response"
                )

            return result

        except Exception as exc:
            logger.error(
                "Publisher %s raised %s",
                name,
                type(exc).__name__
            )

            return PostingResult(
                platform=name,
                status="failed",
                error="Unexpected publisher error"
            )

    async def publish(
        self,
        message: str
    ) -> list[PostingResult]:

        async with httpx.AsyncClient() as client:

            tasks = [
                self._publish_one(
                    name,
                    publisher,
                    message,
                    client
                )
                for name, publisher in self.publishers
            ]

            results = await asyncio.gather(*tasks)

        return list(results)
