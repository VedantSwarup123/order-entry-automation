"""End-to-end integration tests.

These tests exercise the full pipeline from ingest to database persistence.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from order_automation.engine.normalizer import OrderNormalizer
from order_automation.engine.pipeline import OrderPipeline
from order_automation.engine.router import OrderRouter
from order_automation.engine.validator import OrderValidator
from order_automation.ingest.csv_ingest import CSVIngest
from order_automation.models.order import (
    Address,
    Order,
    OrderLineItem,
    OrderSource,
    OrderStatus,
)
from order_automation.output.database import DatabaseAdapter


def _pipeline_with_db(db: DatabaseAdapter) -> OrderPipeline:
    """Build a pipeline wired to a real in-memory database."""
    router = OrderRouter()
    router.rules = [{"name": "all_db", "condition": "always", "destination": "database"}]
    p = OrderPipeline(
        normalizer=OrderNormalizer(),
        validator=OrderValidator(),
        router=router,
    )
    p.register_adapter("database", db)
    return p


# ------------------------------------------------------------------
# CSV → Pipeline → DB
# ------------------------------------------------------------------

class TestCSVEndToEnd:
    """Create a CSV file, ingest it, run the pipeline, verify in DB."""

    def test_csv_to_database(self, tmp_path: Path):
        # 1. Write a CSV
        watch = tmp_path / "inbox"
        watch.mkdir()
        csv_path = watch / "orders.csv"
        csv_path.write_text(
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            "PO-500,CUST-10,acme corp,widget-a,Widget A,5,25.00,each,"
            "Warehouse,100 Main St,Los Angeles,california,90001\n"
            "PO-500,CUST-10,acme corp,widget-b,Widget B,3,15.00,CS,"
            "Warehouse,100 Main St,Los Angeles,california,90001\n"
        )

        # 2. Ingest
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        assert len(raws) == 1

        orders = ing.parse(raws[0])
        assert len(orders) == 1
        order = orders[0]
        assert order.po_number == "PO-500"
        assert len(order.line_items) == 2

        # 3. Pipeline
        db = DatabaseAdapter(url="sqlite:///:memory:")
        pipeline = _pipeline_with_db(db)
        result = pipeline.process(order)

        # 4. Verify
        assert result.status == OrderStatus.completed
        assert result.customer_name == "Acme Corp"  # normalised
        assert result.ship_to.state == "CA"  # normalised
        assert result.ship_to.country == "US"
        assert result.line_items[0].sku == "WIDGET-A"  # normalised
        assert result.line_items[0].uom == "EA"  # normalised
        assert result.line_items[1].uom == "CS"

        # DB check
        rec = db.get_order(result.id)
        assert rec is not None
        assert rec.po_number == "PO-500"
        assert rec.status == "completed"

        items = db.get_line_items(result.id)
        assert len(items) == 2


# ------------------------------------------------------------------
# API schema → Pipeline → DB
# ------------------------------------------------------------------

class TestAPIEndToEnd:
    """Submit an order via the API schema, run the pipeline, verify in DB."""

    def test_api_order_to_database(self):
        db = DatabaseAdapter(url="sqlite:///:memory:")
        pipeline = _pipeline_with_db(db)

        order = Order(
            source=OrderSource.api,
            customer_id="API-CUST-1",
            customer_name="beta inc",
            po_number="PO-API-1",
            ship_to=Address(
                name="HQ", line1="200 Oak Ave", city="Portland",
                state="oregon", postal_code="97201",
            ),
            line_items=[
                OrderLineItem(sku="api-item-1", quantity=10, unit_price=Decimal("50")),
            ],
        )

        result = pipeline.process(order)
        assert result.status == OrderStatus.completed
        assert result.customer_name == "Beta Inc"
        assert result.ship_to.state == "OR"
        assert result.line_items[0].sku == "API-ITEM-1"

        rec = db.get_order(result.id)
        assert rec is not None
        assert Decimal(str(rec.total_amount)) == Decimal("500")


# ------------------------------------------------------------------
# Mock Composio
# ------------------------------------------------------------------

class TestComposioMock:
    """Verify the pipeline works when Composio calls are mocked."""

    def test_with_mock_composio(self):
        mock_emails = {
            "emails": [
                {
                    "id": "msg-123",
                    "body": (
                        "customer_id: COMP-1\n"
                        "customer_name: Gamma LLC\n"
                        "po_number: PO-COMP-1\n"
                        "\n"
                        "SKU-GAMMA 5 $100.00\n"
                    ),
                }
            ]
        }

        with patch("order_automation.integrations.composio_client.execute_action", return_value=mock_emails):
            from order_automation.ingest.email_ingest import EmailIngest
            ing = EmailIngest(provider="gmail")
            raws = ing.poll()
            assert len(raws) == 1

            orders = ing.parse(raws[0])
            assert len(orders) == 1
            order = orders[0]
            assert order.po_number == "PO-COMP-1"
            assert order.line_items[0].sku == "SKU-GAMMA"
            assert order.line_items[0].quantity == 5

            # Run through pipeline
            db = DatabaseAdapter(url="sqlite:///:memory:")
            pipeline = _pipeline_with_db(db)
            result = pipeline.process(order)
            assert result.status == OrderStatus.completed

            rec = db.get_order(result.id)
            assert rec is not None
