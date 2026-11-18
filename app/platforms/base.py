from abc import ABC, abstractmethod

import httpx

from app.schemas import PostingResult


class Publisher(ABC):

    @abstractmethod
    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient
    ) -> PostingResult:
        """Publish a message and return a standardized result."""