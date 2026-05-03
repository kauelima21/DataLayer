import pytest

from datalayer import DataLayer, ValidationError


class User(DataLayer):
    table = "users"
    required = ["name", "email"]
    timestamps = True


class NoTs(DataLayer):
    table = "things"
    required = ["name"]
    timestamps = False


async def test_save_insert_postgres_returning(fake_pg):
    fake_pg.insert_result = {
        "id": 1,
        "name": "kaue",
        "email": "k@x.com",
        "created_at": "x",
        "updated_at": "y",
    }
    u = User()
    u.name = "kaue"
    u.email = "k@x.com"
    saved = await u.save()
    assert saved.id == 1
    assert saved.name == "kaue"
    sql = fake_pg.last_sql()
    assert sql.startswith("INSERT INTO users")
    assert "RETURNING *" in sql


async def test_save_insert_populates_timestamps(fake_pg):
    fake_pg.insert_result = {"id": 1}
    u = User()
    u.name = "x"
    u.email = "y@z.com"
    await u.save()
    cols_sent = [c[0] for c in fake_pg.calls if c[0] == "insert"]
    assert cols_sent  # insert was called
    sql = fake_pg.last_sql()
    assert "created_at" in sql
    assert "updated_at" in sql


async def test_save_no_timestamps_when_disabled(fake_pg):
    fake_pg.insert_result = {"id": 1}
    t = NoTs()
    t.name = "abc"
    await t.save()
    sql = fake_pg.last_sql()
    assert "created_at" not in sql
    assert "updated_at" not in sql


async def test_save_validation_error_when_required_missing(fake_pg):
    u = User()
    u.name = "kaue"  # falta email
    with pytest.raises(ValidationError):
        await u.save()


async def test_save_validation_error_when_field_empty(fake_pg):
    u = User()
    u.name = ""
    u.email = "k@x.com"
    with pytest.raises(ValidationError):
        await u.save()


async def test_save_update_when_id_present(fake_pg):
    # registro pre-existente carregado via find_by_id; user altera "name"
    fake_pg.fetch_one_row = {
        "id": 5,
        "name": "antigo",
        "email": "k@x.com",
        "created_at": "2026-04-29T00:00:00",
    }
    u = await User().find_by_id(5)
    u.name = "novo"  # marca dirty
    fake_pg.fetch_one_row = {"id": 5, "name": "novo", "email": "k@x.com"}
    saved = await u.save()
    update_calls = [c for c in fake_pg.calls if c[0] == "execute"]
    assert len(update_calls) == 1
    update_sql = update_calls[0][1]
    assert update_sql.startswith("UPDATE users SET")
    assert "WHERE id =" in update_sql
    assert "updated_at" in update_sql
    assert "created_at" not in update_sql  # nunca alterado em UPDATE
    assert "email" not in update_sql  # nao foi modificado
    assert saved.name == "novo"


async def test_update_does_not_resend_hydrated_string_timestamps(fake_pg):
    """Regressao: created_at hidratado como ISO string nao deve voltar pro UPDATE
    (Postgres rejeitaria string em coluna TIMESTAMP)."""
    fake_pg.fetch_one_row = {
        "id": 1,
        "name": "kaue",
        "email": "k@x.com",
        "created_at": "2026-04-29T19:00:00",
        "updated_at": "2026-04-29T19:00:00",
    }
    u = await User().find_by_id(1)
    u.name = "novo nome"
    fake_pg.fetch_one_row = {"id": 1, "name": "novo nome", "email": "k@x.com"}
    await u.save()
    update_call = next(c for c in fake_pg.calls if c[0] == "execute")
    update_params = update_call[2]
    # nenhum param do UPDATE pode ser ISO string de timestamp hidratado
    string_params = [p for p in update_params if isinstance(p, str)]
    assert "2026-04-29T19:00:00" not in string_params


async def test_update_skips_db_when_nothing_dirty(fake_pg):
    fake_pg.fetch_one_row = {"id": 1, "name": "x", "email": "y@z.com"}
    u = await User().find_by_id(1)
    fake_pg.fetch_one_row = {"id": 1, "name": "x", "email": "y@z.com"}
    saved = await u.save()
    update_calls = [c for c in fake_pg.calls if c[0] == "execute"]
    assert len(update_calls) == 0  # nada modificado, sem UPDATE
    assert saved.name == "x"


class Country(DataLayer):
    table = "countries"
    required = ["code", "name"]
    primary_key = "code"
    timestamps = False


async def test_save_inserts_when_user_supplied_pk_does_not_exist(fake_pg):
    # PK nao auto-increment, registro inexistente -> INSERT, nao UPDATE
    fake_pg.fetch_rows = [{"total": 0}]  # exists check
    fake_pg.insert_result = {"code": "BR", "name": "Brasil"}
    c = Country()
    c.code = "BR"
    c.name = "Brasil"
    saved = await c.save()
    kinds = [k[0] for k in fake_pg.calls]
    assert "fetch" in kinds  # exists probe
    assert "insert" in kinds
    assert "execute" not in kinds  # nenhum UPDATE
    insert_sql = next(c[1] for c in fake_pg.calls if c[0] == "insert")
    assert insert_sql.startswith("INSERT INTO countries")
    assert "code" in insert_sql
    assert saved.code == "BR"


async def test_save_updates_when_user_supplied_pk_exists(fake_pg):
    # PK nao auto-increment, registro existente -> UPDATE
    fake_pg.fetch_rows = [{"total": 1}]
    fake_pg.fetch_one_row = {"code": "BR", "name": "Brasil Atualizado"}
    c = Country()
    c.code = "BR"
    c.name = "Brasil Atualizado"
    saved = await c.save()
    kinds = [k[0] for k in fake_pg.calls]
    assert "execute" in kinds
    assert "insert" not in kinds
    update_sql = next(c[1] for c in fake_pg.calls if c[0] == "execute")
    assert update_sql.startswith("UPDATE countries SET")
    assert "WHERE code =" in update_sql
    assert saved.code == "BR"


async def test_save_mariadb_uses_lastrowid_then_refetch(fake_maria):
    fake_maria.insert_result = 7  # lastrowid
    fake_maria.fetch_one_row = {"id": 7, "name": "kaue", "email": "k@x.com"}
    u = User()
    u.name = "kaue"
    u.email = "k@x.com"
    saved = await u.save()
    assert saved.id == 7
    kinds = [c[0] for c in fake_maria.calls]
    assert "insert" in kinds
    assert "fetch_one" in kinds
