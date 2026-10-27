import json
from pathlib import Path
from .main import create_app, CONTRACTS

ROOT = Path(__file__).resolve().parents[4]

def export():
    target = ROOT / "contracts"
    target.mkdir(exist_ok=True)
    for name, model in CONTRACTS.items():
        (target / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (target / "openapi.json").write_text(json.dumps(create_app().openapi(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__":
    export()
