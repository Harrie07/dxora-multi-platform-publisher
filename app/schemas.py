
"""Pydantic models defining the API request contract."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.validators import validate_single_cta

from typing import Literal

class PostingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=200
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank.")

        return validate_single_cta(value)

class PostingResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None

class PostingResponse(BaseModel):
    success: bool
    total: int
    successful: int
    failed: int
    results: list[PostingResult]