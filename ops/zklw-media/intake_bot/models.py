"""Normalized data shapes shared across adapters, resolver, and dispatch.

Every channel adapter converts its native event into a `Request`. The resolver
turns a `Request` into a `Resolution`. dispatch turns a `Resolution` into a
`Reply`. Keeping these as plain dataclasses (no pydantic) keeps the core import-
light so it structure-checks without third-party deps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Optional


class Channel(str, Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    EMAIL = "email"


class MediaType(str, Enum):
    MOVIE = "movie"
    TV = "tv"


@dataclass
class Request:
    """A raw, normalized request as it enters the resolver."""

    channel: Channel
    user: str  # channel-native id (discord id, tg id, email addr)
    text: str  # the raw request text the user typed
    # `reply` is an async callback the adapter provides so the resolver can
    # answer on the SAME channel the request arrived on, without the resolver
    # needing to know channel internals.
    reply: Callable[[str], Awaitable[None]]
    # Optional explicit hints parsed by an adapter (e.g. a Discord slash-command
    # with a `tracker:` option). The resolver treats these as a hard pin.
    pinned_indexer: Optional[str] = None
    requested_type: Optional[MediaType] = None


@dataclass
class Candidate:
    """One TMDB search hit, the unit the LLM ranks and dispatch sends."""

    tmdb_id: int
    title: str
    year: Optional[int]
    media_type: MediaType
    overview: str = ""
    popularity: float = 0.0

    def label(self) -> str:
        y = f" ({self.year})" if self.year else ""
        return f"{self.title}{y}"


@dataclass
class Resolution:
    """The resolver's verdict for a request."""

    request: Request
    candidate: Optional[Candidate]  # None => could not resolve
    confidence: str = "none"  # "exact" | "llm" | "ambiguous" | "none"
    alternatives: list[Candidate] = field(default_factory=list)
    note: str = ""  # human-facing reason, esp. on failure

    @property
    def resolved(self) -> bool:
        return self.candidate is not None and self.confidence in ("exact", "llm")


@dataclass
class Reply:
    """What dispatch produced; the adapter renders this back to the channel."""

    ok: bool
    text: str
