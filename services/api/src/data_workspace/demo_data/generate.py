"""Reproducible generic enterprise seed data; monetary values are integer cents."""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import random

SOURCE = "independently_generated_synthetic"
TABLES = ("dim_customer", "dim_product", "fact_order", "fact_order_item", "fact_event")


def generate(seed=20261026, customers=1000, products=100, orders=3000, days=90):
    if min(customers, products, orders, days) < 1:
        raise ValueError("sizes must be positive")
    rng = random.Random(seed)
    start = date(2025, 1, 1)
    snapshot = (start + timedelta(days=days - 1)).isoformat()
    data = {t: [] for t in TABLES}
    for i in range(customers):
        data["dim_customer"].append({"customer_id": f"syn_c{i:06d}", "region_group": f"region_{rng.randrange(1, 5)}", "segment": rng.choice(["standard", "premium"]), "registered_date": (start - timedelta(days=rng.randrange(1, 366))).isoformat(), "snapshot_date": snapshot})
    for i in range(products):
        data["dim_product"].append({"product_id": f"syn_p{i:05d}", "category": f"category_{rng.randrange(1, 6)}", "unit_price_cents": rng.randrange(500, 50001), "currency": "TEST", "snapshot_date": snapshot})
    for i in range(orders):
        customer = rng.choice(data["dim_customer"])
        oid = f"syn_o{i:07d}"
        when = datetime(2025, 1, 1, 12) + timedelta(days=rng.randrange(days), seconds=rng.randrange(30000))
        channel = rng.choice(["direct", "search", "campaign", "referral"])
        status = rng.choices(["paid", "completed", "cancelled"], weights=[35, 55, 10])[0]
        total = 0
        for j, product in enumerate(rng.sample(data["dim_product"], min(rng.randrange(1, 4), products))):
            quantity = rng.randrange(1, 4)
            amount = product["unit_price_cents"] * quantity
            total += amount
            data["fact_order_item"].append({"order_item_id": f"{oid}_i{j}", "order_id": oid, "product_id": product["product_id"], "quantity": quantity, "unit_price_cents": product["unit_price_cents"], "line_amount_cents": amount, "partition_date": when.date().isoformat()})
        discount = total * rng.choice([0, 0, 0, 5, 10]) // 100
        paid = status != "cancelled"
        payment = when + timedelta(minutes=5) if paid else None
        data["fact_order"].append({"order_id": oid, "customer_id": customer["customer_id"], "ordered_at": when.isoformat(), "paid_at": payment.isoformat() if payment else None, "status": status, "channel": channel, "gross_amount_cents": total, "discount_cents": discount, "paid_amount_cents": total - discount if paid else 0, "currency": "TEST", "partition_date": when.date().isoformat()})
        events = [("view", when - timedelta(minutes=10)), ("add_to_cart", when - timedelta(minutes=3)), ("place_order", when)]
        if paid:
            events.append(("pay_order", payment))
        for event_type, at in events:
            data["fact_event"].append({"event_id": f"syn_e{len(data['fact_event']):08d}", "customer_id": customer["customer_id"], "session_id": f"syn_s{i:07d}", "order_id": oid, "event_type": event_type, "event_at": at.isoformat(), "channel": channel, "partition_date": at.date().isoformat()})
    return data


