import pytest

try:
    from fastapi.testclient import TestClient
    fastapi_available = True
except Exception:  # pragma: no cover
    fastapi_available = False


@pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")
def test_search_contacts_endpoint(monkeypatch):
    import whatsapp_mcp_server.main as m

    # monkeypatch the underlying function to avoid DB access
    monkeypatch.setattr(m, "search_contacts", lambda query: [{"jid": "1", "name": "Alice"}])

    app = m.create_app()
    client = TestClient(app)

    resp = client.post("/search_contacts", json={"query": "Ali"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["jid"] == "1"
