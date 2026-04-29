import pytest

from datalayer import DataLayer


class User(DataLayer):
    table = "users"
    required = ["name"]


async def test_destroy_via_loaded_record(fake_pg):
    fake_pg.execute_affected = 1
    u = User()
    u._data = {"id": 5, "name": "x"}
    ok = await u.destroy()
    assert ok is True
    sql, params = fake_pg.last_sql(), fake_pg.last_params()
    assert sql == "DELETE FROM users WHERE (id = $1)"
    assert params == [5]


async def test_destroy_via_find(fake_pg):
    fake_pg.execute_affected = 3
    ok = await User().find("active = :a", a=False).destroy()
    assert ok is True
    sql, params = fake_pg.last_sql(), fake_pg.last_params()
    assert sql == "DELETE FROM users WHERE (active = $1)"
    assert params == [False]


async def test_destroy_returns_false_when_nothing_affected(fake_pg):
    fake_pg.execute_affected = 0
    ok = await User().find("id = :id", id=999).destroy()
    assert ok is False


async def test_destroy_without_target_raises(fake_pg):
    with pytest.raises(ValueError):
        await User().destroy()


async def test_destroy_via_in_clause(fake_maria):
    fake_maria.execute_affected = 2
    ok = await User().find().in_("id", [1, 2]).destroy()
    assert ok is True
    sql, params = fake_maria.last_sql(), fake_maria.last_params()
    assert sql == "DELETE FROM users WHERE id IN (%s, %s)"
    assert params == [1, 2]
