"""Basic tests for CLI commands — verify they don't crash."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from order_automation.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Order Entry Automation CLI" in result.output


def test_stats_no_db():
    runner = CliRunner()
    result = runner.invoke(cli, ["stats"])
    assert result.exit_code == 0


def test_failures_no_db():
    runner = CliRunner()
    result = runner.invoke(cli, ["failures"])
    assert result.exit_code == 0


def test_status_nonexistent():
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "nonexistent-id"])
    assert result.exit_code == 0
    assert "not found" in result.output


def test_test_connections():
    runner = CliRunner()
    result = runner.invoke(cli, ["test-connections"])
    assert result.exit_code == 0
    assert "Composio connected" in result.output


def test_run_csv_no_files():
    """Patch APScheduler import so run does a single poll instead of blocking."""
    with patch.dict("sys.modules", {"apscheduler": None, "apscheduler.schedulers": None, "apscheduler.schedulers.blocking": None}):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--source", "csv"])
        assert result.exit_code == 0
