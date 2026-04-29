import pytest

from datalayer.connection import Connection
from datalayer.grammar.postgres import PostgresGrammar
from datalayer.grammar.mariadb import MariaDBGrammar

from .fake_driver import FakeDriver


@pytest.fixture
def fake_pg():
    driver = FakeDriver()
    Connection.set_driver(driver, PostgresGrammar())
    yield driver
    Connection.reset()


@pytest.fixture
def fake_maria():
    driver = FakeDriver()
    Connection.set_driver(driver, MariaDBGrammar())
    yield driver
    Connection.reset()