def validate(data):
    if set(data) != set(TABLES):
        raise ValueError("unexpected table set")
    primary_keys = dict(zip(TABLES, ("customer_id", "product_id", "order_id", "order_item_id", "event_id")))
    for table, key in primary_keys.items():
        ids = [r[key] for r in data[table]]
        if len(set(ids)) != len(ids) or not all(x.startswith("syn_") for x in ids):
            raise ValueError("invalid synthetic primary keys")
    customers = {r["customer_id"] for r in data["dim_customer"]}
    products = {r["product_id"] for r in data["dim_product"]}
    orders = {r["order_id"]: r for r in data["fact_order"]}
    totals = Counter()
    for row in data["fact_order_item"]:
        if row["order_id"] not in orders or row["product_id"] not in products:
            raise ValueError("orphan order item")
        if row["quantity"] <= 0 or row["unit_price_cents"] < 0 or row["line_amount_cents"] != row["quantity"] * row["unit_price_cents"]:
            raise ValueError("invalid line amount")
        if row["partition_date"] != orders[row["order_id"]]["partition_date"]:
            raise ValueError("invalid item partition")
        totals[row["order_id"]] += row["line_amount_cents"]
    for row in orders.values():
        if row["customer_id"] not in customers or totals[row["order_id"]] != row["gross_amount_cents"]:
            raise ValueError("invalid order relation/total")
        if not 0 <= row["discount_cents"] <= row["gross_amount_cents"]:
            raise ValueError("invalid discount")
        paid = row["status"] in {"paid", "completed"}
        expected = row["gross_amount_cents"] - row["discount_cents"] if paid else 0
        if row["paid_amount_cents"] != expected or bool(row["paid_at"]) != paid or row["status"] not in {"paid", "completed", "cancelled"}:
            raise ValueError("invalid payment")
        ordered = datetime.fromisoformat(row["ordered_at"])
        if row["partition_date"] != ordered.date().isoformat() or (paid and datetime.fromisoformat(row["paid_at"]) < ordered):
            raise ValueError("invalid order time")
    counts = Counter()
    for row in data["fact_event"]:
        order = orders.get(row["order_id"])
        if not order or row["customer_id"] != order["customer_id"] or row["channel"] != order["channel"]:
            raise ValueError("invalid event relation")
        if row["event_type"] not in {"view", "add_to_cart", "place_order", "pay_order"}:
            raise ValueError("invalid event type")
        if row["partition_date"] != datetime.fromisoformat(row["event_at"]).date().isoformat():
            raise ValueError("invalid event partition")
        counts[(row["order_id"], row["event_type"])] += 1
    for oid, row in orders.items():
        for kind in ("view", "add_to_cart", "place_order"):
            if counts[(oid, kind)] != 1:
                raise ValueError("invalid event count")
        if counts[(oid, "pay_order")] != int(row["status"] != "cancelled"):
            raise ValueError("invalid payment event count")
    return {"status": "passed", "checks": ["synthetic_primary_keys", "referential_integrity", "integer_money_conservation", "payment_consistency", "date_partitions", "event_consistency"], "scope": "generator invariants only; not privacy certification or real business validation"}


def write_dataset(destination, **params):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("refusing to overwrite an existing dataset")
    data = generate(**params)
    quality = validate(data)
    destination.mkdir(parents=True)
    files = {}
    for table in TABLES:
        content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in data[table])
        encoded = content.encode("utf-8")
        (destination / f"{table}.jsonl").write_bytes(encoded)
        files[table] = {"path": f"{table}.jsonl", "row_count": len(data[table]), "sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded), "fields": list(data[table][0])}
    golden = {"order_count": len(data["fact_order"]), "paid_order_count": sum(r["status"] != "cancelled" for r in data["fact_order"]), "paid_amount_cents": sum(r["paid_amount_cents"] for r in data["fact_order"]), "currency": "TEST", "note": "synthetic expected SQL results, not real business figures"}
    manifest = {"schema_version": "1.0", "source": SOURCE, "external_sources": [], "synthetic": True, "parameters": params, "timezone": "UTC", "currency": "TEST", "tables": files, "quality": quality, "golden_checks": golden, "limitations": ["Designed synthetic distributions are not estimates of any enterprise", "Events are order-session scenarios, not an unbiased population conversion funnel", "90 days are simulated test dates, not a company partition sample", "Modeling and experimental modules require additional purpose-built data and checks"]}
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    result = write_dataset(args.output, seed=args.seed, customers=1000, products=100, orders=3000, days=90)
    print(json.dumps({"source": result["source"], "rows": {t: f["row_count"] for t, f in result["tables"].items()}, "bytes": sum(f["bytes"] for f in result["tables"].values()), "quality": result["quality"]["status"]}))
