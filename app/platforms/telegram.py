"""Telegram Bot API publisher."""

from datetime import datetime, timezone

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult


class TelegramPublisher(Publisher):

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()

    def _failed(self, reason: str) -> PostingResult:
        return PostingResult(
            platform="Telegram",
            status="failed",
            error=reason
        )

    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient
    ) -> PostingResult:

        if not self.bot_token or not self.chat_id:
            return self._failed(
                "Telegram credentials or channel are not configured"
            )

        url = (
            f"https://api.telegram.org/"
            f"bot{self.bot_token}/sendMessage"
        )

        try:
            response = await client.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "link_preview_options": {
                        "is_disabled": True
                    }
                },
                timeout=10.0
            )

        except httpx.TimeoutException:
            return self._failed(
                "Telegram request timed out; publication is uncertain"
            )

        except httpx.RequestError:
            return self._failed(
                "Telegram connection failed; publication is uncertain"
            )

        try:
            data = response.json()
        except ValueError:
            return self._failed(
                "Telegram returned an invalid JSON response"
            )

        if (
            not isinstance(data, dict)
            or response.status_code != 200
            or data.get("ok") is not True
        ):
            if response.status_code == 401:
                return self._failed(
                    "Telegram authentication failed (401)"
                )

            if response.status_code == 403:
                return self._failed(
                    "Telegram denied posting permission (403)"
                )

            if response.status_code == 429:
                return self._failed(
                    "Telegram rate limit reached (429)"
                )

            return self._failed(
                f"Telegram rejected the request "
                f"(HTTP {response.status_code})"
            )

        result = data.get("result")

        if not isinstance(result, dict):
            return self._failed(
                "Telegram response did not contain a created message"
            )

        message_id = result.get("message_id")
        posted_at = result.get("date")
        chat = result.get("chat")

        if (
            type(message_id) is not int
            or type(posted_at) is not int
            or not isinstance(chat, dict)
        ):
            return self._failed(
                "Telegram response lacked a message ID, date, or chat"
            )

        try:
            dt = datetime.fromtimestamp(
                posted_at,
                tz=timezone.utc
            )
        except (ValueError, OverflowError, OSError):
            return self._failed(
                "Telegram returned an invalid timestamp"
            )

        username = chat.get("username")

        is_public = (
            chat.get("type") == "channel"
            and isinstance(username, str)
            and bool(username)
        )

        post_url = (
            f"https://t.me/{username}/{message_id}"
            if is_public
            else None
        )

        return PostingResult(
            platform="Telegram",
            status="success",
            posted_url=post_url,
            public_access=is_public,
            date=dt.date().isoformat(),
            time=dt.time().isoformat(timespec="seconds")
        )