import os
from datetime import datetime, timezone

import pytest

from datalayer import DataLayer
from datalayer.connection import Connection


class User(DataLayer):
    table = "users"
    required = ["name"]


def test_default_timezone_is_sao_paulo(monkeypatch):
    monkeypatch.delenv("DATA_LAYER_TIMEZONE", raising=False)
    Connection._timezone = None
    tz = Connection.timezone()
    assert str(tz) == "America/Sao_Paulo"


def test_timezone_overridable_via_env(monkeypatch):
    monkeypatch.setenv("DATA_LAYER_TIMEZONE", "UTC")
    Connection._timezone = None
    tz = Connection.timezone()
    assert str(tz) == "UTC"


def test_set_timezone_programmatic():
    Connection.set_timezone("Europe/Lisbon")
    assert str(Connection.timezone()) == "Europe/Lisbon"
    Connection._timezone = None


async def test_aware_datetime_converted_to_configured_tz(fake_pg):
    Connection.set_timezone("America/Sao_Paulo")
    # 12:00 UTC = 09:00 SP (UTC-3)
    dt_utc = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    fake_pg.fetch_one_row = {"id": 1, "name": "x", "created_at": dt_utc}
    user = await User().find_by_id(1)
    assert user.created_at.startswith("2026-04-29T09:00:00")
    assert "-03:00" in user.created_at


async def test_naive_datetime_passes_through_iso(fake_pg):
    Connection.set_timezone("America/Sao_Paulo")
    dt_naive = datetime(2026, 4, 29, 12, 0, 0)
    fake_pg.fetch_one_row = {"id": 1, "name": "x", "created_at": dt_naive}
    user = await User().find_by_id(1)
    assert user.created_at == "2026-04-29T12:00:00"


async def test_save_uses_configured_tz_for_now(fake_pg):
    Connection.set_timezone("America/Sao_Paulo")
    fake_pg.insert_result = {"id": 1, "name": "x"}
    u = User()
    u.name = "x"
    await u.save()
    insert_call = next(c for c in fake_pg.calls if c[0] == "insert")
    params = insert_call[2]
    # ultimos 2 params sao created_at e updated_at (datetime objs)
    dts = [p for p in params if isinstance(p, datetime)]
    assert len(dts) == 2
    # naive (tzinfo strip) mas hora deve corresponder a SP, nao UTC
    sp_now = datetime.now(Connection.timezone()).replace(tzinfo=None)
    delta = abs((dts[0] - sp_now).total_seconds())
    assert delta < 5  # margem
