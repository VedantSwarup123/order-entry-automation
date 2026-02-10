#!/usr/bin/env python3
"""Seed the database with 50+ demo orders across different sources, customers, and statuses.

Usage:
    python scripts/seed_demo_data.py
"""
from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from order_automation.output.database import (
    AuditLogRecord,
    Base,
    LineItemRecord,
    OrderRecord,
)

DB_URL = "sqlite:///orders.db"

CUSTOMERS = [
    ("CUST-001", "Ledvance LLC"),
    ("CUST-002", "Acme Corporation"),
    ("CUST-003", "TechCorp Industries"),
    ("CUST-004", "Global Retail Inc"),
    ("CUST-005", "West Coast Supply Co"),
    ("CUST-006", "Bright Lighting Group"),
    ("CUST-007", "Summit Manufacturing"),
    ("CUST-008", "Pacific Trade Partners"),
    ("CUST-009", "Metro Distribution"),
    ("CUST-010", "Apex Industrial Solutions"),
    ("CUST-011", "Greenfield Enterprises"),
    ("CUST-012", "Quantum Dynamics Corp"),
]

SOURCES = ["email", "csv", "api", "manual", "fax", "sheets"]
STATUSES = ["completed", "completed", "completed", "validated", "routed", "pending", "error"]
STATES = ["CA", "NY", "TX", "FL", "IL", "WA", "OR", "NV", "AZ", "CO", "MA", "GA", "PA", "OH"]
CITIES = {
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento"],
    "NY": ["New York", "Buffalo", "Albany"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
    "IL": ["Chicago", "Springfield"],
    "WA": ["Seattle", "Tacoma", "Bellevue"],
    "OR": ["Portland", "Eugene", "Salem"],
    "NV": ["Las Vegas", "Reno"],
    "AZ": ["Phoenix", "Tucson", "Scottsdale"],
    "CO": ["Denver", "Boulder", "Colorado Springs"],
    "MA": ["Boston", "Cambridge"],
    "GA": ["Atlanta", "Savannah"],
    "PA": ["Philadelphia", "Pittsburgh"],
    "OH": ["Columbus", "Cleveland", "Cincinnati"],
}

SKUS = [
    ("LED-A19-60W", "LED A19 Bulb 60W Equiv", Decimal("4.99"), "EA"),
    ("LED-BR30-65W", "LED BR30 Flood 65W Equiv", Decimal("7.49"), "EA"),
    ("LED-T8-4FT", "LED T8 Tube 4ft 18W", Decimal("12.99"), "EA"),
    ("LED-PAR38-90W", "LED PAR38 Spot 90W Equiv", Decimal("14.99"), "EA"),
    ("LED-STRIP-5M", "LED Strip Light 5m RGB", Decimal("24.99"), "EA"),
    ("FIX-TROFFER-2x4", "2x4 LED Troffer Fixture", Decimal("89.99"), "EA"),
    ("FIX-PANEL-2x2", "2x2 LED Panel Light", Decimal("64.99"), "EA"),
    ("FIX-HIGH-BAY", "LED High Bay Light 200W", Decimal("149.99"), "EA"),
    ("CTL-DIMMER-WiFi", "WiFi Smart Dimmer Switch", Decimal("29.99"), "EA"),
    ("CTL-SENSOR-OCC", "Occupancy Sensor Switch", Decimal("19.99"), "EA"),
    ("WIRE-14AWG-250", "14 AWG Wire 250ft Roll", Decimal("42.99"), "CS"),
    ("WIRE-12AWG-250", "12 AWG Wire 250ft Roll", Decimal("54.99"), "CS"),
    ("CONN-WAGO-5P", "Wago 5-Port Connector 50pk", Decimal("34.99"), "BX"),
    ("EMG-EXIT-LED", "LED Exit Sign Emergency", Decimal("39.99"), "EA"),
    ("BATT-AA-48PK", "AA Batteries 48-Pack", Decimal("18.99"), "PK"),
]


def create_seed_data():
    engine = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if already seeded
    existing = session.query(OrderRecord).count()
    if existing > 10:
        print(f"Database already has {existing} orders. Skipping seed.")
        session.close()
        return

    now = datetime.now(UTC)
    orders_created = 0

    for i in range(60):
        order_id = str(uuid.uuid4())
        cust_id, cust_name = random.choice(CUSTOMERS)
        source = random.choice(SOURCES)
        status = random.choice(STATUSES)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])

        # Spread orders over last 45 days
        days_ago = random.randint(0, 45)
        hours_ago = random.randint(0, 23)
        created_at = now - timedelta(days=days_ago, hours=hours_ago)
        order_date = created_at.strftime("%Y-%m-%d")

        # Generate 1-6 line items
        num_items = random.randint(1, 6)
        selected_items = random.sample(SKUS, min(num_items, len(SKUS)))

        total_amount = Decimal(0)
        total_quantity = 0
        line_items = []

        for sku, desc, price, uom in selected_items:
            qty = random.randint(1, 50)
            line_total = Decimal(qty) * price
            total_amount += line_total
            total_quantity += qty
            line_items.append(LineItemRecord(
                order_id=order_id,
                sku=sku,
                description=desc,
                quantity=qty,
                unit_price=float(price),
                uom=uom,
                line_total=float(line_total),
            ))

        po_number = f"PO-{created_at.strftime('%Y')}-{random.randint(1000, 9999)}"
        errors = "Validation failed: missing ship_to address" if status == "error" else ""

        order = OrderRecord(
            id=order_id,
            source=source,
            source_ref=f"{source}-ref-{random.randint(100, 999)}",
            customer_id=cust_id,
            customer_name=cust_name,
            po_number=po_number,
            order_date=order_date,
            ship_to_name=f"{cust_name} - Warehouse",
            ship_to_line1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Cedar', 'Industrial'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr', 'Way'])}",
            ship_to_city=city,
            ship_to_state=state,
            ship_to_postal_code=str(random.randint(10000, 99999)),
            ship_to_country="US",
            total_amount=float(total_amount),
            total_quantity=total_quantity,
            status=status,
            errors=errors,
            notes="" if random.random() > 0.3 else random.choice([
                "Rush delivery requested",
                "Dock appointment required",
                "Standard delivery",
                "Contact warehouse before delivery",
                "Fragile items — handle with care",
            ]),
            created_at=created_at,
        )

        session.add(order)
        for li in line_items:
            session.add(li)

        # Audit log
        session.add(AuditLogRecord(
            order_id=order_id,
            action="submitted",
            detail=f"Source: {source}, PO: {po_number}",
            timestamp=created_at,
        ))
        if status in ("validated", "routed", "completed"):
            session.add(AuditLogRecord(
                order_id=order_id,
                action="validated",
                detail="All checks passed",
                timestamp=created_at + timedelta(seconds=random.randint(1, 30)),
            ))
        if status in ("routed", "completed"):
            session.add(AuditLogRecord(
                order_id=order_id,
                action="routed",
                detail="Destinations: database",
                timestamp=created_at + timedelta(seconds=random.randint(30, 60)),
            ))
        if status == "completed":
            session.add(AuditLogRecord(
                order_id=order_id,
                action="completed",
                detail="All destinations confirmed",
                timestamp=created_at + timedelta(seconds=random.randint(60, 120)),
            ))

        orders_created += 1

    session.commit()
    session.close()
    print(f"Seeded {orders_created} demo orders into {DB_URL}")


if __name__ == "__main__":
    create_seed_data()
