
"""Publish one intentional live test message to Discord."""

import asyncio

import httpx

from app.config import get_settings
from app.platforms.discord import DiscordPublisher


async def main():
    settings = get_settings()

    if not settings.discord_webhook_url:
        print("ERROR: Discord webhook URL is missing.")
        return

    publisher = DiscordPublisher(
        webhook_url=settings.discord_webhook_url,
        guild_id=settings.discord_guild_id
    )

    message = (
        "Testing my Dxora Python multi-platform "
        "publishing application. https://example.com"
    )

    print("This will publish a REAL Discord message.")
    confirmation = input("Type POST to continue: ")

    if confirmation != "POST":
        print("Cancelled. No message was sent.")
        return

    async with httpx.AsyncClient() as client:
        result = await publisher.publish(message, client)

    print("\nDiscord Publishing Result")
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
