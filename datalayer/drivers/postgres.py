from __future__ import annotations

from typing import Any

from ..exceptions import ConnectionError as DLConnectionError
from ..exceptions import QueryError
from .base import AsyncDriver


class PostgresDriver(AsyncDriver):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.pool = None

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as e:
            raise DLConnectionError("asyncpg nao instalado") from e
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                min_size=self.config.get("pool_min", 1),
                max_size=self.config.get("pool_max", 10),
            )
        except Exception as e:
            raise DLConnectionError(str(e)) from e

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        if self.pool is None:
            raise DLConnectionError("Pool nao inicializado")
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
                return [dict(r) for r in rows]
        except Exception as e:
            raise QueryError(str(e)) from e

    async def fetch_one(
        self, sql: str, params: list[Any]
    ) -> dict[str, Any] | None:
        if self.pool is None:
            raise DLConnectionError("Pool nao inicializado")
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(sql, *params)
                return dict(row) if row else None
        except Exception as e:
            raise QueryError(str(e)) from e

    async def execute(self, sql: str, params: list[Any]) -> int:
        if self.pool is None:
            raise DLConnectionError("Pool nao inicializado")
        try:
            async with self.pool.acquire() as conn:
                tag = await conn.execute(sql, *params)
                parts = tag.split()
                return int(parts[-1]) if parts and parts[-1].isdigit() else 0
        except Exception as e:
            raise QueryError(str(e)) from e

    async def insert(
        self, sql: str, params: list[Any], returning: bool
    ) -> dict[str, Any] | int:
        if self.pool is None:
            raise DLConnectionError("Pool nao inicializado")
        try:
            async with self.pool.acquire() as conn:
                if returning:
                    row = await conn.fetchrow(sql, *params)
                    return dict(row) if row else {}
                await conn.execute(sql, *params)
                return 0
        except Exception as e:
            raise QueryError(str(e)) from e
