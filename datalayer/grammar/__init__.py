from .base import Grammar
from .mariadb import MariaDBGrammar
from .postgres import PostgresGrammar

__all__ = ["Grammar", "MariaDBGrammar", "PostgresGrammar"]


def for_driver(driver: str) -> Grammar:
    d = driver.lower()
    if d in ("postgres", "postgresql", "pg"):
        return PostgresGrammar()
    if d in ("mariadb", "mysql"):
        return MariaDBGrammar()
    raise ValueError(f"Driver desconhecido: {driver}")
