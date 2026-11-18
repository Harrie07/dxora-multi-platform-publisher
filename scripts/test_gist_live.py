
"""Publish one real public GitHub Gist."""

import asyncio

import httpx

from app.config import get_settings
from app.platforms.github_gist import GitHubGistPublisher


async def main():
    settings = get_settings()

    if not settings.github_token:
        print("ERROR: GITHUB_TOKEN is missing.")
        return

    print("This will create a REAL PUBLIC GitHub Gist.")
    confirmation = input("Type POST to continue: ")

    if confirmation != "POST":
        print("Cancelled.")
        return

    message = (
        "Testing my Dxora Python multi-platform "
        "publishing application. https://example.com"
    )

    async with httpx.AsyncClient() as client:
        result = await GitHubGistPublisher(
            settings.github_token
        ).publish(message, client)

    print("\nGitHub Gist Publishing Result")
    print("-----------------------------")
    print("Platform:", result.platform)
    print("Status:", result.status)
    print("Posted URL:", result.posted_url)
    print("Public Access:", result.public_access)
    print("Date:", result.date)
    print("Time:", result.time)
    print("Error:", result.error)


if __name__ == "__main__":
    asyncio.run(main())
