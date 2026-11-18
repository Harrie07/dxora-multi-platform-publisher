"""Controlled real Mastodon publishing test."""

import asyncio

import httpx

from app.config import get_settings
from app.platforms.mastodon import MastodonPublisher


async def main():
    settings = get_settings()

    if not settings.mastodon_access_token:
        print("ERROR: Mastodon token is missing.")
        return

    publisher = MastodonPublisher(
        base_url=settings.mastodon_base_url,
        access_token=settings.mastodon_access_token
    )

    message = (
        "Testing my Dxora Python multi-platform "
        "publishing application. https://example.com"
    )

    print("This will publish a REAL PUBLIC Mastodon post.")
    confirmation = input("Type POST to continue: ")

    if confirmation != "POST":
        print("Cancelled. No post created.")
        return

    async with httpx.AsyncClient() as client:
        result = await publisher.publish(message, client)

    print("\nMastodon Publishing Result")
    print("--------------------------")
    print("Platform:", result.platform)
    print("Status:", result.status)
    print("Posted URL:", result.posted_url)
    print("Public Access:", result.public_access)
    print("Date:", result.date)
    print("Time:", result.time)
    print("Error:", result.error)


if __name__ == "__main__":
    asyncio.run(main())
