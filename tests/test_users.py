"""Tests para db.users (CRUD OAuth + local)."""

from __future__ import annotations

import importlib


def test_get_or_create_oauth_user(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    uid1 = users_mod.get_or_create_oauth_user(
        email="alice@example.com",
        oauth_provider="google",
        oauth_sub="sub_alice_123",
        display_name="Alice",
    )
    assert uid1 > 0

    # Mismo sub → mismo id
    uid2 = users_mod.get_or_create_oauth_user(
        email="alice@example.com",
        oauth_provider="google",
        oauth_sub="sub_alice_123",
        display_name="Alice",
    )
    assert uid1 == uid2


def test_different_users_get_different_ids(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    uid1 = users_mod.get_or_create_oauth_user(
        email="a@test.com",
        oauth_provider="google",
        oauth_sub="sub_a",
    )
    uid2 = users_mod.get_or_create_oauth_user(
        email="b@test.com",
        oauth_provider="google",
        oauth_sub="sub_b",
    )
    assert uid1 != uid2


def test_get_user_by_id(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    uid = users_mod.get_or_create_oauth_user(
        email="test@example.com",
        oauth_provider="google",
        oauth_sub="sub_test",
        display_name="Test User",
    )
    user = users_mod.get_user_by_id(uid)
    assert user is not None
    assert user["email"] == "test@example.com"
    assert user["display_name"] == "Test User"
    assert user["oauth_provider"] == "google"


def test_get_user_by_id_not_found(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    assert users_mod.get_user_by_id(9999) is None


def test_get_user_by_email(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    users_mod.get_or_create_oauth_user(
        email="findme@example.com",
        oauth_provider="google",
        oauth_sub="sub_findme",
    )
    user = users_mod.get_user_by_email("findme@example.com")
    assert user is not None
    assert user["oauth_sub"] == "sub_findme"


def test_get_user_by_email_not_found(tmp_db):
    import db.users as users_mod

    importlib.reload(users_mod)

    assert users_mod.get_user_by_email("nope@example.com") is None


def test_existing_email_links_oauth(tmp_db):
    """Si un email ya existe sin OAuth, vincular el nuevo OAuth sub."""
    import db.users as users_mod

    importlib.reload(users_mod)

    from db.database import connect, now_utc_iso

    # Crear usuario sin OAuth directamente
    with connect() as c:
        c.execute(
            "INSERT INTO users (email, created_at) VALUES (?, ?)",
            ("preexisting@example.com", now_utc_iso()),
        )
        pre_id = c.execute(
            "SELECT id FROM users WHERE email = ?", ("preexisting@example.com",)
        ).fetchone()[0]

    # Ahora vincular OAuth
    uid = users_mod.get_or_create_oauth_user(
        email="preexisting@example.com",
        oauth_provider="google",
        oauth_sub="sub_preexisting",
        display_name="Pre User",
    )
    assert uid == pre_id

    # Verificar que se vinculó
    user = users_mod.get_user_by_id(uid)
    assert user["oauth_provider"] == "google"
    assert user["oauth_sub"] == "sub_preexisting"


def test_watchlist_with_user_id(tmp_db):
    """Las entradas de watchlist se pueden vincular a un user_id."""
    import db.users as users_mod
    import db.watchlist as wl_mod

    importlib.reload(users_mod)
    importlib.reload(wl_mod)

    uid = users_mod.get_or_create_oauth_user(
        email="wl@example.com",
        oauth_provider="google",
        oauth_sub="sub_wl",
    )
    entry = wl_mod.WatchlistEntry(
        user_key="hash_wl",
        cpv_prefix="72",
        keyword="sap",
        user_id=uid,
    )
    wl_mod.add_entry(entry)

    # Buscar por user_key
    items = wl_mod.list_entries("hash_wl")
    assert len(items) == 1
    assert items[0]["user_id"] == uid

    # Buscar por user_id
    items2 = wl_mod.list_entries("different_key", user_id=uid)
    assert len(items2) == 1
    assert items2[0]["cpv_prefix"] == "72"


def test_log_access_oauth(tmp_db):
    """log_access registra un inicio de sesión OAuth."""
    import db.users as users_mod

    importlib.reload(users_mod)

    uid = users_mod.get_or_create_oauth_user(
        email="log@example.com",
        oauth_provider="google",
        oauth_sub="sub_log",
    )
    users_mod.log_access(auth_method="oauth", user_id=uid, email="log@example.com")

    from db.database import connect

    with connect() as c:
        rows = c.execute("SELECT * FROM access_log WHERE user_id = ?", (uid,)).fetchall()
    assert len(rows) == 1
    cols = [d[0] for d in c.execute("SELECT * FROM access_log LIMIT 0").description]
    row = dict(zip(cols, rows[0], strict=False))
    assert row["auth_method"] == "oauth"
    assert row["email"] == "log@example.com"
    assert row["logged_in_at"] is not None


def test_log_access_password(tmp_db):
    """log_access registra un inicio de sesión por password."""
    import db.users as users_mod

    importlib.reload(users_mod)

    users_mod.log_access(auth_method="password")

    from db.database import connect

    with connect() as c:
        rows = c.execute("SELECT * FROM access_log").fetchall()
    assert len(rows) == 1
    cols = [d[0] for d in c.execute("SELECT * FROM access_log LIMIT 0").description]
    row = dict(zip(cols, rows[0], strict=False))
    assert row["auth_method"] == "password"
    assert row["user_id"] is None
    assert row["email"] is None


def test_multiple_accesses_logged(tmp_db):
    """Múltiples accesos generan múltiples entradas."""
    import db.users as users_mod

    importlib.reload(users_mod)

    for _ in range(3):
        users_mod.log_access(auth_method="password")

    from db.database import connect

    with connect() as c:
        count = c.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    assert count == 3
