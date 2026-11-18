
"""Discord webhook publishing adapter."""

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult


class DiscordPublisher(Publisher):

    def __init__(self, webhook_url: str, guild_id: str = ""):
        self.webhook_url = webhook_url.strip()
        self.guild_id = guild_id.strip()

    def _failed(self, reason: str) -> PostingResult:
        return PostingResult(
            platform="Discord",
            status="failed",
            error=reason
        )

    def _valid_webhook(self) -> bool:
        """Allow only official Discord webhook endpoints."""

        try:
            url = urlsplit(self.webhook_url)
        except ValueError:
            return False

        valid_path = re.fullmatch(
            r"/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9._-]+/?",
            url.path
        )

        return (
            url.scheme == "https"
            and url.netloc.lower() in {
                "discord.com", "discordapp.com"
            }
            and valid_path is not None
            and not url.query
            and not url.fragment
        )

    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient
    ) -> PostingResult:

        if not self.webhook_url:
            return self._failed(
                "Discord webhook URL is not configured"
            )

        if not self._valid_webhook():
            return self._failed(
                "Invalid Discord webhook URL"
            )

        if self.guild_id and not self.guild_id.isdigit():
            return self._failed(
                "Discord Guild ID must be numeric"
            )

        try:
            response = await client.post(
                self.webhook_url,
                params={"wait": "true"},
                json={
                    "content": message,
                    "allowed_mentions": {"parse": []}
                },
                timeout=10.0
            )

        except httpx.TimeoutException:
            return self._failed(
                "Discord request timed out; publication is uncertain"
            )

        except httpx.RequestError:
            return self._failed(
                "Discord connection failed; publication is uncertain"
            )

        if response.status_code != 200:
            errors = {
                401: "Discord webhook authentication failed (401)",
                403: "Discord publishing permission denied (403)",
                404: "Discord webhook not found (404)",
                429: "Discord rate limit reached (429)"
            }

            return self._failed(
                errors.get(
                    response.status_code,
                    f"Discord returned HTTP {response.status_code}; "
                    "publication not confirmed"
                )
            )

        try:
            data = response.json()
        except ValueError:
            return self._failed(
                "Discord returned invalid JSON; publication unconfirmed"
            )

        if not isinstance(data, dict):
            return self._failed(
                "Discord returned an unexpected response"
            )

        message_id = data.get("id")
        channel_id = data.get("channel_id")
        timestamp = data.get("timestamp")

        if not (
            isinstance(message_id, str)
            and message_id.isdigit()
            and isinstance(channel_id, str)
            and channel_id.isdigit()
            and isinstance(timestamp, str)
        ):
            return self._failed(
                "Discord response missing valid message details"
            )

        try:
            dt = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                raise ValueError("Missing timezone")

            dt = dt.astimezone(timezone.utc)

        except ValueError:
            return self._failed(
                "Discord returned an invalid timestamp"
            )

        post_url = None

        if self.guild_id:
            post_url = (
                f"https://discord.com/channels/"
                f"{self.guild_id}/{channel_id}/{message_id}"
            )

        return PostingResult(
            platform="Discord",
            status="success",
            posted_url=post_url,
            public_access=False,
            date=dt.date().isoformat(),
            time=dt.strftime("%H:%M:%S"),
            error=None
        )
