
"""Bluesky publishing adapter using AT Protocol XRPC."""

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.platforms.base import Publisher
from app.schemas import PostingResult
from app.validators import URL_PATTERN, validate_single_cta


class BlueskyPublisher(Publisher):

    def __init__(
        self,
        handle: str,
        app_password: str,
        pds_url: str = "https://bsky.social",
    ):
        self.handle = handle.strip().lstrip("@")
        self.app_password = app_password.strip()
        self.pds_url = pds_url.rstrip("/")

    def _failed(self, reason: str) -> PostingResult:
        return PostingResult(
            platform="Bluesky",
            status="failed",
            error=reason,
        )

    def _link_facet(self, message: str) -> dict:
        """Build a clickable URL facet using UTF-8 offsets."""

        match = URL_PATTERN.search(message)
        if match is None:
            raise ValueError("CTA URL not found")

        url = match.group().rstrip(".!?:)]}")
        start = match.start()
        end = start + len(url)

        return {
            "index": {
                "byteStart": len(message[:start].encode("utf-8")),
                "byteEnd": len(message[:end].encode("utf-8")),
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url,
                }
            ],
        }

    async def publish(
        self,
        message: str,
        client: httpx.AsyncClient,
    ) -> PostingResult:

        if not self.handle or not self.app_password:
            return self._failed(
                "Bluesky credentials are not configured"
            )

        pds = urlsplit(self.pds_url)

        if (
            pds.scheme != "https"
            or not pds.hostname
            or pds.username is not None
            or pds.password is not None
            or pds.path not in ("", "/")
            or pds.query
            or pds.fragment
        ):
            return self._failed("Invalid Bluesky PDS URL")

        try:
            validate_single_cta(message)
            facet = self._link_facet(message)
        except ValueError:
            return self._failed("Invalid or missing CTA URL")

        # Step 1: Authenticate with the user's PDS.
        try:
            auth_response = await client.post(
                f"{self.pds_url}/xrpc/com.atproto.server.createSession",
                json={
                    "identifier": self.handle,
                    "password": self.app_password,
                },
                timeout=10.0,
            )
        except httpx.TimeoutException:
            return self._failed(
                "Bluesky authentication timed out"
            )
        except httpx.RequestError:
            return self._failed(
                "Bluesky authentication connection failed"
            )

        if auth_response.status_code != 200:
            return self._failed(
                f"Bluesky authentication failed "
                f"(HTTP {auth_response.status_code})"
            )

        try:
            session = auth_response.json()
        except ValueError:
            return self._failed(
                "Bluesky returned invalid authentication JSON"
            )

        if not isinstance(session, dict):
            return self._failed("Invalid Bluesky session response")

        access_token = session.get("accessJwt")
        did = session.get("did")

        if (
            not isinstance(access_token, str)
            or not access_token
            or not isinstance(did, str)
            or not did.startswith("did:")
        ):
            return self._failed("Incomplete Bluesky session")

        # Step 2: Create a public feed post.
        created_at = datetime.now(timezone.utc)

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": (
                created_at.isoformat().replace("+00:00", "Z")
            ),
            "facets": [facet],
        }

        try:
            response = await client.post(
                f"{self.pds_url}/xrpc/com.atproto.repo.createRecord",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                timeout=10.0,
            )
        except httpx.TimeoutException:
            return self._failed(
                "Bluesky publishing timed out; "
                "publication is uncertain"
            )
        except httpx.RequestError:
            return self._failed(
                "Bluesky publishing connection failed; "
                "publication is uncertain"
            )

        if response.status_code not in (200, 201):
            return self._failed(
                f"Bluesky publishing failed "
                f"(HTTP {response.status_code})"
            )

        try:
            data = response.json()
        except ValueError:
            return self._failed(
                "Bluesky creation response was invalid"
            )

        if not isinstance(data, dict):
            return self._failed("Invalid Bluesky post response")

        uri = data.get("uri")
        cid = data.get("cid")

        if not isinstance(uri, str) or not isinstance(cid, str) or not cid:
            return self._failed(
                "Bluesky did not confirm a created post"
            )

        expected_prefix = f"at://{did}/app.bsky.feed.post/"

        if not uri.startswith(expected_prefix):
            return self._failed("Unexpected Bluesky post URI")

        rkey = uri[len(expected_prefix):]

        if not re.fullmatch(r"[A-Za-z0-9._~-]+", rkey):
            return self._failed("Invalid Bluesky record key")

        post_url = f"https://bsky.app/profile/{did}/post/{rkey}"

        return PostingResult(
            platform="Bluesky",
            status="success",
            posted_url=post_url,
            public_access=True,
            date=created_at.date().isoformat(),
            time=created_at.strftime("%H:%M:%S"),
            error=None,
        )
