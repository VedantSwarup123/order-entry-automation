# Order Entry Automation

A Python system that ingests purchase orders from multiple sources, normalises and validates them, routes them through configurable rules, and submits them to multiple output destinations.

## Architecture

```
  INGEST                    ENGINE                     OUTPUT
 ─────────            ─────────────────           ──────────────
 CSV/Excel  ─┐        ┌─ Normaliser ──┐          ┌─ SQLite DB
 Email      ─┤        │  (states,     │          ├─ Google Sheets
 Sheets     ─┼─ Raw ──┤   SKUs, UOMs) │── Order ─┼─ Slack
 REST API   ─┤ Order  │               │          ├─ Email
 Fax (OCR)  ─┤        ├─ Validator ───┤          ├─ ERP (mock)
 Streamlit  ─┘        │  (business    │          └─ Web Portal
                       │   rules)      │
                       ├─ Router ──────┤
                       │  (YAML rules) │
                       └─ Pipeline ────┘
```

## Quick Start

```bash
# Clone and set up
cd ~/order-entry-automation
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v

# Start the CLI
order-auto --help
```

## Configuration

All runtime configuration lives in `config/settings.yaml`:

- **Ingest sources** — enable/disable CSV, email, sheets, API, fax; set poll intervals and column mappings
- **Output adapters** — enable/disable database, sheets, Slack, email, ERP, web portal
- **Routing rules** — `config/routing_rules.yaml` declares which orders go where

### Environment Variables

Create a `.env` file (not committed):

```
COMPOSIO_API_KEY=your-key-here
DATABASE_URL=sqlite:///orders.db
```

### Composio Integration

External services (Gmail, Outlook, Google Sheets, Slack) are accessed via the [Composio](https://composio.dev) SDK. If Composio is not installed or not configured, the system falls back to mock responses automatically. All Composio calls go through `src/order_automation/integrations/composio_client.py` — no other module imports Composio directly.

## CLI Usage

```bash
order-auto run                     # Start all enabled ingest sources
order-auto run --source csv        # Run only CSV polling
order-auto ingest orders.csv       # Process a single file
order-auto status <order-id>       # Look up an order
order-auto failures                # List failed orders
order-auto retry <order-id>        # Re-process a failed order
order-auto stats                   # Order counts by status
order-auto test-connections        # Verify Composio connectivity
order-auto api                     # Start FastAPI server on :8000
order-auto ui                      # Start Streamlit UI
```

### API Endpoints

When running `order-auto api`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/orders` | Submit a single order |
| POST | `/api/v1/orders/batch` | Submit multiple orders |

All POST endpoints require an `X-API-Key` header (configured in `settings.yaml`).

## Project Structure

```
src/order_automation/
  models/          Pydantic v2 models (Order, Address, LineItem, enums)
  integrations/    Composio wrapper with mock fallback
  ingest/          Sources: CSV, email, sheets, API, fax
  engine/          Normaliser, validator, router, pipeline
  output/          Adapters: database, sheets, Slack, email, ERP, portal
  ui/              Streamlit manual-entry app
  main.py          Click CLI entry-point

config/
  settings.yaml        Master configuration
  routing_rules.yaml   Declarative routing rules
  composio_apps.yaml   Composio action reference

tests/
  test_models/         Order model tests
  test_engine/         Engine component tests
  test_ingest/         Ingest source tests
  test_output/         Output adapter tests
  test_integrations/   Composio client tests
  test_cli.py          CLI smoke tests
  test_integration.py  End-to-end tests
```

## Adding a New Adapter

### New Ingest Source

1. Create `src/order_automation/ingest/my_source.py`
2. Inherit from `IngestSource` (in `ingest/base.py`)
3. Implement `poll() -> list[RawOrder]` and `parse(RawOrder) -> list[Order]`
4. Wire it into `main.py`'s `run` command

### New Output Adapter

1. Create `src/order_automation/output/my_output.py`
2. Inherit from `OutputAdapter` (in `output/base.py`)
3. Implement `submit(Order) -> SubmissionResult`
4. Register it in `_build_pipeline()` in `main.py`
5. Add a routing rule in `config/routing_rules.yaml`

## Routing Rules

Rules in `config/routing_rules.yaml` support:

- **`"always"`** — matches every order
- **Field comparisons** — `==`, `!=`, `>`, `<`, `>=`, `<=`
- **List membership** — `"in"` operator
- **Dot notation** — access nested fields like `ship_to.state`

```yaml
rules:
  - name: "Large orders to ERP"
    condition: {field: "total_amount", operator: ">", value: 5000}
    destination: "erp"
  - name: "West coast to portal"
    condition: {field: "ship_to.state", operator: "in", value: ["CA","OR","WA"]}
    destination: "web_portal"
```

## Development

```bash
# Lint
ruff check src/

# Type check
mypy src/

# Test
pytest -v
```
