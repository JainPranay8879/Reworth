"""Integration and security tests (TC-06 to TC-12 and extras)."""
import re
import sqlite3

from conftest import GOOD, csrf, register


def assess(client, token, **over):
    return client.post("/api/assess", data={**GOOD, **over, "csrf_token": token})


# ---- validation ----
def test_tc06_missing_required_field(client):
    t = csrf(client, "/assess")
    r = assess(client, t, product_name="")
    assert r.status_code == 400 and "required" in r.get_json()["error"]


def test_tc07_negative_age_and_cost_rejected(client):
    t = csrf(client, "/assess")
    assert assess(client, t, age="-1").status_code == 400
    assert assess(client, t, repair_cost="-5").status_code == 400
    assert assess(client, t, replacement_cost="0").status_code == 400
    assert assess(client, t, age="abc").status_code == 400


def test_invalid_category_and_long_text_rejected(client):
    t = csrf(client, "/assess")
    assert assess(client, t, category="Weapons").status_code == 400
    assert assess(client, t, product_name="x" * 500).status_code == 400


# ---- persistence ----
def test_tc08_logged_out_assessment_not_saved(client, app_module):
    t = csrf(client, "/assess")
    r = assess(client, t)
    assert r.status_code == 200 and r.get_json()["saved"] is False
    conn = sqlite3.connect(app_module.DB_PATH)
    assert conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0] == 0


def test_tc09_logged_in_assessment_saved_and_in_dashboard(client):
    register(client)
    t = csrf(client, "/assess")
    r = assess(client, t)
    assert r.get_json()["saved"] is True
    assert "Old phone" in client.get("/dashboard").get_data(as_text=True)


def test_tc10_empty_dashboard(client):
    register(client)
    assert client.get("/dashboard").status_code == 200


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


# ---- auth ----
def test_register_login_logout(client):
    register(client)
    client.get("/logout")
    t = csrf(client)
    bad = client.post("/login", data={"email": "a@example.com", "password": "wrong", "csrf_token": t}, follow_redirects=True)
    assert "incorrect" in bad.get_data(as_text=True)
    ok = client.post("/login", data={"email": "a@example.com", "password": "password123", "csrf_token": t})
    assert ok.status_code == 302 and "/dashboard" in ok.headers["Location"]


def test_password_is_hashed(client, app_module):
    register(client)
    conn = sqlite3.connect(app_module.DB_PATH)
    stored = conn.execute("SELECT password_hash FROM users WHERE email='a@example.com'").fetchone()[0]
    assert stored != "password123" and stored.startswith(("scrypt:", "pbkdf2:"))


def test_short_password_rejected(client):
    register(client, password="short")
    assert client.get("/dashboard").status_code == 302


def test_duplicate_email_rejected(client):
    register(client)
    client.get("/logout")
    r = register(client)
    assert r.status_code == 302 and "/dashboard" not in r.headers["Location"]


def test_login_throttling(client):
    register(client)
    client.get("/logout")
    t = csrf(client)
    for _ in range(5):
        client.post("/login", data={"email": "a@example.com", "password": "bad", "csrf_token": t})
    r = client.post("/login", data={"email": "a@example.com", "password": "password123", "csrf_token": t}, follow_redirects=True)
    assert "Too many failed attempts" in r.get_data(as_text=True)


