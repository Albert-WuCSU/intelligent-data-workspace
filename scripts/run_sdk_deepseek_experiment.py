"""User-operated D-M04B-SDK-REAL-072 D experiment.

One explicitly approved non-Claude compatibility check against the existing
AIPlan coding-plan endpoint.  This is NOT a supported Claude SDK path and does
not close sdk-real-gateway.  The product key is read only from a local hidden
TTY prompt and passed to the isolated child environment; it is never written to
disk or printed.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "scripts"))

from data_workspace.sdk_agent_runner import minimal_runner_environment  # noqa: E402
from data_workspace.sdk_process import run_sdk_process  # noqa: E402
from data_workspace.source_profiles import ProfileDraft, SourceStore  # noqa: E402
from model_key_input import read_model_key  # noqa: E402

MODELS = ("deepseek-v4.1-flash", "deepseek-v4-1-flash-261017")
BASE_URL = "http://ada-cli-golang.ctripcorp.com/coding-plan"
QUESTION = "What is total amount?"


def build_fixture(root: Path) -> Path:
    source = root / "allowed" / "rows.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "id,region,amount,cost,created_at\n"
        + "".join(f'{i},{"A" if i % 2 else "B"},{i},1,2026-10-{(i % 20) + 1:02}\n' for i in range(1, 151)),
        encoding="utf-8",
    )
    store = SourceStore(root / "connections", source.parent)
    database, _ = store.snapshot(ProfileDraft(name="sdk deepseek experiment", path=str(source), usage_authorized=True))
    return database


def redact(value, secret: str):
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, secret) for key, item in value.items()}
    return value


def read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:300_000]


def main() -> int:
    parser = argparse.ArgumentParser(description="D072-D DeepSeek SDK compatibility experiment")
    parser.add_argument("--model", action="append", choices=MODELS, help="repeat to override the default two names")
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--output-root", default=None, help="evidence directory; default project-control/modules/M04/evidence/<utc>-sdk-deepseek-experiment")
    args = parser.parse_args()

    try:
        key = read_model_key()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.output_root:
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=False)
    else:
        base = ROOT / "project-control/modules/M04/evidence"
        output_root = base / f"{stamp}-sdk-deepseek-experiment"
        for index in range(100):
            candidate = output_root if index == 0 else base / f"{stamp}-sdk-deepseek-experiment-{index + 1}"
            try:
                candidate.mkdir(parents=True, exist_ok=False)
                output_root = candidate
                break
            except FileExistsError:
                continue
        else:
            raise SystemExit("无法创建唯一证据目录。")

    database = build_fixture(output_root / "fixture")

    models = tuple(args.model) if args.model else MODELS
    results = []
    try:
        for index, model in enumerate(models, start=1):
            model_dir = output_root / f"model-{index}"
            model_dir.mkdir(parents=True, exist_ok=False)
            task_id = str(uuid.uuid4())
            # Keep the SDK cwd/HOME outside the project tree: the CLI walks up
            # from cwd and would otherwise discover the project's AGENTS.md.
            runtime_root = Path(tempfile.mkdtemp(prefix=f"sdk-d072-{index}-"))
            config = {
                "database": str(database),
                "question": args.question,
                "base_url": BASE_URL,
                "runtime_root": str(runtime_root),
                "task_id": task_id,
                "model": model,
                "mode": "real_gateway_experiment",
                "auto_confirm_fixture": True,
                "wall_clock_seconds": 300,
            }
            config_path = model_dir / "config.json"
            output_path = model_dir / "output.json"
            stdout_path = model_dir / "runner-stdout.txt"
            stderr_path = model_dir / "runner-stderr.txt"
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            env = minimal_runner_environment(model_dir / "outer-home", model_dir / "outer-config", model_dir / "outer-temp")
            env["SDK_EXPERIMENT_AUTH_TOKEN"] = key
            env["SDK_FIXTURE_DEBUG"] = "1"
            completed = None
            error = None
            failure_diagnostics = None
            try:
                completed = run_sdk_process(config_path, output_path, stdout_path, stderr_path, env)
            except Exception as exc:  # evidence must survive a failed run
                error = f"{type(exc).__name__}: {str(exc)[:500]}"
            diagnostic_path = runtime_root / task_id / "failure-diagnostics.json"
            if diagnostic_path.is_file():
                try:
                    failure_diagnostics = json.loads(diagnostic_path.read_text(encoding="utf-8"))
                except ValueError:
                    failure_diagnostics = {"status": "UNREADABLE_DIAGNOSTICS"}
            child = None
            if output_path.is_file():
                try:
                    child = json.loads(output_path.read_text(encoding="utf-8"))
                except ValueError:
                    child = {"status": "UNREADABLE_OUTPUT"}
            results.append(
                {
                    "model": model,
                    "task_id": task_id,
                    "config": config,
                    "runtime_root": str(runtime_root),
                    "runtime_cleaned": True,
                    "process": {k: v for k, v in (completed or {}).items() if k != "result"},
                    "child_output": child,
                    "failure_diagnostics": failure_diagnostics,
                    "stdout": read_text_if_exists(stdout_path),
                    "stderr": read_text_if_exists(stderr_path),
                    "error": error,
                    "status": (child or {}).get("status", "FAILED"),
                }
            )
            shutil.rmtree(runtime_root, ignore_errors=True)
    finally:
        secret = key
        key = ""

    evidence = {
        "decision_id": "D-M04B-SDK-REAL-072",
        "selected_option": "D",
        "kind": "non_claude_sdk_compatibility_experiment",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "official_support": "unsupported_non_claude_experiment",
        "base_url": BASE_URL,
        "question": args.question,
        "models": list(models),
        "auto_confirm_fixture": True,
        "fixture": str(database),
        "budget_contract": {
            "model_steps": 8,
            "tool_calls": 10,
            "metadata_calls": 3,
            "total_tokens": 100000,
            "wall_clock_seconds": 300,
            "estimated_reserve_usd": 2.0,
            "campaign": "D053, no reset; two runs reserve at most 4 USD estimate",
        },
        "results": results,
        "not_run": [
            "authorized Claude model",
            "official Claude SDK gateway compatibility",
            "production/business data",
            "default Web migration",
            "deployment",
        ],
    }
    output_root.joinpath("results.json").write_text(
        json.dumps(redact(evidence, secret), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Evidence: {output_root / 'results.json'}")
    for item in results:
        child = item.get("child_output") or {}
        print(f"{item['model']}: {item['status']} {child.get('error', '')} {item.get('error', '')}".strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
