
"""Controlled live Bluesky publishing test."""

import asyncio

import httpx

from app.config import get_settings
from app.platforms.bluesky import BlueskyPublisher


async def main():
    settings = get_settings()

    if not settings.bluesky_handle or not settings.bluesky_app_password:
        print("ERROR: Bluesky credentials missing.")
        return

    publisher = BlueskyPublisher(
        handle=settings.bluesky_handle,
        app_password=settings.bluesky_app_password,
        pds_url=settings.bluesky_pds_url,
    )

    print("This will publish a REAL PUBLIC Bluesky post.")
    confirmation = input("Type POST to continue: ")

    if confirmation != "POST":
        print("Cancelled.")
        return

    message = (
        "Testing my Dxora Python multi-platform "
        "publishing application. https://example.com"
    )

    async with httpx.AsyncClient() as client:
        result = await publisher.publish(message, client)

    print("\nBluesky Publishing Result")
    print("-------------------------")
    print("Platform:", result.platform)
    print("Status:", result.status)
    print("Posted URL:", result.posted_url)
    print("Public Access:", result.public_access)
    print("Date:", result.date)
    print("Time:", result.time)
    print("Error:", result.error)


if __name__ == "__main__":
    asyncio.run(main())
