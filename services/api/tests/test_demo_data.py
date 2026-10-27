import copy
import json
from pathlib import Path
import tempfile
import pytest
from data_workspace.demo_data.generate import generate, validate, write_dataset, SOURCE


def small(seed=1):
    return generate(seed, customers=12, products=5, orders=30, days=7)


def test_reproducible():
    assert small() == small()
    assert small(1) != small(2)


def test_integrity():
    assert validate(small())["status"] == "passed"


@pytest.mark.parametrize("mutation", ["orphan", "amount", "duplicate", "payment", "partition", "event"])
def test_reject_corruption(mutation):
    data = copy.deepcopy(small())
    if mutation == "orphan":
        data["fact_order_item"][0]["product_id"] = "syn_missing"
    elif mutation == "amount":
        data["fact_order_item"][0]["line_amount_cents"] += 1
    elif mutation == "duplicate":
        data["dim_customer"].append(data["dim_customer"][0].copy())
    elif mutation == "payment":
        data["fact_order"][0]["paid_amount_cents"] += 1
    elif mutation == "partition":
        data["fact_order"][0]["partition_date"] = "1900-01-01"
    else:
        data["fact_event"][0]["customer_id"] = "syn_missing"
    with pytest.raises(ValueError):
        validate(data)


def test_write_provenance_and_no_overwrite(tmp_path):
    target = tmp_path / "seed"
    result = write_dataset(target, seed=1, customers=12, products=5, orders=30, days=7)
    assert result["source"] == SOURCE
    assert result["external_sources"] == []
    assert result["synthetic"] is True
    assert json.loads((target / "manifest.json").read_text())["currency"] == "TEST"
    with pytest.raises(FileExistsError):
        write_dataset(target)


def test_positive_sizes():
    with pytest.raises(ValueError):
        generate(customers=0)
