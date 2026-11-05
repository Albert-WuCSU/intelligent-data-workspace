"""Fixed subprocess entry for the offline SDK fixture; arguments are nonsecret paths."""
import asyncio
import json
import os
from pathlib import Path
import sys

from .auth import PublicError
from .sdk_agent_runner import SdkRunnerConfig, run_sdk_fixture


def main():
    config_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    try:
        config = SdkRunnerConfig.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
        result = asyncio.run(run_sdk_fixture(config))
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": result["status"], "output": str(output_path)}, ensure_ascii=False))
        return 0
    except PublicError as exc:
        result = {"status": "FAILED", "error": exc.code, "message": exc.message}
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 2
    except Exception as exc:
        if os.environ.get("SDK_FIXTURE_DEBUG") == "1":
            import traceback
            traceback.print_exc()
        result = {"status": "FAILED", "error": type(exc).__name__, "message": "离线runner未完成，请查看fixture诊断。"}
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
