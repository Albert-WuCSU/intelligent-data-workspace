"""Independently designed typed star-schema, not copied enterprise metadata."""
COLUMNS = {
    "dim_customer": [("customer_id", "VARCHAR"), ("region_group", "VARCHAR"), ("segment", "VARCHAR"), ("registered_date", "DATE"), ("snapshot_date", "DATE")],
    "dim_product": [("product_id", "VARCHAR"), ("category", "VARCHAR"), ("unit_price_cents", "BIGINT"), ("currency", "VARCHAR"), ("snapshot_date", "DATE")],
    "fact_order": [("order_id", "VARCHAR"), ("customer_id", "VARCHAR"), ("ordered_at", "TIMESTAMP"), ("paid_at", "TIMESTAMP"), ("status", "VARCHAR"), ("channel", "VARCHAR"), ("gross_amount_cents", "BIGINT"), ("discount_cents", "BIGINT"), ("paid_amount_cents", "BIGINT"), ("currency", "VARCHAR"), ("partition_date", "DATE")],
    "fact_order_item": [("order_item_id", "VARCHAR"), ("order_id", "VARCHAR"), ("product_id", "VARCHAR"), ("quantity", "INTEGER"), ("unit_price_cents", "BIGINT"), ("line_amount_cents", "BIGINT"), ("partition_date", "DATE")],
    "fact_event": [("event_id", "VARCHAR"), ("customer_id", "VARCHAR"), ("session_id", "VARCHAR"), ("order_id", "VARCHAR"), ("event_type", "VARCHAR"), ("event_at", "TIMESTAMP"), ("channel", "VARCHAR"), ("partition_date", "DATE")],
}
CONSTRAINTS = {
    "dim_customer": ["PRIMARY KEY(customer_id)"],
    "dim_product": ["PRIMARY KEY(product_id)", "CHECK(unit_price_cents >= 0)", "CHECK(currency = 'TEST')"],
    "fact_order": ["PRIMARY KEY(order_id)", "FOREIGN KEY(customer_id) REFERENCES analytics.dim_customer(customer_id)", "CHECK(status IN ('paid','completed','cancelled'))", "CHECK(gross_amount_cents >= discount_cents AND discount_cents >= 0)", "CHECK(currency = 'TEST')", "CHECK((status = 'cancelled' AND paid_amount_cents = 0 AND paid_at IS NULL) OR (status != 'cancelled' AND paid_amount_cents = gross_amount_cents - discount_cents AND paid_at >= ordered_at))", "CHECK(partition_date = CAST(ordered_at AS DATE))"],
    "fact_order_item": ["PRIMARY KEY(order_item_id)", "FOREIGN KEY(order_id) REFERENCES analytics.fact_order(order_id)", "FOREIGN KEY(product_id) REFERENCES analytics.dim_product(product_id)", "CHECK(quantity > 0 AND unit_price_cents >= 0)", "CHECK(line_amount_cents = quantity * unit_price_cents)"],
    "fact_event": ["PRIMARY KEY(event_id)", "FOREIGN KEY(customer_id) REFERENCES analytics.dim_customer(customer_id)", "FOREIGN KEY(order_id) REFERENCES analytics.fact_order(order_id)", "CHECK(event_type IN ('view','add_to_cart','place_order','pay_order'))", "CHECK(partition_date = CAST(event_at AS DATE))"],
}
RELATIONS = {
    "dim_customer": [], "dim_product": [],
    "fact_order": [{"field": "customer_id", "references": "analytics.dim_customer.customer_id"}],
    "fact_order_item": [{"field": "order_id", "references": "analytics.fact_order.order_id"}, {"field": "product_id", "references": "analytics.dim_product.product_id"}],
    "fact_event": [{"field": "customer_id", "references": "analytics.dim_customer.customer_id"}, {"field": "order_id", "references": "analytics.fact_order.order_id"}],
}

def ddl(table):
    fields = [f'"{name}" {kind}' + ("" if name == "paid_at" else " NOT NULL") for name, kind in COLUMNS[table]]
    return f'CREATE TABLE analytics."{table}" (' + ", ".join(fields + CONSTRAINTS[table]) + ")"
