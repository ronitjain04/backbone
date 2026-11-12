"""Bounded, request-local conversation context; no server-side history store."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_MESSAGE_CHARS = 4000
MAX_HISTORY_CHARS = 16000


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=MAX_HISTORY_MESSAGE_CHARS)

    @field_validator('content')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Conversation messages must not be blank')
        return value.strip()


def validate_history(messages):
    if len(messages) % 2:
        raise ValueError('Conversation history must contain completed exchanges')
    for index, message in enumerate(messages):
        if message.role != ('user' if index % 2 == 0 else 'assistant'):
            raise ValueError('Conversation roles must alternate user and assistant')
    if sum(len(message.content) for message in messages) > MAX_HISTORY_CHARS:
        raise ValueError('Conversation history is too large')
    return messages
