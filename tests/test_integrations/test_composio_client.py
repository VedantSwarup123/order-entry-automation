"""Smoke tests for the Composio integration wrapper."""
from __future__ import annotations

from order_automation.integrations.composio_client import (
    COMPOSIO_AVAILABLE,
    _mock_response,
    execute_action,
)


def test_mock_response_fetch():
    """Fetch-type actions return empty lists."""
    resp = _mock_response("GMAIL_FETCH_EMAILS", {})
    assert resp["emails"] == []


def test_mock_response_send():
    """Write-type actions return success."""
    resp = _mock_response("SLACK_SEND_MESSAGE", {})
    assert resp["success"] is True


def test_mock_response_sheets_get():
    """Sheets get returns empty rows."""
    resp = _mock_response("GOOGLESHEETS_GET_SPREADSHEET_DATA", {})
    assert resp["values"] == []


def test_execute_action_without_composio():
    """execute_action returns mock data when Composio is unavailable."""
    result = execute_action("GMAIL_FETCH_EMAILS", {"query": "subject:order"})
    assert isinstance(result, dict)
    # Should contain emails key with empty list (mock)
    if not COMPOSIO_AVAILABLE:
        assert result["emails"] == []


def test_composio_available_is_bool():
    """COMPOSIO_AVAILABLE is a boolean."""
    assert isinstance(COMPOSIO_AVAILABLE, bool)
