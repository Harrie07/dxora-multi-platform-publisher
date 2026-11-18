"""Dxora credentials preflight: read-only checks; never publishes a post.

Run from the project root with: python scripts/preflight.py
Requires: pip install httpx python-dotenv
"""

import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


def required(*names: str) -> tuple[str, ...] | None:
    values = tuple(os.getenv(name, '').strip() for name in names)
    return values if all(values) else None


async def telegram(client: httpx.AsyncClient) -> str:
    config = required('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID')
    if not config:
        return 'NOT READY: missing Telegram configuration'
    token, chat_id = config
    api = f'https://api.telegram.org/bot{token}'

    identity = await client.get(f'{api}/getMe')
    if identity.status_code != 200 or not identity.json().get('ok'):
        return f'FAIL: bot authentication (HTTP {identity.status_code})'
    bot_id = identity.json()['result']['id']

    channel = await client.get(f'{api}/getChat', params={'chat_id': chat_id})
    if channel.status_code != 200 or not channel.json().get('ok'):
        return f'FAIL: channel lookup (HTTP {channel.status_code})'
    info = channel.json()['result']
    if info.get('type') != 'channel' or not info.get('username'):
        return 'FAIL: destination is not a public channel'

    membership = await client.get(
        f'{api}/getChatMember',
        params={'chat_id': chat_id, 'user_id': bot_id},
    )
    if membership.status_code != 200 or not membership.json().get('ok'):
        return f'FAIL: cannot inspect channel permissions (HTTP {membership.status_code})'
    member = membership.json()['result']
    if member.get('status') != 'administrator' or not member.get('can_post_messages'):
        return 'FAIL: bot lacks channel posting permission'
    return 'PASS: bot authenticated; public channel; posting permission confirmed'


async def discord(client: httpx.AsyncClient) -> str:
    config = required('DISCORD_WEBHOOK_URL')
    if not config:
        return 'NOT READY: missing webhook URL'
    (url,) = config
    if not url.startswith('https://discord.com/api/webhooks/'):
        return 'FAIL: webhook URL format is unexpected'
    response = await client.get(url)
    if response.status_code != 200:
        return f'FAIL: webhook lookup (HTTP {response.status_code})'
    data = response.json()
    if data.get('type') != 1 or not data.get('channel_id'):
        return 'FAIL: not a usable incoming webhook'
    return 'PASS: incoming webhook is reachable (posting not yet tested)'


async def github(client: httpx.AsyncClient) -> str:
    config = required('GITHUB_TOKEN')
    if not config:
        return 'NOT READY: missing GitHub token'
    (token,) = config
    response = await client.get(
        'https://api.github.com/gists',
        params={'per_page': 1},
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
        },
    )
    if response.status_code != 200 or not isinstance(response.json(), list):
        return f'FAIL: Gist API access (HTTP {response.status_code})'
    return 'PASS: token accepted by Gist API (write scope not yet tested)'


async def bluesky(client: httpx.AsyncClient) -> str:
    config = required('BLUESKY_HANDLE', 'BLUESKY_APP_PASSWORD', 'BLUESKY_PDS_URL')
    if not config:
        return 'NOT READY: missing Bluesky configuration'
    handle, password, pds_url = config
    if not pds_url.startswith('https://'):
        return 'FAIL: PDS URL must use HTTPS'
    response = await client.post(
        f'{pds_url.rstrip("/")}/xrpc/com.atproto.server.createSession',
        json={'identifier': handle, 'password': password},
    )
    if response.status_code != 200:
        return f'FAIL: session creation (HTTP {response.status_code})'
    data = response.json()
    if not data.get('did') or not data.get('accessJwt'):
        return 'FAIL: session response missing required fields'
    return 'PASS: authenticated session created (publishing not yet tested)'


async def mastodon(client: httpx.AsyncClient) -> str:
    config = required('MASTODON_BASE_URL', 'MASTODON_ACCESS_TOKEN')
    if not config:
        return 'NOT READY: missing Mastodon configuration'
    base_url, token = config
    if not base_url.startswith('https://'):
        return 'FAIL: instance URL must use HTTPS'
    response = await client.get(
        f'{base_url.rstrip("/")}/api/v1/apps/verify_credentials',
        headers={'Authorization': f'Bearer {token}'},
    )
    if response.status_code != 200 or not response.json().get('id'):
        return f'FAIL: token/application check (HTTP {response.status_code})'
    return 'PASS: application token recognized (user/write scope not yet tested)'


async def check(name: str, callback, client: httpx.AsyncClient) -> tuple[str, str]:
    try:
        return name, await callback(client)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # Never print raw exceptions: they can contain credential-bearing URLs.
        return name, 'FAIL: network or unexpected API response (details suppressed for safety)'


async def main() -> None:
    async with httpx.AsyncClient(timeout=12.0) as client:
        results = await asyncio.gather(*[
            check(name, function, client)
            for name, function in [
                ('Telegram', telegram),
                ('Discord', discord),
                ('GitHub', github),
                ('Bluesky', bluesky),
                ('Mastodon', mastodon),
            ]
        ])
    print('Dxora read-only API preflight — no posts created')
    for name, result in results:
        print(f'{name}: {result}')
    print(f'Checks passed: {sum(result.startswith("PASS") for _, result in results)}/5')


if __name__ == '__main__':
    asyncio.run(main())
