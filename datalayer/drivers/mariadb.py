from __future__ import annotations

from typing import Any

from ..exceptions import ConnectionError as DLConnectionError
from ..exceptions import QueryError
from .base import AsyncDriver


class MariaDBDriver(AsyncDriver):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.pool = None

    async def connect(self) -> None:
        try:
            import asyncmy
        except ImportError as e:
            raise DLConnectionError("asyncmy nao instalado") from e
        try:
            self.pool = await asyncmy.create_pool(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                db=self.config["database"],
                minsize=self.config.get("pool_min", 1),
                maxsize=self.config.get("pool_max", 10),
                autocommit=True,
            )
        except Exception as e:
            raise DLConnectionError(str(e)) from e

    async def disconnect(self) -> None:
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def _acquire(self):
        if self.pool is None:
            raise DLConnectionError("Pool nao inicializado")
        return self.pool.acquire()

    async def fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        try:
            async with await self._acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = await cur.fetchall()
                    return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            raise QueryError(str(e)) from e

    async def fetch_one(
        self, sql: str, params: list[Any]
    ) -> dict[str, Any] | None:
        try:
            async with await self._acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    cols = [d[0] for d in cur.description] if cur.description else []
                    row = await cur.fetchone()
                    return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise QueryError(str(e)) from e

    async def execute(self, sql: str, params: list[Any]) -> int:
        try:
            async with await self._acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    return cur.rowcount or 0
        except Exception as e:
            raise QueryError(str(e)) from e

    async def insert(
        self, sql: str, params: list[Any], returning: bool
    ) -> dict[str, Any] | int:
        try:
            async with await self._acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    return cur.lastrowid or 0
        except Exception as e:
            raise QueryError(str(e)) from e
