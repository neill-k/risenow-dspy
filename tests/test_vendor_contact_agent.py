from types import SimpleNamespace

import pytest

from agents import vendor_contact_agent as vca


class _BudgetRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, limit=None):
        self.calls.append(limit)
        return self

    def __enter__(self):  # pragma: no cover - context manager protocol
        return None

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover
        return False


def test_lookup_vendor_contacts_normalizes_prediction(monkeypatch):
    recorder = _BudgetRecorder()
    monkeypatch.setattr(vca, "scoped_tavily_extract_budget", recorder)

    stub_calls = []

    class StubAgent:
        def __call__(self, **kwargs):
            stub_calls.append(kwargs)
            return SimpleNamespace(
                contact_emails=[{"email": "info@acme.com", "description": "info"}],
                phone_numbers=[{"number": "+15551234567", "description": "main"}],
                supporting_urls=["https://acme.com/contact"],
                summary="Found official contact details.",
            )

    monkeypatch.setattr(vca, "_get_cached_contact_agent", lambda max_iters=vca.DEFAULT_MAX_ITERS: StubAgent())

    payload = vca.lookup_vendor_contacts(
        "Acme Corp",
        vendor_website="https://acme.com",
        country_or_region="United States",
        extract_limit=5,
    )

    assert payload["contact_emails"][0]["email"] == "info@acme.com"
    assert payload["phone_numbers"][0]["number"] == "+15551234567"
    assert payload["supporting_urls"] == ["https://acme.com/contact"]
    assert payload["summary"] == "Found official contact details."

    assert recorder.calls == [5]
    assert stub_calls[0]["vendor_website"] == "https://acme.com"
    assert stub_calls[0]["country_or_region"] == "United States"


def test_lookup_vendor_contacts_validation_fallback(monkeypatch):
    recorder = _BudgetRecorder()
    monkeypatch.setattr(vca, "scoped_tavily_extract_budget", recorder)

    class StubAgent:
        def __call__(self, **kwargs):
            return SimpleNamespace(
                contact_emails=object(),
                phone_numbers=object(),
                supporting_urls=object(),
                summary="bad data",
            )

    monkeypatch.setattr(vca, "_get_cached_contact_agent", lambda max_iters=vca.DEFAULT_MAX_ITERS: StubAgent())

    payload = vca.lookup_vendor_contacts("Broken Vendor", extract_limit=None)

    assert payload["contact_emails"] == []
    assert payload["phone_numbers"] == []
    assert payload["supporting_urls"] == []
    assert "unparsable" in payload["summary"].lower()
    assert recorder.calls == [None]


def test_lookup_vendor_contacts_requires_vendor_name():
    with pytest.raises(ValueError):
        vca.lookup_vendor_contacts("")


def test_create_vendor_contact_tool_delegates(monkeypatch):
    captured: dict[str, object] = {}

    def fake_lookup(
        vendor_name,
        vendor_website=None,
        country_or_region=None,
        *,
        max_iters,
        extract_limit,
    ):
        captured.update(
            {
                "vendor_name": vendor_name,
                "vendor_website": vendor_website,
                "country_or_region": country_or_region,
                "max_iters": max_iters,
                "extract_limit": extract_limit,
            }
        )
        return {"ok": True}

    monkeypatch.setattr(vca, "lookup_vendor_contacts", fake_lookup)

    tool = vca.create_vendor_contact_tool(max_iters=7, extract_limit=2)

    assert tool.name == "lookup_vendor_contacts"
    result = tool.func(
        vendor_name="Acme Co",
        vendor_website="https://acme.example",
        country_or_region="Canada",
    )

    assert result == {"ok": True}
    assert captured["vendor_name"] == "Acme Co"
    assert captured["vendor_website"] == "https://acme.example"
    assert captured["country_or_region"] == "Canada"
    assert captured["max_iters"] == 7
    assert captured["extract_limit"] == 2
