import importlib
import os
import pytest


def test_base_url_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_BASE_URL", "http://example.com/api")
    import whatsapp as w
    importlib.reload(w)
    assert w.WHATSAPP_API_BASE_URL == "http://example.com/api"
