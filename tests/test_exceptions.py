from datalayer import (
    ConnectionError,
    DataLayerError,
    QueryError,
    ValidationError,
)


def test_validation_inherits_base():
    assert issubclass(ValidationError, DataLayerError)


def test_connection_inherits_base():
    assert issubclass(ConnectionError, DataLayerError)


def test_query_inherits_base():
    assert issubclass(QueryError, DataLayerError)


def test_can_catch_specific_as_base():
    try:
        raise ValidationError("x")
    except DataLayerError as e:
        assert str(e) == "x"
