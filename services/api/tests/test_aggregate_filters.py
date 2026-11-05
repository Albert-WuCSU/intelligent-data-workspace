"""Governed filter contract and engine tests; no free SQL, rows stay local."""
from datetime import date

import pytest
from pydantic import ValidationError

from data_workspace.warehouse.aggregate_contract import (
    AggregateFilter,
    AggregateRequest,
    AggregateTime,
    compile_aggregate,
    schema_hash,
    validate_aggregate,
)
from data_workspace.warehouse.aggregate_engine import execute_aggregate
from data_workspace.warehouse.local_file import LocalFileWarehouse
from data_workspace.warehouse.policy import QueryDenied
from test_agent import fixture, metric


def warehouse(tmp_path):
    store, database = fixture(tmp_path)
    value = LocalFileWarehouse(database)
    return value, value.describe("t0")


def request(description, **changes):
    value = AggregateRequest(table="t0", schema_hash=schema_hash(description), metric=metric(), grain=["id"])
    return value.model_copy(update=changes)


def test_filter_eq_in_gte_and_time_compile_and_execute_full_input(tmp_path):
    subject, description = warehouse(tmp_path)
    base = request(description)
    assert execute_aggregate(subject, base).rows == [[11325]]

    region_a = request(description, filters=[AggregateFilter(column="region", operator="eq", values=["A"])])
    result = execute_aggregate(subject, region_a)
    assert result.matched_rows == 75 and result.rows == [[5625]] and result.full_input_aggregate

    id_in = request(description, filters=[AggregateFilter(column="id", operator="in", values=[1, 2, 3])])
    result = execute_aggregate(subject, id_in)
    assert result.matched_rows == 3 and result.rows == [[6]]

    amount_gte = request(description, filters=[AggregateFilter(column="amount", operator="gte", values=[100])])
    result = execute_aggregate(subject, amount_gte)
    assert result.matched_rows == 51 and result.rows == [[6375]]

    time_and_filter = request(
        description,
        time_filter=AggregateTime(column="created_at", start=date(2026, 10, 1), end_exclusive=date(2026, 10, 11)),
        filters=[AggregateFilter(column="region", operator="eq", values=["A"])],
    )
    result = execute_aggregate(subject, time_and_filter)
    assert result.matched_rows == 40 and result.rows == [[3000]]

    sql, params, _, _ = compile_aggregate(region_a, description)
    assert '"region" = ?' in sql and params == ["A"]
    sql, params, _, _ = compile_aggregate(id_in, description)
    assert '"id" IN (?,?,?)' in sql and params == [1, 2, 3]
    validate_aggregate(sql, sql, description, id_in)


def test_filter_unknown_field_type_and_limits_are_denied_without_execution(tmp_path):
    subject, description = warehouse(tmp_path)
    with pytest.raises((QueryDenied, ValidationError)):
        execute_aggregate(subject, request(description, filters=[AggregateFilter(column="missing", operator="eq", values=["x"])]))
    with pytest.raises((QueryDenied, ValidationError)):
        execute_aggregate(subject, request(description, filters=[AggregateFilter(column="amount", operator="eq", values=["not-a-number"])]))
    with pytest.raises((QueryDenied, ValidationError)):
        execute_aggregate(subject, request(description, filters=[AggregateFilter(column="region", operator="eq", values=[1])]))
    with pytest.raises((QueryDenied, ValidationError)):
        execute_aggregate(subject, request(description, filters=[AggregateFilter(column="created_at", operator="gte", values=["not-a-date"])]))
    with pytest.raises(ValidationError):
        AggregateFilter(column="region", operator="eq", values=["A", "B"])
    with pytest.raises(ValidationError):
        AggregateFilter(column="region", operator="eq", values=[True])
    with pytest.raises(ValidationError):
        AggregateFilter(column="region", operator="in", values=["x"] * 201)
    with pytest.raises(ValidationError):
        AggregateRequest(
            table="t0",
            schema_hash=schema_hash(description),
            metric=metric(),
            grain=["id"],
            filters=[AggregateFilter(column="region", operator="eq", values=["A"])] * 6,
        )
    sql, _, _, _ = compile_aggregate(request(description, filters=[AggregateFilter(column="region", operator="eq", values=["A"])]), description)
    with pytest.raises(QueryDenied):
        validate_aggregate(sql + " -- bypass", sql, description, request(description))
    with pytest.raises(QueryDenied):
        validate_aggregate(sql.replace('"region" = ?', "read_csv('x') = ?"), sql, description, request(description))
