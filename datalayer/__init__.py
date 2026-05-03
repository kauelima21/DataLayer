__version__ = "2.3.1"

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
