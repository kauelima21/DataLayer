from .base import AsyncDriver

__all__ = ["AsyncDriver"]


def for_driver(name: str) -> type[AsyncDriver]:
    n = name.lower()
    if n in ("postgres", "postgresql", "pg"):
        from .postgres import PostgresDriver
        return PostgresDriver
    if n in ("mariadb", "mysql"):
        from .mariadb import MariaDBDriver
        return MariaDBDriver
    raise ValueError(f"Driver desconhecido: {name}")
