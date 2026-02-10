"""CLI entry-point for the Order Entry Automation system.

Usage:
    order-auto run                    Start all enabled ingest sources
    order-auto run --source csv       Single source only
    order-auto ingest <filepath>      Manually process one file
    order-auto status <order-id>      Look up order in DB
    order-auto failures               List failed orders
    order-auto retry <order-id>       Re-run pipeline on failed order
    order-auto stats                  Print order counts by status/source
    order-auto test-connections       Verify Composio connections
    order-auto api                    Start FastAPI server
    order-auto ui                     Start Streamlit UI
"""
from __future__ import annotations

import signal
import sys
from pathlib import Path

import click
import structlog
import yaml

from order_automation.engine.normalizer import OrderNormalizer
from order_automation.engine.pipeline import OrderPipeline
from order_automation.engine.router import OrderRouter
from order_automation.engine.validator import OrderValidator
from order_automation.ingest.csv_ingest import CSVIngest
from order_automation.integrations.composio_client import is_connected
from order_automation.output.database import DatabaseAdapter
from order_automation.output.erp import ERPAdapter
from order_automation.output.notifications import EmailConfirmation, SlackNotifier
from order_automation.output.sheets_output import SheetsOutputAdapter
from order_automation.output.web_portal import WebPortalAdapter

log = structlog.get_logger()


# ------------------------------------------------------------------
# Config helpers
# ------------------------------------------------------------------

def _load_config(path: str = "config/settings.yaml") -> dict:
    """Load the master settings file."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}


def _build_pipeline(cfg: dict) -> OrderPipeline:
    """Construct the pipeline with all adapters from config."""
    db_url = cfg.get("database", {}).get("url", "sqlite:///orders.db")
    router_path = cfg.get("routing", {}).get("rules_file", "config/routing_rules.yaml")

    router = OrderRouter()
    if Path(router_path).exists():
        router.load(router_path)

    pipeline = OrderPipeline(
        normalizer=OrderNormalizer(),
        validator=OrderValidator(),
        router=router,
    )

    # Register adapters
    out_cfg = cfg.get("output", {})

    if out_cfg.get("database", {}).get("enabled", True):
        pipeline.register_adapter("database", DatabaseAdapter(url=db_url))

    if out_cfg.get("sheets", {}).get("enabled", False):
        pipeline.register_adapter("sheets", SheetsOutputAdapter(
            spreadsheet_id=out_cfg["sheets"].get("spreadsheet_id", ""),
            sheet_name=out_cfg["sheets"].get("sheet_name", "OrderLog"),
        ))

    if out_cfg.get("slack", {}).get("enabled", False):
        pipeline.register_adapter("slack_notify", SlackNotifier(
            channel=out_cfg["slack"].get("channel", "#orders"),
        ))

    if out_cfg.get("email_confirmation", {}).get("enabled", False):
        pipeline.register_adapter("email_confirmation", EmailConfirmation())

    if out_cfg.get("erp", {}).get("enabled", False):
        pipeline.register_adapter("erp", ERPAdapter(
            base_url=out_cfg["erp"].get("base_url", ""),
        ))

    if out_cfg.get("web_portal", {}).get("enabled", False):
        pipeline.register_adapter("web_portal", WebPortalAdapter(
            base_url=out_cfg["web_portal"].get("base_url", ""),
        ))

    return pipeline


def _get_db(cfg: dict) -> DatabaseAdapter:
    """Get a DatabaseAdapter from config."""
    db_url = cfg.get("database", {}).get("url", "sqlite:///orders.db")
    return DatabaseAdapter(url=db_url)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Order Entry Automation CLI."""


