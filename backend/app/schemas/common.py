"""Schemas shared across routers."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    """A simple human-readable response."""

    detail: str


class HealthStatus(BaseModel):
    """Payload returned by the health-check endpoint."""

    status: str = Field(description="'ok' when every dependency is reachable")
    service: str
    version: str
    environment: str
    database: str = Field(description="'connected' or 'disconnected'")
    database_error: Optional[str] = None
    timestamp: str


class Page(BaseModel, Generic[T]):
    """A generic paginated envelope."""

    items: List[T]
    total: int
    page: int = 1
    page_size: int = 25
