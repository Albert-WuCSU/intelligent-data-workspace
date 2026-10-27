"""Owned synthetic warehouse; never connected to external enterprise data."""
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SEED = PROJECT_ROOT / "data/demo/synthetic-v1"
DEFAULT_WAREHOUSE = PROJECT_ROOT / "data/warehouse/synthetic-v1"
