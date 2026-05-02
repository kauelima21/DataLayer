__version__ = "2.2.0"

from .connection import Connection
from .exceptions import (
    ConnectionError,
    DataLayerError,
    QueryError,
    ValidationError,
)
from .model import DataLayer

# Alias — spec mostra ambos os nomes
Model = DataLayer

__all__ = [
    "__version__",
    "DataLayer",
    "Model",
    "Connection",
    "DataLayerError",
    "ValidationError",
    "ConnectionError",
    "QueryError",
]
