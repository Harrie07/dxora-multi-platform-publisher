
"""Tests for concurrent multi-platform publishing."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_publishers
from app.platforms.base import Publisher
from app.schemas import PostingResult
from app.services.posting_service import PostingService


class FakePublisher(Publisher):
    """Publisher used only for automated tests."""

    def __init__(
        self,
        name: str,
        status: str = "success",
        crash: bool = False
    ):
        self.name = name
        self.status = status
        self.crash = crash
        self.calls = 0

    async def publish(self, message, client):
        self.calls += 1

        if self.crash:
            raise RuntimeError("Sensitive test exception")

        return PostingResult(
            platform=self.name,
            status=self.status,
            error="Test failure" if self.status == "failed" else None
        )


@pytest.fixture
def mocked_api():
    names = [
        "Telegram", "Discord", "GitHub Gist",
        "Bluesky", "Mastodon"
    ]

    publishers = [FakePublisher(name) for name in names]

    app.dependency_overrides[get_publishers] = (
        lambda: [(p.name, p) for p in publishers]
    )

    try:
        with TestClient(app) as client:
            yield client, publishers
    finally:
        app.dependency_overrides.pop(get_publishers, None)


def test_posting_endpoint_all_success(mocked_api):
    client, publishers = mocked_api

    response = client.post(
        "/posting",
        json={"message": "Visit https://example.com"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["total"] == 5
    assert data["successful"] == 5
    assert data["failed"] == 0
    assert len(data["results"]) == 5
    assert all(p.calls == 1 for p in publishers)


def test_invalid_request_does_not_publish(mocked_api):
    client, publishers = mocked_api

    response = client.post(
        "/posting",
        json={"message": "No URL provided"}
    )

    assert response.status_code == 422
    assert all(p.calls == 0 for p in publishers)


@pytest.mark.asyncio
async def test_one_failure_does_not_stop_others():
    publishers = [
        ("Telegram", FakePublisher("Telegram")),
        ("Discord", FakePublisher("Discord", crash=True)),
        ("GitHub Gist", FakePublisher("GitHub Gist")),
        ("Bluesky", FakePublisher("Bluesky")),
        ("Mastodon", FakePublisher("Mastodon"))
    ]

    results = await PostingService(publishers).publish(
        "Visit https://example.com"
    )

    assert len(results) == 5
    assert sum(r.status == "success" for r in results) == 4
    assert results[1].status == "failed"
    assert results[1].platform == "Discord"

    # Internal exception details must not leak.
    assert "Sensitive" not in results[1].error


@pytest.mark.asyncio
async def test_publishers_execute_concurrently():
    started = 0
    all_started = asyncio.Event()

    class ConcurrentPublisher(Publisher):
        async def publish(self, message, client):
            nonlocal started

            started += 1

            if started == 5:
                all_started.set()

            await asyncio.wait_for(
                all_started.wait(),
                timeout=2.0
            )

            return PostingResult(
                platform="Test",
                status="success"
            )

    publishers = [
        (str(i), ConcurrentPublisher())
        for i in range(5)
    ]

    results = await PostingService(publishers).publish(
        "Visit https://example.com"
    )

    assert started == 5
    assert len(results) == 5
    assert all(r.status == "success" for r in results)
