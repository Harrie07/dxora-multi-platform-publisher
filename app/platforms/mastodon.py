
"""Mastodon status publishing adapter."""

from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult


class MastodonPublisher(Publisher):

    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.strip().rstrip("/")
        self.access_token = access_token.strip()

    def _failed(self, reason: str) -> PostingResult:
        return PostingResult(
            platform="Mastodon",
            status="failed",
            error=reason
        )

    def _valid_instance(self) -> bool:
        try:
            parsed = urlsplit(self.base_url)

            return (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            return False

    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient
    ) -> PostingResult:

        if not self.access_token:
            return self._failed(
                "Mastodon access token is not configured"
            )

        if not self._valid_instance():
            return self._failed(
                "Invalid Mastodon instance URL"
            )

        endpoint = f"{self.base_url}/api/v1/statuses"

        try:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json"
                },
                data={
                    "status": message,
                    "visibility": "public"
                },
                timeout=10.0
            )

        except httpx.TimeoutException:
            return self._failed(
                "Mastodon timed out; publication is uncertain"
            )

        except httpx.RequestError:
            return self._failed(
                "Mastodon connection failed; publication is uncertain"
            )

        if response.status_code not in (200, 201):
            errors = {
                401: "Mastodon authentication failed (401)",
                403: "Mastodon publishing permission denied (403)",
                404: "Mastodon endpoint not found (404)",
                422: "Mastodon rejected the post content (422)",
                429: "Mastodon rate limit reached (429)"
            }

            return self._failed(
                errors.get(
                    response.status_code,
                    f"Mastodon returned HTTP {response.status_code}"
                )
            )

        try:
            data = response.json()
        except ValueError:
            return self._failed(
                "Mastodon returned invalid JSON; "
                "publication may have succeeded"
            )

        if not isinstance(data, dict):
            return self._failed(
                "Unexpected Mastodon response"
            )

        status_id = data.get("id")
        created_at = data.get("created_at")
        visibility = data.get("visibility")
        post_url = data.get("url")

        if (
            not isinstance(status_id, str)
            or not status_id
            or not isinstance(created_at, str)
            or not isinstance(visibility, str)
        ):
            return self._failed(
                "Mastodon did not return complete status details"
            )

        try:
            dt = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                raise ValueError("Timestamp has no timezone")

            dt = dt.astimezone(timezone.utc)

        except ValueError:
            return self._failed(
                "Mastodon returned an invalid timestamp"
            )

        # Mastodon's URL property can legitimately be null.
        valid_post_url = None

        if isinstance(post_url, str):
            try:
                parsed = urlsplit(post_url)
                if parsed.scheme == "https" and parsed.hostname:
                    valid_post_url = post_url
            except ValueError:
                pass

        is_public = (
            visibility == "public"
            and valid_post_url is not None
        )

        return PostingResult(
            platform="Mastodon",
            status="success",
            posted_url=valid_post_url,
            public_access=is_public,
            date=dt.date().isoformat(),
            time=dt.strftime("%H:%M:%S"),
            error=None
        )
