import httpx
import pytest
import json

from app.platforms.telegram import TelegramPublisher
from app.platforms.discord import DiscordPublisher
from app.platforms.github_gist import GitHubGistPublisher
from app.platforms.bluesky import BlueskyPublisher
from app.platforms.mastodon import MastodonPublisher


@pytest.mark.asyncio
async def test_telegram_success():

    def handler(request):
        assert request.method == "POST"

        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 42,
                    "date": 1763400000,
                    "chat": {
                        "type": "channel",
                        "username": "dxora_test"
                    }
                }
            }
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        publisher = TelegramPublisher(
            "dummy-token",
            "@dxora_test"
        )

        result = await publisher.publish(
            "Test https://example.com",
            client
        )

    assert result.status == "success"
    assert result.posted_url == "https://t.me/dxora_test/42"
    assert result.public_access is True
    assert result.error is None


@pytest.mark.asyncio
async def test_telegram_permission_failure():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            403,
            json={
                "ok": False,
                "description": "Forbidden"
            }
        )
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        publisher = TelegramPublisher(
            "dummy-token",
            "@dxora_test"
        )

        result = await publisher.publish(
            "Test https://example.com",
            client
        )

    assert result.status == "failed"
    assert result.posted_url is None
    assert "permission" in result.error


@pytest.mark.asyncio
async def test_telegram_timeout():

    def timeout(request):
        raise httpx.ConnectTimeout("timeout")

    transport = httpx.MockTransport(timeout)

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        publisher = TelegramPublisher(
            "dummy-token",
            "@dxora_test"
        )

        result = await publisher.publish(
            "Test https://example.com",
            client
        )

    assert result.status == "failed"
    assert "uncertain" in result.error


@pytest.mark.asyncio
async def test_telegram_missing_credentials():

    async with httpx.AsyncClient() as client:

        publisher = TelegramPublisher("", "")

        result = await publisher.publish(
            "Test https://example.com",
            client
        )

    assert result.status == "failed"
    assert result.posted_url is None


# ---------------- DISCORD TESTS ----------------

@pytest.mark.asyncio
async def test_discord_success():

    def handler(request):
        assert request.method == "POST"
        assert request.url.params["wait"] == "true"

        import json
        payload = json.loads(request.content)
        assert payload["allowed_mentions"]["parse"] == []

        return httpx.Response(
            200,
            json={
                "id": "123456789",
                "channel_id": "987654321",
                "timestamp": "2026-11-17T12:04:15+00:00"
            }
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        publisher = DiscordPublisher(
            "https://discord.com/api/webhooks/123/token",
            guild_id="555555555"
        )
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "success"
    assert result.posted_url == (
        "https://discord.com/channels/"
        "555555555/987654321/123456789"
    )
    assert result.public_access is False
    assert result.date == "2026-11-17"
    assert result.time == "12:04:15"
    assert result.error is None


@pytest.mark.asyncio
async def test_discord_permission_failure():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(403)
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        publisher = DiscordPublisher(
            "https://discord.com/api/webhooks/123/token"
        )
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "failed"
    assert "permission" in result.error.lower()


@pytest.mark.asyncio
async def test_discord_timeout():

    def timeout(request):
        raise httpx.ReadTimeout("Request timed out")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(timeout)
    ) as client:
        publisher = DiscordPublisher(
            "https://discord.com/api/webhooks/123/token"
        )
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "failed"
    assert "uncertain" in result.error


@pytest.mark.asyncio
async def test_discord_missing_webhook():

    async with httpx.AsyncClient() as client:
        publisher = DiscordPublisher("")
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "failed"
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_discord_invalid_webhook():

    publisher = DiscordPublisher(
        "https://example.com/api/webhooks/123/token"
    )

    async with httpx.AsyncClient() as client:
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "failed"
    assert "invalid" in result.error.lower()


@pytest.mark.asyncio
async def test_discord_no_confirmation():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(204)
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        publisher = DiscordPublisher(
            "https://discord.com/api/webhooks/123/token"
        )
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "failed"
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_discord_success_without_guild_id():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "id": "123456789",
                "channel_id": "987654321",
                "timestamp": "2026-11-17T12:04:15Z"
            }
        )
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        publisher = DiscordPublisher(
            "https://discord.com/api/webhooks/123/token"
        )
        result = await publisher.publish(
            "Test https://example.com", client
        )

    assert result.status == "success"
    assert result.posted_url is None
    assert result.public_access is False

