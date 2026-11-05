import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 168
module = next(item for item in data["modules"] if item["id"] == "M04")
base = "project-control/modules/M04/evidence/20261103T060255Z-sdk-install-plan"
evidence = f"{base}/install-verification.json"
sha = hashlib.sha256((root / evidence).read_bytes()).hexdigest()
module["implementation_items"].append({
    "id": "M04B-SDK-S02-INSTALL",
    "status": "done",
    "paths": [evidence],
    "description": "D071固定wheel离线安装完成；SDK0.2.177/CLI2.1.317 import与隔离version probe通过，无真实模型调用"
})
module["tests"].append({
    "id": "sdk-install-version",
    "required": True,
    "status": "passed",
    "environment": "local",
    "integration": "unit",
    "command": ["./services/api/.venv/Scripts/python.exe -I", f"{base}/scripts/verify_install.py", base],
    "exit_code": 0,
    "code_fingerprint": "26b01ec22df2c17ac7f5703aa547d36706e8d58412136ced0344a8ced4d86038",
    "log": evidence,
    "evidence_id": "M04B-SDK-INSTALL-029",
    "scope": "项目venv import、CLI2.1.317实际version probe、binary SHA、隔离HOME/config/禁非必要流量；pip check通过；不含Agent loop/网关"
})
module["evidence"].append({"id": "M04B-SDK-INSTALL-029", "kind": "test", "path": evidence, "sha256": sha, "stale": False})
data["next_action"]["description"] = "SDK0.2.177/CLI2.1.317已按D071离线安装并验证版本。继续实现最小隔离runner/版本化Skills/治理工具与预算，使用本地假Anthropic Messages网关和真实合成MCP验证Skill→指标/SQL→确认→执行自动QA→回执发布；禁止真实AIPlan/收费/生产查询。"
data["next_action"]["read_refs"] = [evidence, "project-control/modules/M04/SDK_S01_INSTALL_PLAN.md", "project-control/modules/M04/plan.md"]
data["working_state"].insert(0, "2026-11-03 D071安装检查点：固定SHA wheel离线安装成功，SDK0.2.177 import、CLI2.1.317 (Claude Code)隔离version probe退出0，CLI SHA256=26b01ec22df2c17ac7f5703aa547d36706e8d58412136ced0344a8ced4d86038，pip check通过。未真实模型/AIPlan调用；下一步本地假网关＋合成MCP fixture。")
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
