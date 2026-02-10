"""Tests for CSVIngest using actual temp CSV files."""
from __future__ import annotations

import tempfile
from pathlib import Path

from order_automation.ingest.csv_ingest import CSVIngest


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content)


class TestCSVIngest:
    def test_poll_finds_csv(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        _write_csv(watch / "orders.csv", (
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            "PO-100,C1,Acme,ABC,Widget,10,9.99,EA,Warehouse,1 Main St,Springfield,IL,62701\n"
        ))
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        assert len(raws) == 1
        assert raws[0].rows

    def test_parse_single_order(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        _write_csv(watch / "orders.csv", (
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            "PO-100,C1,Acme,ABC,Widget,10,9.99,EA,Warehouse,1 Main St,Springfield,IL,62701\n"
            "PO-100,C1,Acme,DEF,Gadget,5,19.99,EA,Warehouse,1 Main St,Springfield,IL,62701\n"
        ))
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        orders = ing.parse(raws[0])
        assert len(orders) == 1
        assert orders[0].po_number == "PO-100"
        assert len(orders[0].line_items) == 2

    def test_parse_multiple_pos(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        _write_csv(watch / "orders.csv", (
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            "PO-100,C1,Acme,ABC,Widget,10,9.99,EA,W,1 St,C,IL,60601\n"
            "PO-200,C2,Beta,XYZ,Thing,2,5.00,EA,W2,2 St,D,NY,10001\n"
        ))
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        orders = ing.parse(raws[0])
        assert len(orders) == 2
        pos = {o.po_number for o in orders}
        assert pos == {"PO-100", "PO-200"}

    def test_empty_rows_skipped(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        _write_csv(watch / "orders.csv", (
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            ",,,,,,,,,,,,\n"
            "PO-100,C1,Acme,ABC,Widget,10,9.99,EA,W,1 St,C,IL,60601\n"
        ))
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        orders = ing.parse(raws[0])
        assert len(orders) == 1

    def test_move_to_processed(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        proc = tmp_path / "proc"
        watch.mkdir()
        f = watch / "test.csv"
        _write_csv(f, "PO Number,SKU,Quantity,Unit Price\nPO-1,X,1,10\n")
        ing = CSVIngest(watch_dir=watch, processed_dir=proc)
        ing.move_to_processed(f)
        assert not f.exists()
        assert (proc / "test.csv").exists()

    def test_no_files_returns_empty(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        assert ing.poll() == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path):
        ing = CSVIngest(watch_dir=tmp_path / "nope", processed_dir=tmp_path / "proc")
        assert ing.poll() == []

    def test_missing_quantity_defaults_to_1(self, tmp_path: Path):
        watch = tmp_path / "inbox"
        watch.mkdir()
        _write_csv(watch / "orders.csv", (
            "PO Number,Customer ID,Customer Name,SKU,Description,Quantity,Unit Price,UOM,"
            "Ship To Name,Ship To Address,Ship To City,Ship To State,Ship To Zip\n"
            "PO-100,C1,Acme,ABC,Widget,,9.99,EA,W,1 St,C,IL,60601\n"
        ))
        ing = CSVIngest(watch_dir=watch, processed_dir=tmp_path / "proc")
        raws = ing.poll()
        orders = ing.parse(raws[0])
        assert orders[0].line_items[0].quantity == 1
