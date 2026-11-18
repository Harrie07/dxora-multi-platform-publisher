
import pytest
from fastapi.testclient import TestClient


from app.main import app,get_publishers

client = TestClient(app)


@pytest.mark.parametrize("message", [
    "",
    "   ",
    "A message with no link",
    "Visit https://example.com and https://other.com",
    "Visit https://example.com,https://other.com",
    "Visit ftp://example.com",
    "Visit https://localhost",
    "Visit https://",
    "A" * 201 + " https://example.com",
])
def test_reject_invalid_message(message):
    response = client.post(
        "/posting",
        json={"message": message}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("message", [
    "Visit https://example.com",
    "Visit (https://example.com).",
    "Visit https://example.com/path?q=abc&x=1",
    "A" * (200 - len(" https://example.com"))
        + " https://example.com",
])

def test_accept_valid_message(message):
    response = client.post(
        "/posting",
        json={"message": message}
    )

    # The endpoint is now implemented.
    assert response.status_code == 200

    data = response.json()

    # Real publishers are disabled by our test fixture.
    assert data["total"] == 0
    assert data["successful"] == 0
    assert data["failed"] == 0
    assert data["results"] == []

def test_reject_extra_fields():
    response = client.post(
        "/posting",
        json={
            "message": "Visit https://example.com",
            "platforms": ["telegram"]
        }
    )
    assert response.status_code == 422


def test_reject_non_string_message():
    response = client.post(
        "/posting",
        json={"message": 123}
    )
    assert response.status_code == 422


@pytest.fixture(autouse=True)
def disable_live_publishing():
    """Prevent validation tests from calling real APIs."""

    previous = app.dependency_overrides.get(get_publishers)

    # No publishers are configured during validation tests.
    app.dependency_overrides[get_publishers] = lambda: []

    yield

    # Restore the original dependency configuration.
    if previous is None:
        app.dependency_overrides.pop(get_publishers, None)
    else:
        app.dependency_overrides[get_publishers] = previous

