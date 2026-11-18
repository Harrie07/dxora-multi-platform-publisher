
"""Rules for the single CTA URL required in each message."""

import re

from pydantic import HttpUrl, TypeAdapter, ValidationError

# Detect URL-like strings, including unsupported schemes.
URL_PATTERN = re.compile(
    r"""(?i)(?<![\w@])(?:[a-z][a-z0-9+.-]*://|www\.)[^\s,;<>\[\]{}"']+"""
)

HTTP_URL = TypeAdapter(HttpUrl)


def validate_single_cta(message: str) -> str:
    """Require exactly one valid HTTP(S) CTA URL."""

    candidates = [
        match.group().rstrip(".!?:)]}")
        for match in URL_PATTERN.finditer(message)
    ]

    if len(candidates) != 1:
        raise ValueError(
            "Message must contain exactly one CTA URL."
        )

    try:
        parsed_url = HTTP_URL.validate_python(candidates[0])
    except ValidationError as exc:
        raise ValueError(
            "CTA must be a valid http:// or https:// URL."
        ) from exc

    if not parsed_url.host or "." not in parsed_url.host:
        raise ValueError(
            "CTA URL must have a valid domain name."
        )

    return message
