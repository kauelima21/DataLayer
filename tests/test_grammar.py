import pytest

from datalayer.grammar.mariadb import MariaDBGrammar
from datalayer.grammar.postgres import PostgresGrammar


def test_translate_postgres_named_to_dollar():
    g = PostgresGrammar()
    sql, params = g.translate("WHERE id = :id AND role = :role", {"id": 5, "role": "admin"})
    assert sql == "WHERE id = $1 AND role = $2"
    assert params == [5, "admin"]


def test_translate_mariadb_named_to_qmark():
    g = MariaDBGrammar()
    sql, params = g.translate("WHERE id = :id AND role = :role", {"id": 5, "role": "admin"})
    assert sql == "WHERE id = %s AND role = %s"
    assert params == [5, "admin"]


def test_translate_repeated_param_emits_each_position():
    g = PostgresGrammar()
    sql, params = g.translate("a = :x OR b = :x", {"x": 7})
    assert sql == "a = $1 OR b = $2"
    assert params == [7, 7]


def test_translate_missing_param_raises():
    g = PostgresGrammar()
    with pytest.raises(KeyError):
        g.translate(":missing", {})


def test_compile_select_no_filters():
    g = PostgresGrammar()
    sql, params = g.compile_select("users")
    assert sql == "SELECT * FROM users"
    assert params == []


def test_compile_select_with_condition_and_order_limit_offset():
    g = PostgresGrammar()
    sql, params = g.compile_select(
        "users",
        condition="role = :role",
        params={"role": "admin"},
        order="name ASC",
        limit=10,
        offset=20,
    )
    assert sql == "SELECT * FROM users WHERE (role = $1) ORDER BY name ASC LIMIT 10 OFFSET 20"
    assert params == ["admin"]


def test_compile_select_with_in_clause():
    g = PostgresGrammar()
    sql, params = g.compile_select("users", in_clause=("id", [1, 2, 3]))
    assert sql == "SELECT * FROM users WHERE id IN ($1, $2, $3)"
    assert params == [1, 2, 3]


def test_compile_select_combines_condition_and_in():
    g = MariaDBGrammar()
    sql, params = g.compile_select(
        "users",
        condition="role = :role",
        params={"role": "admin"},
        in_clause=("id", [1, 2]),
    )
    assert sql == "SELECT * FROM users WHERE (role = %s) AND id IN (%s, %s)"
    assert params == ["admin", 1, 2]


def test_compile_count():
    g = PostgresGrammar()
    sql, params = g.compile_count("users", condition="role = :r", params={"r": "x"})
    assert sql == "SELECT COUNT(*) AS total FROM users WHERE (role = $1)"
    assert params == ["x"]


def test_compile_insert_postgres_returning():
    g = PostgresGrammar()
    sql, params, returning = g.compile_insert("users", {"name": "kaue", "email": "k@x.com"})
    assert returning is True
    assert sql == "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *"
    assert params == ["kaue", "k@x.com"]


def test_compile_insert_mariadb_no_returning():
    g = MariaDBGrammar()
    sql, params, returning = g.compile_insert("users", {"name": "kaue"})
    assert returning is False
    assert sql == "INSERT INTO users (name) VALUES (%s)"
    assert params == ["kaue"]


def test_compile_update():
    g = PostgresGrammar()
    sql, params = g.compile_update(
        "users",
        data={"name": "novo", "email": "n@x.com"},
        condition="id = :__pk",
        condition_params={"__pk": 5},
    )
    # condition_params traduz primeiro pq aparece antes do SET
    assert "UPDATE users SET name =" in sql
    assert "WHERE id =" in sql
    # __pk vira $1 (primeiro :__pk no SQL e o do WHERE; mas no SET ja vem com __set_*)
    # ordem real: SQL = "UPDATE users SET name = :__set_name, email = :__set_email WHERE id = :__pk"
    assert sql == (
        "UPDATE users SET name = $1, email = $2 WHERE id = $3"
    )
    assert params == ["novo", "n@x.com", 5]


def test_compile_delete_with_condition():
    g = PostgresGrammar()
    sql, params = g.compile_delete("users", condition="id = :id", params={"id": 5})
    assert sql == "DELETE FROM users WHERE (id = $1)"
    assert params == [5]


def test_compile_delete_with_in():
    g = MariaDBGrammar()
    sql, params = g.compile_delete("users", in_clause=("id", [1, 2]))
    assert sql == "DELETE FROM users WHERE id IN (%s, %s)"
    assert params == [1, 2]