@cli.command()
@click.option("--source", default=None, help="Run a single ingest source (csv, email, sheets, fax)")
def run(source: str | None) -> None:
    """Start all enabled ingest sources (or a single one)."""
    cfg = _load_config()
    pipeline = _build_pipeline(cfg)
    ingest_cfg = cfg.get("ingest", {})

    # Graceful shutdown
    running = True

    def _shutdown(sig, frame):
        nonlocal running
        running = False
        click.echo("\nShutting down…")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        scheduler = BlockingScheduler()
    except ImportError:
        click.echo("APScheduler not available; running single poll cycle.")
        scheduler = None

    sources_to_run = [source] if source else []
    if not sources_to_run:
        for name in ("csv", "email", "sheets", "fax"):
            if ingest_cfg.get(name, {}).get("enabled", False):
                sources_to_run.append(name)

    if not sources_to_run:
        click.echo("No ingest sources enabled. Enable them in config/settings.yaml.")
        return

    def _poll_csv():
        csv_cfg = ingest_cfg.get("csv", {})
        ing = CSVIngest(
            watch_dir=csv_cfg.get("watch_dir", "inbox/csv"),
            processed_dir=csv_cfg.get("processed_dir", "processed/csv"),
            column_mapping=csv_cfg.get("column_mapping"),
        )
        raws = ing.poll()
        for raw in raws:
            orders = ing.parse(raw)
            for order in orders:
                result = pipeline.process(order)
                click.echo(f"  [{result.status.value}] {result.po_number} — {result.total_amount}")
            if raw.source_ref:
                ing.move_to_processed(raw.source_ref)

    def _poll_email():
        from order_automation.ingest.email_ingest import EmailIngest
        provider = ingest_cfg.get("email", {}).get("provider", "gmail")
        ing = EmailIngest(provider=provider)
        raws = ing.poll()
        for raw in raws:
            orders = ing.parse(raw)
            for order in orders:
                pipeline.process(order)
            if raw.source_ref:
                ing.mark_read(raw.source_ref)

    def _poll_sheets():
        from order_automation.ingest.sheets_ingest import SheetsIngest
        sheets_cfg = ingest_cfg.get("sheets", {})
        ing = SheetsIngest(
            spreadsheet_id=sheets_cfg.get("spreadsheet_id", ""),
            sheet_name=sheets_cfg.get("sheet_name", "Orders"),
            column_mapping=sheets_cfg.get("column_mapping"),
        )
        raws = ing.poll()
        for raw in raws:
            orders = ing.parse(raw)
            for order in orders:
                pipeline.process(order)

    def _poll_fax():
        from order_automation.ingest.fax_ingest import FaxIngest
        fax_cfg = ingest_cfg.get("fax", {})
        ing = FaxIngest(
            watch_dir=fax_cfg.get("watch_dir", "inbox/fax"),
            processed_dir=fax_cfg.get("processed_dir", "processed/fax"),
            review_dir=fax_cfg.get("review_dir", "review/fax"),
            min_confidence=fax_cfg.get("min_confidence", 0.6),
        )
        raws = ing.poll()
        for raw in raws:
            orders = ing.parse(raw)
            for order in orders:
                pipeline.process(order)

    poll_funcs = {
        "csv": _poll_csv,
        "email": _poll_email,
        "sheets": _poll_sheets,
        "fax": _poll_fax,
    }

    if scheduler is None:
        # Single poll
        for name in sources_to_run:
            fn = poll_funcs.get(name)
            if fn:
                click.echo(f"Polling {name}…")
                fn()
        return

    for name in sources_to_run:
        fn = poll_funcs.get(name)
        if fn is None:
            continue
        interval = ingest_cfg.get(name, {}).get("poll_interval_seconds", 30)
        scheduler.add_job(fn, "interval", seconds=interval, id=f"poll_{name}")
        click.echo(f"Scheduled {name} every {interval}s")

    click.echo("Running… Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)


@cli.command()
@click.argument("filepath")
def ingest(filepath: str) -> None:
    """Manually process a single CSV/Excel file."""
    cfg = _load_config()
    pipeline = _build_pipeline(cfg)
    csv_cfg = cfg.get("ingest", {}).get("csv", {})
    ing = CSVIngest(
        watch_dir=Path(filepath).parent,
        processed_dir=csv_cfg.get("processed_dir", "processed/csv"),
        column_mapping=csv_cfg.get("column_mapping"),
    )
    import pandas as pd
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath, engine="openpyxl")

    from order_automation.models.order import OrderSource, RawOrder
    raw = RawOrder(
        source=OrderSource.csv,
        source_ref=filepath,
        rows=df.dropna(how="all").to_dict(orient="records"),
        metadata={"filename": Path(filepath).name},
    )
    orders = ing.parse(raw)
    for order in orders:
        result = pipeline.process(order)
        click.echo(f"[{result.status.value}] {result.po_number} — ${result.total_amount}")


@cli.command()
@click.argument("order_id")
def status(order_id: str) -> None:
    """Look up an order by ID in the database."""
    cfg = _load_config()
    db = _get_db(cfg)
    record = db.get_order(order_id)
    if record is None:
        click.echo(f"Order {order_id} not found.")
        return
    click.echo(f"ID:       {record.id}")
    click.echo(f"PO:       {record.po_number}")
    click.echo(f"Customer: {record.customer_name} ({record.customer_id})")
    click.echo(f"Status:   {record.status}")
    click.echo(f"Total:    {record.total_amount}")
    click.echo(f"Source:   {record.source}")
    click.echo(f"Created:  {record.created_at}")
    if record.errors:
        click.echo(f"Errors:   {record.errors}")


@cli.command()
def failures() -> None:
    """List failed orders."""
    cfg = _load_config()
    db = _get_db(cfg)
    failed = db.get_failures()
    if not failed:
        click.echo("No failed orders.")
        return
    for r in failed:
        click.echo(f"  {r.id}  PO={r.po_number}  err={r.errors}")


@cli.command()
@click.argument("order_id")
def retry(order_id: str) -> None:
    """Re-run the pipeline on a failed order."""
    cfg = _load_config()
    db = _get_db(cfg)
    record = db.get_order(order_id)
    if record is None:
        click.echo(f"Order {order_id} not found.")
        return
    click.echo(f"Retry not yet implemented for persisted orders (order {order_id}).")


@cli.command()
def stats() -> None:
    """Print order counts by status."""
    cfg = _load_config()
    db = _get_db(cfg)
    s = db.get_stats()
    if not s:
        click.echo("No orders in database.")
        return
    for status_val, count in sorted(s.items()):
        click.echo(f"  {status_val}: {count}")


@cli.command("test-connections")
def test_connections() -> None:
    """Verify Composio connections."""
    connected = is_connected()
    click.echo(f"Composio connected: {connected}")


@cli.command()
def api() -> None:
    """Start the FastAPI server."""
    cfg = _load_config()
    pipeline = _build_pipeline(cfg)
    api_cfg = cfg.get("ingest", {}).get("api", {})

    from order_automation.ingest.api_ingest import app, set_api_key, set_pipeline
    set_pipeline(pipeline)
    api_key = api_cfg.get("api_key", "dev-api-key-change-me")
    set_api_key(api_key)

    import uvicorn
    uvicorn.run(
        app,
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 8000),
    )


@cli.command()
def ui() -> None:
    """Start the Streamlit UI."""
    import subprocess
    ui_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(ui_path)])
