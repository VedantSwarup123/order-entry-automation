"""Smoke test that project scaffolding is correct."""
from __future__ import annotations


def test_imports():
    """Verify all packages are importable."""
    import order_automation
    import pydantic
    import sqlalchemy
    import pandas
    import fastapi
    import click
    import structlog
    import tenacity
    import yaml
    assert True
