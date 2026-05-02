from __future__ import annotations

import re
from typing import Any

_NAMED_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


class Grammar:
    """SQL builder + placeholder translator. Subclasses define `placeholder`."""

    def placeholder(self, index: int) -> str:
        raise NotImplementedError

    def quote_ident(self, name: str) -> str:
        return f'"{name}"' if '"' not in name else name

    def translate(
        self, sql: str, params: dict[str, Any] | None
    ) -> tuple[str, list[Any]]:
        """Translate :name placeholders to native ones. Returns (sql, ordered_params)."""
        params = params or {}
        ordered: list[Any] = []
        counter = {"i": 0}

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in params:
                raise KeyError(f"Param ':{key}' nao fornecido")
            counter["i"] += 1
            ordered.append(params[key])
            return self.placeholder(counter["i"])

        new_sql = _NAMED_PARAM_RE.sub(repl, sql)
        return new_sql, ordered

    def compile_select(
        self,
        table: str,
        condition: str | None = None,
        params: dict[str, Any] | None = None,
        in_clause: tuple[str, list[Any]] | None = None,
        order: str | None = None,
        group: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        columns: str = "*",
    ) -> tuple[str, list[Any]]:
        sql = f"SELECT {columns} FROM {table}"
        params = dict(params or {})
        wheres: list[str] = []
        if condition:
            wheres.append(f"({condition})")
        if in_clause:
            col, values = in_clause
            keys = []
            for idx, v in enumerate(values):
                k = f"__in_{col}_{idx}"
                params[k] = v
                keys.append(f":{k}")
            wheres.append(f"{col} IN ({', '.join(keys)})")
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        if group:
            sql += f" GROUP BY {group}"
        if order:
            sql += f" ORDER BY {order}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset is not None:
            sql += f" OFFSET {int(offset)}"
        return self.translate(sql, params)

    def compile_count(
        self,
        table: str,
        condition: str | None = None,
        params: dict[str, Any] | None = None,
        in_clause: tuple[str, list[Any]] | None = None,
    ) -> tuple[str, list[Any]]:
        return self.compile_select(
            table=table,
            condition=condition,
            params=params,
            in_clause=in_clause,
            columns="COUNT(*) AS total",
        )

    def compile_insert(
        self, table: str, data: dict[str, Any], primary_key: str = "id"
    ) -> tuple[str, list[Any], bool]:
        cols = list(data.keys())
        keys = [f":{c}" for c in cols]
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({', '.join(keys)})"
        )
        sql, ordered = self.translate(sql, data)
        return sql, ordered, False  # supports_returning overridden

    def compile_update(
        self,
        table: str,
        data: dict[str, Any],
        condition: str,
        condition_params: dict[str, Any],
    ) -> tuple[str, list[Any]]:
        sets = []
        merged = dict(condition_params)
        for col, val in data.items():
            placeholder_key = f"__set_{col}"
            sets.append(f"{col} = :{placeholder_key}")
            merged[placeholder_key] = val
        sql = f"UPDATE {table} SET {', '.join(sets)} WHERE {condition}"
        return self.translate(sql, merged)

    def compile_delete(
        self,
        table: str,
        condition: str | None = None,
        params: dict[str, Any] | None = None,
        in_clause: tuple[str, list[Any]] | None = None,
    ) -> tuple[str, list[Any]]:
        sql = f"DELETE FROM {table}"
        params = dict(params or {})
        wheres: list[str] = []
        if condition:
            wheres.append(f"({condition})")
        if in_clause:
            col, values = in_clause
            keys = []
            for idx, v in enumerate(values):
                k = f"__in_{col}_{idx}"
                params[k] = v
                keys.append(f":{k}")
            wheres.append(f"{col} IN ({', '.join(keys)})")
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        return self.translate(sql, params)
