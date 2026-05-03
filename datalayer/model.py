from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .connection import Connection
from .exceptions import ValidationError


def _coerce(value: Any, tz: ZoneInfo) -> Any:
    """Normaliza tipos do driver para JSON-friendly:
    - datetime aware  -> astimezone(tz).isoformat()
    - datetime naive  -> isoformat() (assume ja na tz configurada)
    - date / time     -> isoformat()
    """
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(tz)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    return value


def _normalize_row(row: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    return {k: _coerce(v, tz) for k, v in row.items()}

_INTERNAL = {
    "_data",
    "_dirty",
    "_condition",
    "_params",
    "_order",
    "_group",
    "_limit",
    "_offset",
    "_in_clause",
    "_columns",
    "_table",
    "_required",
    "_primary_key",
    "_timestamps",
}


class DataLayer:
    """Base ActiveRecord. Configure via __init__(super) ou via class attrs:

        class User(DataLayer):
            table = "users"
            required = ["name", "email"]
            primary_key = "id"
            timestamps = True
    """

    table: str = ""
    required: list[str] = []
    primary_key: str = "id"
    timestamps: bool = True

    def __init__(
        self,
        table: str | None = None,
        required: list[str] | None = None,
        primary_key: str | None = None,
        timestamps: bool | None = None,
    ) -> None:
        cls = type(self)
        self._table = table if table is not None else cls.table
        self._required = list(
            required if required is not None else cls.required
        )
        self._primary_key = (
            primary_key if primary_key is not None else cls.primary_key
        )
        self._timestamps = (
            timestamps if timestamps is not None else cls.timestamps
        )
        if not self._table:
            raise ValueError(
                f"{cls.__name__}: 'table' nao definido (passe em __init__ ou como atributo de classe)"
            )

        self._data: dict[str, Any] = {}
        self._dirty: set[str] = set()
        self._condition: str | None = None
        self._params: dict[str, Any] = {}
        self._order: str | None = None
        self._group: str | None = None
        self._limit: int | None = None
        self._offset: int | None = None
        self._in_clause: tuple[str, list[Any]] | None = None
        self._columns: str = "*"

    # column-as-attr access -----------------------------------------------
    def __setattr__(self, name: str, value: Any) -> None:
        if name in _INTERNAL or name.startswith("__"):
            object.__setattr__(self, name, value)
            return
        # antes do __init__ terminar, _data ainda nao existe
        if "_data" not in self.__dict__:
            object.__setattr__(self, name, value)
            return
        self._data[name] = value
        self._dirty.add(name)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        data = self.__dict__.get("_data")
        if data is not None and name in data:
            return data[name]
        raise AttributeError(name)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def data(self) -> dict[str, Any]:
        return dict(self._data)

    def _hydrate(self, row: dict[str, Any]) -> "DataLayer":
        self._data = _normalize_row(row, Connection.timezone())
        self._dirty = set()  # reseta: registro fresh do banco
        return self

    # query builders ------------------------------------------------------
    def find(self, condition: str | None = None, **params: Any) -> "DataLayer":
        self._condition = condition
        self._params = dict(params)
        return self

    async def find_by_id(self, value: Any):
        self.find(f"{self._primary_key} = :id", id=value)
        return await self.fetch()

    def order(self, clause: str) -> "DataLayer":
        self._order = clause
        return self

    def group(self, clause: str) -> "DataLayer":
        self._group = clause
        return self

    def limit(self, n: int) -> "DataLayer":
        self._limit = int(n)
        return self

    def offset(self, n: int) -> "DataLayer":
        self._offset = int(n)
        return self

    def in_(self, column: str, values: Iterable[Any]) -> "DataLayer":
        self._in_clause = (column, list(values))
        return self

    def columns(self, spec: str) -> "DataLayer":
        self._columns = spec or "*"
        return self

    # execution -----------------------------------------------------------
    async def fetch(self, all: bool = False):
        driver = await Connection.driver()
        grammar = Connection.grammar()
        if all:
            effective_limit = self._limit
        else:
            effective_limit = self._limit if self._limit is not None else 1
        sql, params = grammar.compile_select(
            table=self._table,
            condition=self._condition,
            params=self._params,
            in_clause=self._in_clause,
            order=self._order,
            group=self._group,
            limit=effective_limit,
            offset=self._offset,
            columns=self._columns,
        )
        if all:
            rows = await driver.fetch(sql, params)
            return [type(self)()._hydrate(r) for r in rows]
        row = await driver.fetch_one(sql, params)
        if row is None:
            return None
        return type(self)()._hydrate(row)

    async def count(self) -> int:
        driver = await Connection.driver()
        grammar = Connection.grammar()
        sql, params = grammar.compile_count(
            table=self._table,
            condition=self._condition,
            params=self._params,
            in_clause=self._in_clause,
        )
        rows = await driver.fetch(sql, params)
        if not rows:
            return 0
        first = rows[0]
        if "total" in first:
            return int(first["total"])
        return int(next(iter(first.values())))

    def _validate(self) -> None:
        for col in self._required:
            if col not in self._data or self._data[col] in (None, ""):
                raise ValidationError(f"Campo '{col}' e obrigatorio")

    async def _exists_by_pk(self, driver, grammar, pk: str, value: Any) -> bool:
        sql, params = grammar.compile_count(
            table=self._table,
            condition=f"{pk} = :__pk_check",
            params={"__pk_check": value},
        )
        rows = await driver.fetch(sql, params)
        if not rows:
            return False
        first = rows[0]
        if "total" in first:
            return int(first["total"]) > 0
        return int(next(iter(first.values()))) > 0

    async def save(self) -> "DataLayer":
        self._validate()
        driver = await Connection.driver()
        grammar = Connection.grammar()
        pk = self._primary_key
        now = datetime.now(Connection.timezone()).replace(tzinfo=None)

        pk_value = self._data.get(pk)
        has_pk = pk_value not in (None, "")
        # pk hidratado do DB nao esta em _dirty; pk informado pelo usuario esta.
        # Para PKs nao auto-increment, precisamos checar existencia antes.
        if has_pk and pk in self._dirty:
            exists = await self._exists_by_pk(driver, grammar, pk, pk_value)
        else:
            exists = has_pk

        if exists:
            # UPDATE — apenas campos modificados; created_at nunca tocado
            data = {
                k: v
                for k, v in self._data.items()
                if k in self._dirty and k != pk and k != "created_at"
            }
            if not data:
                # nada modificado — devolve registro atual sem hit no DB
                return await type(self)().find_by_id(pk_value)
            if self._timestamps:
                data["updated_at"] = now
            sql, params = grammar.compile_update(
                table=self._table,
                data=data,
                condition=f"{pk} = :__pk",
                condition_params={"__pk": pk_value},
            )
            await driver.execute(sql, params)
            return await type(self)().find_by_id(pk_value)

        # INSERT
        if self._timestamps:
            self._data.setdefault("created_at", now)
            self._data.setdefault("updated_at", now)

        sql, params, returning = grammar.compile_insert(
            self._table, self._data, primary_key=pk
        )
        result = await driver.insert(sql, params, returning)
        if returning and isinstance(result, dict) and result:
            return type(self)()._hydrate(result)
        # MariaDB path — lastrowid
        new_id = result if isinstance(result, int) and result else self._data.get(pk)
        if new_id:
            return await type(self)().find_by_id(new_id)
        return self

    async def destroy(self) -> bool:
        driver = await Connection.driver()
        grammar = Connection.grammar()
        condition = self._condition
        params = dict(self._params)
        in_clause = self._in_clause

        # se carregado via find_by_id, _data tem pk mas _condition perdeu
        if condition is None and self._primary_key in self._data:
            condition = f"{self._primary_key} = :__pk"
            params = {"__pk": self._data[self._primary_key]}

        if condition is None and in_clause is None:
            raise ValueError("destroy() requer find()/find_by_id() ou registro carregado")

        sql, ordered = grammar.compile_delete(
            table=self._table,
            condition=condition,
            params=params,
            in_clause=in_clause,
        )
        affected = await driver.execute(sql, ordered)
        return affected > 0
