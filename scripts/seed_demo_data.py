#!/usr/bin/env python3
"""Seed the database with Ledvance-specific demo data.

Generates 80 orders with LED lighting products, real distributor names,
review queue items, and SAP field mappings.

Usage:
    python scripts/seed_demo_data.py
"""
from __future__ import annotations

import json
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
    ReviewQueueRecord,
)

DB_URL = "sqlite:///orders.db"

# Ledvance distributors / customers
CUSTOMERS = [
    ("CUST-LED01", "Sonepar USA"),
    ("CUST-LED02", "Rexel Holdings"),
    ("CUST-LED03", "WESCO International"),
    ("CUST-LED04", "Graybar Electric"),
    ("CUST-LED05", "CED Greentech"),
    ("CUST-LED06", "City Electric Supply"),
    ("CUST-LED07", "Crescent Electric"),
    ("CUST-LED08", "Border States Electric"),
    ("CUST-LED09", "Anixter International"),
    ("CUST-LED10", "HD Supply"),
    ("CUST-LED11", "Consolidated Electrical"),
    ("CUST-LED12", "Ferguson Enterprises"),
    ("CUST-LED13", "Werner Electric"),
    ("CUST-LED14", "Elliott Electric Supply"),
    ("CUST-LED15", "Platt Electric Supply"),
]

