from __future__ import annotations

import os
from typing import Any
from zoneinfo import ZoneInfo

from . import drivers as drivers_pkg
from . import grammar as grammar_pkg
from .drivers.base import AsyncDriver
from .exceptions import ConnectionError as DLConnectionError
from .grammar.base import Grammar

DEFAULT_TIMEZONE = "America/Sao_Paulo"


class Connection:
    """Singleton — driver + grammar carregados sob demanda via env vars."""

    _driver: AsyncDriver | None = None
    _grammar: Grammar | None = None
    _driver_name: str | None = None
    _timezone: ZoneInfo | None = None

    @classmethod
    def reset(cls) -> None:
        cls._driver = None
        cls._grammar = None
        cls._driver_name = None
        cls._timezone = None

    @classmethod
    def set_driver(cls, driver: AsyncDriver, grammar: Grammar) -> None:
        """Inject driver/grammar — usado em testes."""
        cls._driver = driver
        cls._grammar = grammar

    @classmethod
    def set_timezone(cls, name: str) -> None:
        """Override TZ — usado em testes ou config programatica."""
        cls._timezone = ZoneInfo(name)

    @classmethod
    def timezone(cls) -> ZoneInfo:
        if cls._timezone is None:
            name = os.environ.get("DATA_LAYER_TIMEZONE", DEFAULT_TIMEZONE)
            cls._timezone = ZoneInfo(name)
        return cls._timezone

    @classmethod
    def _load_config(cls) -> dict[str, Any]:
        name = os.environ.get("DATA_LAYER_DRIVER")
        if not name:
            raise DLConnectionError("DATA_LAYER_DRIVER nao configurado")
        cfg: dict[str, Any] = {
            "driver": name,
            "host": os.environ.get("DATA_LAYER_HOST", "localhost"),
            "database": os.environ.get("DATA_LAYER_DATABASE", ""),
            "user": os.environ.get("DATA_LAYER_USER", ""),
            "password": os.environ.get("DATA_LAYER_PASSWORD", ""),
            "pool_min": int(os.environ.get("DATA_LAYER_POOL_MIN", "1")),
            "pool_max": int(os.environ.get("DATA_LAYER_POOL_MAX", "10")),
        }
        default_port = "5432" if name.lower().startswith("post") else "3306"
        cfg["port"] = int(os.environ.get("DATA_LAYER_PORT", default_port))
        return cfg

    @classmethod
    async def driver(cls) -> AsyncDriver:
        if cls._driver is None:
            cfg = cls._load_config()
            cls._driver_name = cfg["driver"]
            driver_cls = drivers_pkg.for_driver(cfg["driver"])
            cls._driver = driver_cls(cfg)
            await cls._driver.connect()
            cls._grammar = grammar_pkg.for_driver(cfg["driver"])
        return cls._driver

    @classmethod
    def grammar(cls) -> Grammar:
        if cls._grammar is None:
            name = cls._driver_name or os.environ.get("DATA_LAYER_DRIVER")
            if not name:
                raise DLConnectionError("Grammar indisponivel — driver nao definido")
            cls._grammar = grammar_pkg.for_driver(name)
        return cls._grammar
