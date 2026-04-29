from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AsyncDriver(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def fetch_one(
        self, sql: str, params: list[Any]
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    async def execute(self, sql: str, params: list[Any]) -> int:
        """Returns affected rows."""
        ...

    @abstractmethod
    async def insert(
        self, sql: str, params: list[Any], returning: bool
    ) -> dict[str, Any] | int:
        """Postgres: returns row dict. MariaDB: returns lastrowid."""
        ...
