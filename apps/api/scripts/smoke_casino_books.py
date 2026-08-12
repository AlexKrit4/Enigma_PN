"""Isolate book-build smoke test without full app boot."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Minimal stubs so casino.py imports succeed
pkg = types.ModuleType("app")
pkg_services = types.ModuleType("app.services")
pkg_models = types.ModuleType("app.models")
pkg_entities = types.ModuleType("app.models.entities")
pkg_config = types.ModuleType("app.config")
pkg_happ = types.ModuleType("app.services.happ")
pkg_marz = types.ModuleType("app.services.marzban")
pkg_prov = types.ModuleType("app.services.provisioning")

pkg_config.Settings = type("Settings", (), {})
pkg_config.get_settings = lambda: pkg_config.Settings()
pkg_entities.CasinoSpin = type("CasinoSpin", (), {})
pkg_entities.Subscription = type("Subscription", (), {})
pkg_entities.User = type("User", (), {})
pkg_entities.SubscriptionStatus = types.SimpleNamespace(active="active", trial="trial", expired="expired")
pkg_happ.days_left = lambda *_a, **_k: 0
pkg_marz.MarzbanClient = object
pkg_marz.to_unix = lambda x: 0
pkg_prov._now = lambda: None
pkg_prov.get_active_subscription = lambda *a, **k: None
pkg_prov.serialize_subscription_with_devices = lambda *a, **k: None

sys.modules["app"] = pkg
sys.modules["app.config"] = pkg_config
sys.modules["app.models"] = pkg_models
sys.modules["app.models.entities"] = pkg_entities
sys.modules["app.services"] = pkg_services
sys.modules["app.services.happ"] = pkg_happ
sys.modules["app.services.marzban"] = pkg_marz
sys.modules["app.services.provisioning"] = pkg_prov

spec = importlib.util.spec_from_file_location(
    "app.services.casino",
    ROOT / "app/services/casino.py",
)
mod = importlib.util.module_from_spec(spec)
sys.modules["app.services.casino"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

books = mod.get_books()
print(
    "books",
    len(books),
    "sum",
    sum(b.win_days for b in books),
    "rtp",
    mod.books_rtp(),
    "bonus",
    sum(1 for b in books if b.is_bonus),
)
assert len(books) == mod.BOOK_COUNT
assert sum(b.win_days for b in books) == mod.TARGET_RETURN_DAYS
assert sum(1 for b in books if b.is_bonus) == mod.BONUS_BOOK_COUNT
print("OK")
