class DataLayerError(Exception):
    pass


class ValidationError(DataLayerError):
    pass


class ConnectionError(DataLayerError):
    pass


class QueryError(DataLayerError):
    pass
