from __future__ import annotations

from typing import Any

from datalayer.drivers.base import AsyncDriver


class FakeDriver(AsyncDriver):
    """Driver em memoria — registra SQL/params, retorna canned rows."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[Any]]] = []
        self.fetch_rows: list[dict[str, Any]] = []
        self.fetch_one_row: dict[str, Any] | None = None
        self.execute_affected: int = 1
        self.insert_result: Any = {"id": 1}
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        self.calls.append(("fetch", sql, params))
        return list(self.fetch_rows)

    async def fetch_one(
        self, sql: str, params: list[Any]
    ) -> dict[str, Any] | None:
        self.calls.append(("fetch_one", sql, params))
        return self.fetch_one_row

    async def execute(self, sql: str, params: list[Any]) -> int:
        self.calls.append(("execute", sql, params))
        return self.execute_affected

    async def insert(
        self, sql: str, params: list[Any], returning: bool
    ) -> Any:
        self.calls.append(("insert", sql, params))
        return self.insert_result

    # helpers ----------------------------------------------------------
    def last_sql(self) -> str:
        return self.calls[-1][1]

    def last_params(self) -> list[Any]:
        return self.calls[-1][2]
