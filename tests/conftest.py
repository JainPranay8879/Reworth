import importlib
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def app_module(monkeypatch):
    """Fresh app + fresh temporary database for every test (demo mode)."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("REWORTH_DB_PATH", str(Path(tmp) / "test.db"))
    monkeypatch.delenv("REWORTH_ENV", raising=False)
    monkeypatch.delenv("REWORTH_DEMO_MODE", raising=False)
    monkeypatch.delenv("REWORTH_ADMIN_PASSWORD", raising=False)
    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True
    module._FAILED.clear()
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def csrf(client, path="/"):
    """Fetch a page and return the CSRF token embedded in its forms."""
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


GOOD = {
    "product_name": "Old phone", "category": "Mobile / Tablet", "age": "2",
    "condition": "Good", "functional_condition": "Works normally",
    "cosmetic_condition": "Minor wear", "problem_type": "Minor / occasional issue",
    "repair_history": "Never repaired", "usage_frequency": "Sometimes",
    "repair_cost": "500", "replacement_cost": "15000",
}


def register(client, email="a@example.com", password="password123", name="Asha Rao"):
    token = csrf(client)
    return client.post("/register", data={"name": name, "email": email, "password": password, "csrf_token": token})
