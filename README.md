# Dxora Multi-Platform Publisher

A FastAPI application that publishes a single, validated message to **five third-party platforms concurrently**, using official APIs and reporting the actual outcome of each publication.

**Practical test:** [Python Practical Test – Automated Multi-Platform Posting System](https://github.com/chivoxai/practical-test/blob/main/python-post-message.md)

## Features

- One REST endpoint: `POST /posting` (port `4000`).
- Message length limited to **200 characters**, with **exactly one valid HTTP(S) CTA URL**.
- Internal selection of all five platforms (the client does not select destinations).
- Concurrent asynchronous API calls using `asyncio.gather()` and `httpx.AsyncClient`.
- Independent error handling: one platform's failure does not stop the others.
- Per-platform status, real post URL where available, public-access flag, UTC date/time, and error details.
- Pydantic request and response validation, interactive Swagger docs, and mocked automated tests.
- Secrets loaded from environment variables rather than committed to the repository.

## Supported platforms

| Platform | Integration | Visibility / URL behavior |
| --- | --- | --- |
| Telegram | Bot API (`sendMessage`) | Public channel posts have a `t.me` URL; private destinations might not. |
| Discord | Incoming webhook (`wait=true`) | Message URL is generated when `DISCORD_GUILD_ID` is configured; `public_access` is `false` for the member-only server. |
| GitHub Gist | GitHub REST Gists API | Creates a public Markdown Gist and returns its actual URL. |
| Bluesky | AT Protocol XRPC | Creates a feed post with a clickable CTA link facet; returns a `bsky.app` URL. |
| Mastodon | Mastodon REST API | Creates a public status and returns its URL when the instance provides one. |

## Project structure

```text
dxora-multi-platform-publisher/
├── app/
│   ├── main.py                    # FastAPI routes and dependency injection
│   ├── config.py                  # Environment-based settings
│   ├── schemas.py                 # Request and response models
│   ├── validators.py              # Single CTA URL validation
│   ├── platforms/
│   │   ├── base.py                # Abstract Publisher contract
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   ├── github_gist.py
│   │   ├── bluesky.py
│   │   └── mastodon.py
│   └── services/
│       └── posting_service.py     # Concurrent orchestration and isolation
├── tests/
│   ├── test_platforms.py
│   ├── test_posting_service.py
│   └── test_validation.py
├── scripts/                       # Optional manual API checks and live tests
├── evidence/                      # Screenshots of successful publications
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Requirements

- Python **3.11+** (developed and tested with Python 3.11.8)
- Network access for live publishing
- Credentials and a suitable destination/account for each platform

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/Harrie07/dxora-multi-platform-publisher.git
cd dxora-multi-platform-publisher
```

### 2. Create a virtual environment and install dependencies

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in **your own** values.

**Windows PowerShell:** `Copy-Item .env.example .env`

**Linux / macOS:** `cp .env.example .env`

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=
DISCORD_GUILD_ID=
GITHUB_TOKEN=
BLUESKY_HANDLE=
BLUESKY_APP_PASSWORD=
BLUESKY_PDS_URL=https://bsky.social
MASTODON_BASE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=
```

Configuration notes:

- **Telegram:** Add the bot as a channel administrator with permission to post. A public channel username is needed for a public `t.me` post link.
- **Discord:** Create an incoming webhook for the target channel. Supply the numeric server/guild ID if you want a Discord message link. A working link may still require server membership.
- **GitHub Gist:** Use a token with the permissions needed to create Gists.
- **Bluesky:** Use an app password, not your account password.
- **Mastodon:** Use an access token with permission to write statuses on the configured instance.

**Security:** `.env` is excluded by `.gitignore`. Never commit tokens, webhook URLs, passwords, or a populated `.env` file.

### 4. Run the API

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 4000
```

Open:

- Health check: <http://127.0.0.1:4000/health>
- Swagger UI: <http://127.0.0.1:4000/docs>
- OpenAPI JSON: <http://127.0.0.1:4000/openapi.json>

## API usage

### `POST /posting`

The message must be at most 200 characters and contain exactly one valid HTTP(S) URL.

**Request:**

```json
{
  "message": "Check out our latest update. https://example.com"
}
```

**PowerShell example:**

```powershell
$body = @{ message = "Check out our latest update. https://example.com" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:4000/posting" -Method Post -ContentType "application/json" -Body $body
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message":"Check out our latest update. https://example.com"}'
```

**Sample successful response** (actual values recorded during the integration test on November 18, 2026):

```json
{
  "success": true,
  "total": 5,
  "successful": 5,
  "failed": 0,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/Dxora_Demo/11",
      "public_access": true,
      "date": "2026-11-18",
      "time": "01:31:34",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1572158822510891009/1572158875623497738/1572423995087921243",
      "public_access": false,
      "date": "2026-11-18",
      "time": "01:31:34",
      "error": null
    },
    {
      "platform": "GitHub Gist",
      "status": "success",
      "posted_url": "https://gist.github.com/Harrie07/60104788e6e92690427b535c2237d18e",
      "public_access": true,
      "date": "2026-11-18",
      "time": "01:31:34",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/did:plc:4pb7tyfz2vyl25jhjntwpxxd/post/3n2kfwfypc62e",
      "public_access": true,
      "date": "2026-11-18",
      "time": "01:31:33",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@harrie07/117634858654827334",
      "public_access": true,
      "date": "2026-11-18",
      "time": "01:31:34",
      "error": null
    }
  ]
}
```

`date` and `time` are reported in **UTC**. Each platform reports its own publishing outcome. A non-public Discord message can be successfully posted even though `public_access` is `false`.

### Error behavior

- **HTTP 422:** Invalid request, such as an empty message, more than 200 characters, missing/invalid CTA URL, multiple CTA URLs, or unexpected request fields. Validation happens before publishing.
- **HTTP 200:** The request was processed and the results from all configured publishers are included, even if some or all publishers failed. `success` is `true` if at least one publisher succeeded.
- **Platform failure:** An individual `results` entry uses `status: "failed"`, and includes a safe error message; other publishers continue.
- **Timeouts:** A timed-out remote call can leave publication status uncertain. Inspect the destination before retrying to avoid duplicate posts.

## Architecture

```text
Client
  |
  v
FastAPI POST /posting
  |
  v
Pydantic PostingRequest -> validate <=200 chars and exactly one CTA URL
  |
  v
PostingService.publish(message)
  |
  +-- asyncio.gather() with one shared httpx.AsyncClient
  |      +-- TelegramPublisher
  |      +-- DiscordPublisher
  |      +-- GitHubGistPublisher
  |      +-- BlueskyPublisher
  |      +-- MastodonPublisher
  |
  v
PostingResponse: total, successful, failed, results[]
```

Each publisher implements the same asynchronous `Publisher` interface. `PostingService` catches unexpected exceptions per destination, preventing a single integration failure from aborting the complete request. Configuration is injected into the FastAPI route via `get_publishers`.

## Testing

Run the mocked automated test suite (does **not** create live posts):

```bash
python -m pytest tests/ -v
```

**Verified local test run:** 46 passing tests, covering input validation, platform success/failure cases, concurrency, and failure isolation.

Optional live scripts are located in `scripts/` and prompt for an explicit `POST` confirmation. **They create real posts** and should not be used as automated unit tests. Similarly, calling `POST /posting` with real credentials creates real content on all five platforms.

## Demonstration evidence

See the [`evidence/`](evidence/) directory for screenshots. The live end-to-end test returned five successful platform results on **November 18, 2026**. Links to published content appear in the sample response above; the Discord link requires appropriate server access.

## Notes and limitations

- The service is intended for local demonstration. There is **no authentication or rate limiting** on `POST /posting`; do not expose it to the public internet with live posting credentials.
- Each request creates new content; idempotency and deduplication are not implemented.
- Per-platform posting is not a distributed transaction. A successful post is not rolled back if another platform fails.
- Public accessibility reflects API metadata and configured destination settings; independent anonymous-browser accessibility depends on platform rules and account visibility.

## Official API documentation

- [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)
- [Discord Execute Webhook](https://discord.com/developers/docs/resources/webhook#execute-webhook)
- [GitHub Gists REST API](https://docs.github.com/en/rest/gists/gists#create-a-gist)
- [Bluesky / AT Protocol](https://docs.bsky.app/docs/advanced-guides/posts)
- [Mastodon Post a new status](https://docs.joinmastodon.org/methods/statuses/#create)
