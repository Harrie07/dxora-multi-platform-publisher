
"""FastAPI entry point for multi-platform publishing."""

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.schemas import PostingRequest, PostingResponse

from app.platforms.base import Publisher
from app.platforms.telegram import TelegramPublisher
from app.platforms.discord import DiscordPublisher
from app.platforms.github_gist import GitHubGistPublisher
from app.platforms.bluesky import BlueskyPublisher
from app.platforms.mastodon import MastodonPublisher

from app.services.posting_service import PostingService


app = FastAPI(
    title="Dxora Multi-Platform Publisher",
    description=(
        "Publish a validated message across five "
        "third-party platforms using their official APIs."
    ),
    version="1.0.0"
)


def get_publishers(
    settings: Settings = Depends(get_settings)
) -> list[tuple[str, Publisher]]:
    """Select and configure the five supported platforms."""

    return [
        (
            "Telegram",
            TelegramPublisher(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id
            )
        ),
        (
            "Discord",
            DiscordPublisher(
                webhook_url=settings.discord_webhook_url,
                guild_id=settings.discord_guild_id
            )
        ),
        (
            "GitHub Gist",
            GitHubGistPublisher(
                token=settings.github_token
            )
        ),
        (
            "Bluesky",
            BlueskyPublisher(
                handle=settings.bluesky_handle,
                app_password=settings.bluesky_app_password,
                pds_url=settings.bluesky_pds_url
            )
        ),
        (
            "Mastodon",
            MastodonPublisher(
                base_url=settings.mastodon_base_url,
                access_token=settings.mastodon_access_token
            )
        )
    ]


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post(
    "/posting",
    response_model=PostingResponse
)
async def post_message(
    payload: PostingRequest,
    publishers: list[tuple[str, Publisher]] = Depends(
        get_publishers
    )
) -> PostingResponse:
    """Publish one message across all configured platforms."""

    service = PostingService(publishers)

    results = await service.publish(payload.message)

    successful = sum(
        result.status == "success"
        for result in results
    )

    return PostingResponse(
        success=successful > 0,
        total=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=results
    )
