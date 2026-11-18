
"""Run one intentional live Telegram publishing test."""

import asyncio

import httpx

from app.config import get_settings
from app.platforms.telegram import TelegramPublisher


async def main():
    settings = get_settings()

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("ERROR: Telegram credentials are missing.")
        return

    print("This test will publish a REAL message to your channel.")

    confirmation = input("Type POST to continue: ")

    if confirmation != "POST":
        print("Cancelled. No publishing request was made.")
        return

    publisher = TelegramPublisher(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )

    message = (
        "Testing my Dxora Python multi-platform "
        "publishing application. https://example.com"
    )

    async with httpx.AsyncClient() as client:
        result = await publisher.publish(message, client)

    print("\nTelegram Publishing Result")
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
