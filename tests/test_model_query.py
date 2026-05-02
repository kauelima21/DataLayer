from datetime import date, datetime, time

import pytest

from datalayer import DataLayer


class User(DataLayer):
    table = "users"
    required = ["name", "email"]
    primary_key = "id"
    timestamps = True


async def test_fetch_one_returns_hydrated_instance(fake_pg):
    fake_pg.fetch_one_row = {"id": 1, "name": "kaue", "email": "k@x.com"}
    user = await User().find_by_id(1)
    assert user is not None
    assert user.name == "kaue"
    assert user["email"] == "k@x.com"
    sql, params = fake_pg.last_sql(), fake_pg.last_params()
    assert "WHERE (id = $1)" in sql
    assert "LIMIT 1" in sql
    assert params == [1]


async def test_fetch_one_returns_none_when_no_row(fake_pg):
    fake_pg.fetch_one_row = None
    user = await User().find_by_id(999)
    assert user is None


async def test_fetch_many_returns_list(fake_pg):
    fake_pg.fetch_rows = [
        {"id": 1, "name": "a"},
        {"id": 2, "name": "b"},
    ]
    rows = await User().find().fetch(True)
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["name"] == "a"


async def test_fetch_many_chain_with_filters(fake_pg):
    fake_pg.fetch_rows = []
    await (
        User()
        .find("role = :role", role="admin")
        .in_("id", [1, 2, 3])
        .order("name ASC")
        .limit(10)
        .offset(5)
        .fetch(True)
    )
    sql, params = fake_pg.last_sql(), fake_pg.last_params()
    assert "WHERE (role = $1) AND id IN ($2, $3, $4)" in sql
    assert "ORDER BY name ASC" in sql
    assert "LIMIT 10" in sql
    assert "OFFSET 5" in sql
    assert params == ["admin", 1, 2, 3]


async def test_columns_restricts_select_list(fake_pg):
    fake_pg.fetch_rows = [{"id": 1, "name": "kaue"}]
    await User().find().columns("id, name").fetch(True)
    sql = fake_pg.last_sql()
    assert sql.startswith("SELECT id, name FROM users")


async def test_columns_default_is_star(fake_pg):
    fake_pg.fetch_rows = []
    await User().find().fetch(True)
    assert fake_pg.last_sql().startswith("SELECT * FROM users")


async def test_columns_chains_with_filters(fake_pg):
    fake_pg.fetch_one_row = {"id": 1, "name": "kaue"}
    await (
        User()
        .find("role = :role", role="admin")
        .columns("id, name")
        .fetch()
    )
    sql = fake_pg.last_sql()
    assert sql.startswith("SELECT id, name FROM users")
    assert "WHERE (role = $1)" in sql


async def test_columns_does_not_affect_count(fake_pg):
    fake_pg.fetch_rows = [{"total": 7}]
    total = await User().find().columns("id, name").count()
    assert total == 7
    assert "COUNT(*)" in fake_pg.last_sql()


async def test_count_returns_total(fake_pg):
    fake_pg.fetch_rows = [{"total": 42}]
    total = await User().find("role = :r", r="admin").count()
    assert total == 42
    assert "COUNT(*)" in fake_pg.last_sql()


async def test_count_zero_when_empty(fake_pg):
    fake_pg.fetch_rows = []
    total = await User().find().count()
    assert total == 0


async def test_in_only_query(fake_maria):
    fake_maria.fetch_rows = []
    await User().find().in_("id", [10, 20]).fetch(True)
    sql, params = fake_maria.last_sql(), fake_maria.last_params()
    assert sql.endswith("WHERE id IN (%s, %s)")
    assert params == [10, 20]


def test_table_required_constructor_style():
    """Spec mostra `super().__init__('users', [...], 'user_id', True)`."""
    class Custom(DataLayer):
        def __init__(self):
            super().__init__("widgets", ["sku"], "widget_id", False)

    c = Custom()
    assert c._table == "widgets"
    assert c._required == ["sku"]
    assert c._primary_key == "widget_id"
    assert c._timestamps is False


def test_missing_table_raises():
    class Bare(DataLayer):
        pass
    with pytest.raises(ValueError):
        Bare()


def test_data_returns_dict_copy():
    u = User()
    u.name = "kaue"
    u.email = "k@x.com"
    d = u.data()
    assert d == {"name": "kaue", "email": "k@x.com"}
    # mutar copia nao afeta o model
    d["name"] = "outro"
    assert u.name == "kaue"


async def test_data_after_hydrate(fake_pg):
    fake_pg.fetch_one_row = {"id": 1, "name": "kaue", "email": "k@x.com"}
    user = await User().find_by_id(1)
    assert user.data() == {"id": 1, "name": "kaue", "email": "k@x.com"}


async def test_datetime_columns_coerced_to_iso_string_on_fetch_one(fake_pg):
    dt = datetime(2026, 4, 29, 12, 34, 56)
    fake_pg.fetch_one_row = {
        "id": 1,
        "name": "kaue",
        "email": "k@x.com",
        "created_at": dt,
        "updated_at": dt,
    }
    user = await User().find_by_id(1)
    assert user.created_at == "2026-04-29T12:34:56"
    assert user.updated_at == "2026-04-29T12:34:56"
    assert isinstance(user.data()["created_at"], str)


async def test_date_and_time_columns_coerced(fake_pg):
    fake_pg.fetch_one_row = {
        "id": 1,
        "name": "x",
        "email": "y@z.com",
        "birthday": date(1990, 5, 1),
        "wakeup": time(7, 30),
    }
    user = await User().find_by_id(1)
    assert user.birthday == "1990-05-01"
    assert user.wakeup == "07:30:00"


async def test_datetime_coerced_in_fetch_many(fake_pg):
    fake_pg.fetch_rows = [
        {"id": 1, "created_at": datetime(2026, 1, 1, 0, 0, 0)},
        {"id": 2, "created_at": datetime(2026, 2, 2, 0, 0, 0)},
    ]
    rows = await User().find().fetch(True)
    assert rows[0]["created_at"] == "2026-01-01T00:00:00"
    assert rows[1]["created_at"] == "2026-02-02T00:00:00"
