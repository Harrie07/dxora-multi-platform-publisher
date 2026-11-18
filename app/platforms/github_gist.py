
"""GitHub Gist publishing adapter."""

from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult


class GitHubGistPublisher(Publisher):

    def __init__(self, token: str):
        self.token = token.strip()

    def _failed(self, reason: str) -> PostingResult:
        return PostingResult(
            platform="GitHub Gist",
            status="failed",
            error=reason,
        )

    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient,
    ) -> PostingResult:

        if not self.token:
            return self._failed("GitHub token is not configured")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }

        payload = {
            "description": "Dxora multi-platform publishing demo",
            "public": True,
            "files": {
                "dxora-post.md": {
                    "content": message
                }
            }
        }

        try:
            response = await client.post(
                "https://api.github.com/gists",
                headers=headers,
                json=payload,
                timeout=10.0,
            )

        except httpx.TimeoutException:
            return self._failed(
                "GitHub request timed out; publication is uncertain"
            )

        except httpx.RequestError:
            return self._failed(
                "GitHub connection failed; publication is uncertain"
            )

        if response.status_code != 201:
            errors = {
                401: "GitHub authentication failed (401)",
                403: "GitHub permission or rate-limit error (403)",
                422: "GitHub rejected the Gist content (422)",
                429: "GitHub rate limit reached (429)",
            }

            return self._failed(
                errors.get(
                    response.status_code,
                    f"GitHub returned HTTP {response.status_code}"
                )
            )

        try:
            data = response.json()
        except ValueError:
            return self._failed(
                "GitHub returned invalid JSON; creation unconfirmed"
            )

        if not isinstance(data, dict):
            return self._failed("Invalid GitHub response")

        gist_id = data.get("id")
        post_url = data.get("html_url")
        created_at = data.get("created_at")

        if not all(isinstance(v, str) and v for v in (
            gist_id, post_url, created_at
        )):
            return self._failed(
                "GitHub response missing Gist creation details"
            )

        parsed = urlsplit(post_url)

        if (
            parsed.scheme != "https"
            or parsed.hostname != "gist.github.com"
            or not parsed.path.rstrip("/").endswith(f"/{gist_id}")
        ):
            return self._failed(
                "GitHub returned an unexpected Gist URL"
            )

        try:
            dt = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                raise ValueError("Missing timezone")

            dt = dt.astimezone(timezone.utc)

        except ValueError:
            return self._failed(
                "GitHub returned an invalid creation timestamp"
            )

        return PostingResult(
            platform="GitHub Gist",
            status="success",
            posted_url=post_url,
            public_access=data.get("public") is True,
            date=dt.date().isoformat(),
            time=dt.strftime("%H:%M:%S"),
            error=None,
        )