@pytest.mark.asyncio
async def test_gist_success():

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/gists"

        return httpx.Response(
            201,
            json={
                "id": "abc123",
                "html_url": "https://gist.github.com/testuser/abc123",
                "public": True,
                "created_at": "2026-11-17T14:00:00Z",
            }
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await GitHubGistPublisher(
            "dummy-token"
        ).publish("Test https://example.com", client)

    assert result.status == "success"
    assert result.posted_url == (
        "https://gist.github.com/testuser/abc123"
    )
    assert result.public_access is True
    assert result.error is None


@pytest.mark.asyncio
async def test_gist_invalid_token():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(401)
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await GitHubGistPublisher(
            "invalid-token"
        ).publish("Test https://example.com", client)

    assert result.status == "failed"
    assert "authentication" in result.error


@pytest.mark.asyncio
async def test_gist_missing_token():

    async with httpx.AsyncClient() as client:
        result = await GitHubGistPublisher(
            ""
        ).publish("Test https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_gist_timeout():

    def timeout(request):
        raise httpx.ReadTimeout("Timed out")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(timeout)
    ) as client:
        result = await GitHubGistPublisher(
            "dummy-token"
        ).publish("Test https://example.com", client)

    assert result.status == "failed"
    assert "uncertain" in result.error


@pytest.mark.asyncio
async def test_gist_missing_response_details():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            201,
            json={"id": "abc123"}
        )
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await GitHubGistPublisher(
            "dummy-token"
        ).publish("Test https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


# ---------------- BLUESKY TESTS ----------------



@pytest.mark.asyncio
async def test_bluesky_success():

    did = "did:plc:test123"
    message = "✨ Explore https://example.com"

    def handler(request):
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={
                    "accessJwt": "mock-access-token",
                    "did": did,
                    "handle": "test.bsky.social",
                },
            )

        assert request.url.path.endswith("createRecord")
        assert request.headers["Authorization"] == (
            "Bearer mock-access-token"
        )

        body = json.loads(request.content)
        assert body["repo"] == did
        assert body["collection"] == "app.bsky.feed.post"

        record = body["record"]
        assert record["text"] == message

        facet = record["facets"][0]
        assert facet["index"]["byteStart"] == len(
            "✨ Explore ".encode("utf-8")
        )
        assert facet["features"][0]["uri"] == (
            "https://example.com"
        )

        return httpx.Response(
            200,
            json={
                "uri": (
                    f"at://{did}/app.bsky.feed.post/abc123"
                ),
                "cid": "bafymockcid123",
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        publisher = BlueskyPublisher(
            "test.bsky.social",
            "mock-password",
        )
        result = await publisher.publish(message, client)

    assert result.status == "success"
    assert result.posted_url == (
        f"https://bsky.app/profile/{did}/post/abc123"
    )
    assert result.public_access is True
    assert result.error is None


@pytest.mark.asyncio
async def test_bluesky_authentication_failure():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(401)
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await BlueskyPublisher(
            "test.bsky.social",
            "invalid-password",
        ).publish("Visit https://example.com", client)

    assert result.status == "failed"
    assert "authentication failed" in result.error


@pytest.mark.asyncio
async def test_bluesky_missing_credentials():

    async with httpx.AsyncClient() as client:
        result = await BlueskyPublisher(
            "", ""
        ).publish("Visit https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_bluesky_publish_timeout():

    def handler(request):
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={
                    "accessJwt": "mock-token",
                    "did": "did:plc:test123",
                },
            )

        raise httpx.ReadTimeout("Mock publishing timeout")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await BlueskyPublisher(
            "test.bsky.social",
            "mock-password",
        ).publish("Visit https://example.com", client)

    assert result.status == "failed"
    assert "uncertain" in result.error


@pytest.mark.asyncio
async def test_bluesky_missing_post_confirmation():

    def handler(request):
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={
                    "accessJwt": "mock-token",
                    "did": "did:plc:test123",
                },
            )

        return httpx.Response(
            200,
            json={"uri": "invalid-uri"}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await BlueskyPublisher(
            "test.bsky.social",
            "mock-password",
        ).publish("Visit https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


# ---------------- MASTODON TESTS ----------------

from urllib.parse import parse_qs


@pytest.mark.asyncio
async def test_mastodon_success():

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/statuses"
        assert request.headers["Authorization"] == "Bearer dummy-token"

        payload = parse_qs(request.content.decode())
        assert payload["visibility"] == ["public"]
        assert payload["status"] == [
            "Testing https://example.com"
        ]

        return httpx.Response(
            200,
            json={
                "id": "113000000000000001",
                "created_at": "2026-11-17T16:00:00.000Z",
                "visibility": "public",
                "url": (
                    "https://mastodon.social/"
                    "@testuser/113000000000000001"
                )
            }
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        publisher = MastodonPublisher(
            "https://mastodon.social",
            "dummy-token"
        )
        result = await publisher.publish(
            "Testing https://example.com", client
        )

    assert result.status == "success"
    assert result.public_access is True
    assert result.posted_url == (
        "https://mastodon.social/"
        "@testuser/113000000000000001"
    )
    assert result.date == "2026-11-17"
    assert result.time == "16:00:00"
    assert result.error is None


@pytest.mark.asyncio
async def test_mastodon_auth_failure():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(401)
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await MastodonPublisher(
            "https://mastodon.social",
            "invalid-token"
        ).publish("Testing https://example.com", client)

    assert result.status == "failed"
    assert "authentication" in result.error


@pytest.mark.asyncio
async def test_mastodon_timeout():

    def handler(request):
        raise httpx.ReadTimeout("Mock timeout")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await MastodonPublisher(
            "https://mastodon.social",
            "dummy-token"
        ).publish("Testing https://example.com", client)

    assert result.status == "failed"
    assert "uncertain" in result.error


@pytest.mark.asyncio
async def test_mastodon_missing_token():

    async with httpx.AsyncClient() as client:
        result = await MastodonPublisher(
            "https://mastodon.social",
            ""
        ).publish("Testing https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_mastodon_private_response():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "id": "113000000000000002",
                "created_at": "2026-11-17T16:00:00Z",
                "visibility": "private",
                "url": (
                    "https://mastodon.social/"
                    "@testuser/113000000000000002"
                )
            }
        )
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await MastodonPublisher(
            "https://mastodon.social",
            "dummy-token"
        ).publish("Testing https://example.com", client)

    assert result.status == "success"
    assert result.public_access is False


@pytest.mark.asyncio
async def test_mastodon_missing_confirmation():

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"id": "123"}
        )
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:
        result = await MastodonPublisher(
            "https://mastodon.social",
            "dummy-token"
        ).publish("Testing https://example.com", client)

    assert result.status == "failed"
    assert result.posted_url is None