# ---- security ----
def test_csrf_blocks_post_without_token(client):
    r = client.post("/login", data={"email": "a@example.com", "password": "x"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    assert client.post("/api/assess", data=GOOD).status_code == 400


def test_security_headers_present(client):
    h = client.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY"


def test_sql_injection_string_is_harmless(client, app_module):
    t = csrf(client)
    client.post("/login", data={"email": "' OR 1=1 --", "password": "' OR 1=1 --", "csrf_token": t})
    assert "user_id" not in client.get("/dashboard").request.environ.get("HTTP_COOKIE", "")
    assert client.get("/dashboard").status_code == 302


def test_xss_is_escaped_in_dashboard(client):
    register(client)
    t = csrf(client, "/assess")
    assess(client, t, product_name="<script>alert(1)</script>")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_regular_user_cannot_open_admin(client):
    register(client)
    assert client.get("/admin").status_code == 302
    assert "/dashboard" in client.get("/admin").headers["Location"]


def test_csv_formula_injection_neutralised(app_module):
    assert app_module.csv_safe("=1+1") == "'=1+1"
    assert app_module.csv_safe("Phone") == "Phone"


def test_unknown_route_404_page(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "ERROR 404" in r.get_data(as_text=True)


# ---- admin ----
def admin_login(client):
    t = csrf(client, "/admin/login")
    return client.post("/admin/login", data={"email": "admin@reworth.local", "password": "ReWorth@123", "csrf_token": t})


def test_admin_login_dashboard_and_export(client):
    r = admin_login(client)
    assert r.status_code == 302
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/export.csv").mimetype == "text/csv"


def test_admin_can_generate_reset_link_and_user_can_use_it(client, app_module):
    register(client, email="u@example.com")
    client.get("/logout")
    admin_login(client)
    conn = sqlite3.connect(app_module.DB_PATH)
    uid = conn.execute("SELECT id FROM users WHERE email='u@example.com'").fetchone()[0]
    t = csrf(client, "/admin/users")
    page = client.post(f"/admin/users/{uid}/reset-link", data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
    token = re.search(r"/reset-password/([\w\-]+)", page).group(1)
    client.get("/logout")
    t = csrf(client, f"/reset-password/{token}")
    client.post(f"/reset-password/{token}", data={"password": "newpassword1", "confirm_password": "newpassword1", "csrf_token": t})
    t = csrf(client)
    ok = client.post("/login", data={"email": "u@example.com", "password": "newpassword1", "csrf_token": t})
    assert "/dashboard" in ok.headers["Location"]
    # token is single-use
    assert "invalid, expired or has already been used" in client.get(f"/reset-password/{token}").get_data(as_text=True)


# ---- password reset modes ----
def load_app(monkeypatch, tmp_path, **env):
    import importlib, sys
    monkeypatch.setenv("REWORTH_DB_PATH", str(tmp_path / "m.db"))
    for k in ("REWORTH_ENV", "REWORTH_DEMO_MODE", "REWORTH_ADMIN_PASSWORD", "REWORTH_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_default_mode_is_secure_no_demo_ui_no_direct_reset(client):
    forgot = client.get("/forgot-password").get_data(as_text=True)
    assert "Send reset link" in forgot and 'name="confirm_password"' not in forgot
    admin_page = client.get("/admin/login").get_data(as_text=True)
    assert "Use demo admin" not in admin_page and "ReWorth@123" not in admin_page


def test_default_reset_request_prints_link_to_console(client, capsys):
    register(client, email="u@example.com")
    client.get("/logout")
    t = csrf(client, "/forgot-password")
    r = client.post("/forgot-password", data={"email": "u@example.com", "csrf_token": t}, follow_redirects=True)
    assert "If that email is registered" in r.get_data(as_text=True)
    assert "/reset-password/" in capsys.readouterr().out


def test_demo_mode_is_opt_in_and_blocks_admin_reset(monkeypatch, tmp_path):
    mod = load_app(monkeypatch, tmp_path, REWORTH_DEMO_MODE="1")
    c = mod.app.test_client()
    assert "Use demo admin" in c.get("/admin/login").get_data(as_text=True)
    assert 'name="confirm_password"' in c.get("/forgot-password").get_data(as_text=True)
    t = csrf(c, "/forgot-password")
    c.post("/forgot-password", data={"email": "admin@reworth.local", "password": "hacked1234",
                                     "confirm_password": "hacked1234", "csrf_token": t})
    t = csrf(c, "/admin/login")
    r = c.post("/admin/login", data={"email": "admin@reworth.local", "password": "hacked1234", "csrf_token": t}, follow_redirects=True)
    assert "incorrect" in r.get_data(as_text=True)
    import sys; sys.modules.pop("app", None)


def test_production_mode_requires_secret_and_disables_direct_reset(monkeypatch, tmp_path):
    import importlib, sys
    monkeypatch.setenv("REWORTH_ENV", "production")
    monkeypatch.setenv("REWORTH_DB_PATH", str(tmp_path / "p.db"))
    monkeypatch.delenv("REWORTH_SECRET_KEY", raising=False)
    sys.modules.pop("app", None)
    try:
        importlib.import_module("app")
        raise AssertionError("production start-up should fail without a secret key")
    except RuntimeError:
        pass
    monkeypatch.setenv("REWORTH_SECRET_KEY", "x" * 40)
    monkeypatch.setenv("REWORTH_ADMIN_PASSWORD", "StrongAdminPass1")
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    assert mod.DEMO_MODE is False
    c = mod.app.test_client()
    t = csrf(c, "/forgot-password")
    r = c.post("/forgot-password", data={"email": "nobody@example.com", "csrf_token": t}, follow_redirects=True)
    assert "If that email is registered" in r.get_data(as_text=True)
    assert 'name="confirm_password"' not in c.get("/forgot-password").get_data(as_text=True)
    assert "ReWorth@123" not in c.get("/admin/login").get_data(as_text=True)
    sys.modules.pop("app", None)


# ---- ops ----
def test_tc12_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_tc11_migration_from_old_database(monkeypatch, tmp_path):
    import importlib, sys
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, product_name TEXT NOT NULL,
        category TEXT NOT NULL, age INTEGER NOT NULL, condition TEXT NOT NULL, problem TEXT NOT NULL, repair_history TEXT NOT NULL,
        repair_cost REAL, replacement_cost REAL, decision TEXT NOT NULL, score INTEGER NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);""")
    conn.commit(); conn.close()
    monkeypatch.setenv("REWORTH_DB_PATH", str(db))
    monkeypatch.delenv("REWORTH_ENV", raising=False)
    sys.modules.pop("app", None)
    importlib.import_module("app")
    cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(assessments)")}
    assert {"confidence", "functional_condition", "next_step"} <= cols
    assert "role" in {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(users)")}
    sys.modules.pop("app", None)