SOURCES = ["email", "csv", "api", "manual", "fax", "sheets"]
STATUSES = ["completed", "completed", "completed", "completed", "validated", "routed", "pending", "error", "review"]
STATES = ["CA", "NY", "TX", "FL", "IL", "WA", "OR", "NV", "AZ", "CO", "MA", "GA", "PA", "OH"]
CITIES = {
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "Irvine"],
    "NY": ["New York", "Buffalo", "Albany", "Rochester"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
    "IL": ["Chicago", "Springfield", "Naperville"],
    "WA": ["Seattle", "Tacoma", "Bellevue"],
    "OR": ["Portland", "Eugene", "Salem"],
    "NV": ["Las Vegas", "Reno"],
    "AZ": ["Phoenix", "Tucson", "Scottsdale"],
    "CO": ["Denver", "Boulder", "Colorado Springs"],
    "MA": ["Boston", "Cambridge", "Worcester"],
    "GA": ["Atlanta", "Savannah", "Augusta"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown"],
    "OH": ["Columbus", "Cleveland", "Cincinnati"],
}

# Ledvance LED product SKUs
SKUS = [
    ("LED-A19-60W", "LEDVANCE A19 LED Bulb 60W Equivalent", Decimal("3.99"), "EA"),
    ("LED-A19-100W", "LEDVANCE A19 LED Bulb 100W Equivalent", Decimal("5.49"), "EA"),
    ("LED-BR30-65W", "LEDVANCE BR30 LED Flood 65W Equivalent", Decimal("6.99"), "EA"),
    ("LED-BR40-75W", "LEDVANCE BR40 LED Flood 75W Equivalent", Decimal("8.99"), "EA"),
    ("LED-PAR38-90W", "LEDVANCE PAR38 LED Spot 90W Equivalent", Decimal("12.99"), "EA"),
    ("LED-PAR30-75W", "LEDVANCE PAR30 LED Spot 75W Equivalent", Decimal("10.49"), "EA"),
    ("LED-T8-4FT", "SYLVANIA LED T8 SubstiTUBE 4ft 15W", Decimal("8.99"), "EA"),
    ("LED-T8-2FT", "SYLVANIA LED T8 SubstiTUBE 2ft 8W", Decimal("6.49"), "EA"),
    ("LED-MR16-50W", "LEDVANCE MR16 LED 50W Equivalent GU10", Decimal("7.49"), "EA"),
    ("LED-STRIP-5M", "SYLVANIA Smart+ LED Strip 5m RGBW", Decimal("29.99"), "EA"),
    ("LED-CAN-60W", "LEDVANCE B11 LED Candelabra 60W Equiv", Decimal("4.99"), "EA"),
    ("FIX-TROFFER-2x4", "SYLVANIA 2x4 LED Troffer ValueLED", Decimal("79.99"), "EA"),
    ("FIX-TROFFER-2x2", "SYLVANIA 2x2 LED Troffer ValueLED", Decimal("59.99"), "EA"),
    ("FIX-PANEL-2x2", "SYLVANIA LED Flat Panel 2x2 40W", Decimal("64.99"), "EA"),
    ("FIX-PANEL-1x4", "SYLVANIA LED Flat Panel 1x4 50W", Decimal("74.99"), "EA"),
    ("FIX-HIGH-BAY", "SYLVANIA LED High Bay 200W 25000lm", Decimal("149.99"), "EA"),
    ("FIX-STRIP-4FT", "SYLVANIA LED Strip Light 4ft 25W", Decimal("34.99"), "EA"),
    ("FIX-WRAP-4FT", "SYLVANIA LED Wrap Light 4ft 40W", Decimal("44.99"), "EA"),
    ("FIX-VAPOR-4FT", "SYLVANIA LED Vapor Tight 4ft 40W IP65", Decimal("69.99"), "EA"),
    ("CTL-DIMMER-WiFi", "SYLVANIA Smart+ WiFi Dimmer Switch", Decimal("24.99"), "EA"),
    ("CTL-SENSOR-OCC", "SYLVANIA Occupancy Sensor Switch", Decimal("18.99"), "EA"),
    ("CTL-SENSOR-DL", "SYLVANIA Daylight Sensor", Decimal("22.99"), "EA"),
    ("EMG-EXIT-LED", "SYLVANIA LED Exit Sign Combo Emergency", Decimal("49.99"), "EA"),
    ("EMG-BATT-PACK", "SYLVANIA Emergency Battery Pack", Decimal("34.99"), "EA"),
    ("WIRE-14AWG-250", "14 AWG THHN Wire 250ft Spool", Decimal("42.99"), "CS"),
    ("CONN-WAGO-5P", "Wago 5-Port Lever Connector 50pk", Decimal("34.99"), "BX"),
]

# Extraction methods and confidence for variety
EXTRACTION_METHODS = ["llm", "llm", "llm", "regex", "regex_fallback"]

# Sample email texts for review queue items
SAMPLE_EMAILS = [
    """From: orders@sonepar.com
Subject: PO #SP-2026-4521 - LED Lighting Order

Hi Ledvance Team,

Please process the following order:

Customer: Sonepar USA (CUST-LED01)
PO Number: SP-2026-4521

Items:
LED-A19-60W    500  $3.99
LED-BR30-65W   200  $6.99
FIX-TROFFER-2x4  50  $79.99

Ship to:
Sonepar Distribution Center
4521 Industrial Pkwy
Houston, TX 77001

Rush delivery requested.
Thanks""",

    """Subject: New Order - Rexel PO REX-0892

Ordering:
- 1000x LED T8 4FT tubes (LED-T8-4FT) @ $8.99 each
- 300x LED Panel 2x2 (FIX-PANEL-2x2) @ $64.99 each

Customer ID: CUST-LED02
Ship to: Rexel warehouse, 892 Commerce Dr, Atlanta GA 30301

Need by end of week please.""",

    """PURCHASE ORDER

FROM: Graybar Electric Company
DATE: 2026-02-08
PO#: GB-44891

QTY  ITEM         PRICE
200  LED-PAR38-90W   12.99
150  CTL-DIMMER-WiFi 24.99
 75  EMG-EXIT-LED    49.99

SHIP TO:
Graybar Electric - Denver Branch
1200 W Colfax Ave
Denver CO 80204

SPECIAL INSTRUCTIONS: Dock appointment required""",
]


def create_seed_data():
    engine = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear existing data for clean re-seed
    session.query(ReviewQueueRecord).delete()
    session.query(AuditLogRecord).delete()
    session.query(LineItemRecord).delete()
    session.query(OrderRecord).delete()
    session.commit()

    now = datetime.now(UTC)
    orders_created = 0
    review_items_created = 0

    # SAP order type mapping
    sap_types = ["ZL01", "ZL01", "ZL01", "ZL02", "ZL02"]

    for i in range(80):
        order_id = str(uuid.uuid4())
        cust_id, cust_name = random.choice(CUSTOMERS)
        source = random.choice(SOURCES)
        status = random.choice(STATUSES)
        state = random.choice(STATES)
        city = random.choice(CITIES[state])

        # Spread orders over last 60 days
        days_ago = random.randint(0, 60)
        hours_ago = random.randint(0, 23)
        created_at = now - timedelta(days=days_ago, hours=hours_ago)
        order_date = created_at.strftime("%Y-%m-%d")

        # Generate 1-8 line items
        num_items = random.randint(1, 8)
        selected_items = random.sample(SKUS, min(num_items, len(SKUS)))

        total_amount = Decimal(0)
        total_quantity = 0
        line_items = []

        for sku, desc, price, uom in selected_items:
            qty = random.randint(5, 200)
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

        po_number = f"PO-{cust_name.split()[0].upper()[:4]}-{created_at.strftime('%Y')}-{random.randint(1000, 9999)}"
        errors = "Validation failed: missing ship_to address" if status == "error" else ""

        # Extraction confidence for email/fax orders
        extraction_method = random.choice(EXTRACTION_METHODS) if source in ("email", "fax") else ""
        confidence = None
        if extraction_method:
            if extraction_method == "llm":
                confidence = round(random.uniform(0.7, 0.98), 2)
            elif extraction_method == "regex":
                confidence = round(random.uniform(0.4, 0.75), 2)
            else:
                confidence = round(random.uniform(0.3, 0.6), 2)

        # SAP mapping
        sap_type = random.choice(sap_types)
        ship_to_suffix = random.choice(["Warehouse", "DC", "Distribution Center", "Branch", "Store"])
        sap_data = json.dumps({
            "order_type": sap_type,
            "order_type_desc": "Stock Order" if sap_type == "ZL01" else "Drop Ship Order",
            "sales_org": "1000",
            "plant": {"CA": "1000", "NY": "2000", "TX": "3000", "FL": "4000"}.get(state, "1000"),
            "delivery_priority": "02",
            "incoterms": "EXW" if sap_type == "ZL01" else "FOB",
        })

        # Handle review status → pending for the actual order, queue item for review
        actual_status = "pending" if status == "review" else status

        order = OrderRecord(
            id=order_id,
            source=source,
            source_ref=f"{source}-ref-{random.randint(100, 999)}",
            customer_id=cust_id,
            customer_name=cust_name,
            po_number=po_number,
            order_date=order_date,
            ship_to_name=f"{cust_name} - {ship_to_suffix}",
            ship_to_line1=f"{random.randint(100, 9999)} {random.choice(['Industrial', 'Commerce', 'Distribution', 'Enterprise', 'Logistics'])} {random.choice(['Pkwy', 'Dr', 'Blvd', 'Way', 'Ave'])}",
            ship_to_city=city,
            ship_to_state=state,
            ship_to_postal_code=str(random.randint(10000, 99999)),
            ship_to_country="US",
            total_amount=float(total_amount),
            total_quantity=total_quantity,
            status=actual_status,
            errors=errors,
            confidence=float(confidence) if confidence else None,
            extraction_method=extraction_method,
            sap_order_type=sap_type,
            sap_data=sap_data,
            notes="" if random.random() > 0.3 else random.choice([
                "Rush delivery requested",
                "Dock appointment required",
                "Standard delivery",
                "Contact warehouse before delivery",
                "Fragile items — handle with care",
                "Must deliver before end of month",
                "Forklift required at delivery",
                "Call ahead 1 hour before delivery",
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
        if actual_status in ("validated", "routed", "completed"):
            session.add(AuditLogRecord(
                order_id=order_id,
                action="validated",
                detail="All checks passed",
                timestamp=created_at + timedelta(seconds=random.randint(1, 30)),
            ))
        if actual_status in ("routed", "completed"):
            session.add(AuditLogRecord(
                order_id=order_id,
                action="routed",
                detail=f"Destinations: database, erp (SAP {sap_type})",
                timestamp=created_at + timedelta(seconds=random.randint(30, 60)),
            ))
        if actual_status == "completed":
            session.add(AuditLogRecord(
                order_id=order_id,
                action="completed",
                detail="All destinations confirmed",
                timestamp=created_at + timedelta(seconds=random.randint(60, 120)),
            ))

        # Create review queue items for orders needing review
        if status == "review" or (source in ("email", "fax") and confidence and confidence < 0.7):
            review_confidence = confidence or round(random.uniform(0.3, 0.65), 2)
            review_method = extraction_method or "regex_fallback"
            anomalies = []
            if review_confidence < 0.5:
                anomalies.extend(["Missing customer_id", "Low extraction confidence"])
            if random.random() > 0.5:
                anomalies.append("Unusually large quantity detected")
            if random.random() > 0.7:
                anomalies.append("Missing ship-to address")

            sample_text = random.choice(SAMPLE_EMAILS) if source == "email" else f"[Fax OCR text for PO {po_number}]"

            review_status = random.choice(["pending", "pending", "pending", "approved", "rejected"])

            session.add(ReviewQueueRecord(
                order_id=order_id,
                source=source,
                customer_name=cust_name,
                po_number=po_number,
                confidence=float(review_confidence),
                extraction_method=review_method,
                anomalies=json.dumps(anomalies),
                original_text=sample_text,
                extracted_data=json.dumps({
                    "customer_id": cust_id,
                    "customer_name": cust_name,
                    "po_number": po_number,
                    "line_items": [
                        {"sku": li.sku, "quantity": li.quantity, "unit_price": float(li.unit_price)}
                        for li in line_items[:3]
                    ],
                }),
                status=review_status,
                reviewer_notes="Verified against original PO document" if review_status == "approved" else "",
                reviewed_at=created_at + timedelta(minutes=random.randint(5, 120)) if review_status != "pending" else None,
                created_at=created_at,
            ))
            review_items_created += 1

        orders_created += 1

    # Add a few more explicit pending review items for demo
    for idx, email_text in enumerate(SAMPLE_EMAILS):
        order_id = str(uuid.uuid4())
        cust_id, cust_name = CUSTOMERS[idx]
        source = "email"
        created_at = now - timedelta(hours=random.randint(1, 24))

        # Create order
        session.add(OrderRecord(
            id=order_id,
            source=source,
            source_ref=f"email-demo-{idx}",
            customer_id=cust_id,
            customer_name=cust_name,
            po_number=f"DEMO-PO-{idx + 1}",
            order_date=created_at.strftime("%Y-%m-%d"),
            ship_to_name=f"{cust_name} - Warehouse",
            ship_to_line1="123 Demo St",
            ship_to_city="Houston",
            ship_to_state="TX",
            ship_to_postal_code="77001",
            ship_to_country="US",
            total_amount=random.uniform(500, 15000),
            total_quantity=random.randint(50, 500),
            status="pending",
            confidence=round(random.uniform(0.35, 0.6), 2),
            extraction_method="llm",
            sap_order_type="ZL01",
            sap_data=json.dumps({"order_type": "ZL01", "order_type_desc": "Stock Order", "sales_org": "1000", "plant": "3000"}),
            created_at=created_at,
        ))

        # Create review queue entry
        session.add(ReviewQueueRecord(
            order_id=order_id,
            source=source,
            customer_name=cust_name,
            po_number=f"DEMO-PO-{idx + 1}",
            confidence=round(random.uniform(0.35, 0.6), 2),
            extraction_method="llm",
            anomalies=json.dumps(["Low extraction confidence", "Missing fields detected"]),
            original_text=email_text,
            extracted_data=json.dumps({
                "customer_id": cust_id,
                "customer_name": cust_name,
                "po_number": f"DEMO-PO-{idx + 1}",
                "line_items": [
                    {"sku": "LED-A19-60W", "quantity": 500, "unit_price": 3.99},
                    {"sku": "LED-BR30-65W", "quantity": 200, "unit_price": 6.99},
                ],
            }),
            status="pending",
            created_at=created_at,
        ))
        review_items_created += 1
        orders_created += 1

    session.commit()
    session.close()
    print(f"Seeded {orders_created} demo orders + {review_items_created} review queue items into {DB_URL}")


if __name__ == "__main__":
    create_seed_data()
