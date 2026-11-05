import json
import pathlib
import sys
from datetime import datetime, timezone

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 167
module = next(item for item in data["modules"] if item["id"] == "M04")
data["decisions"].append({
    "id": "D-M04B-SDK-INSTALL-071",
    "kind": "plan",
    "module_id": "M04",
    "cycle_id": "M04-C02-SDK",
    "source": "user",
    "user_statement": "批准离线安装 (Recommended)",
    "selected_option": "offline-install-and-synthetic-fixture",
    "rationale": "对应D071展示的固定SHA wheel项目venv离线安装＋离线/合成fixture S02；不含真实模型收费、生产SQL、新模型端点、结果行外发、WSL/container安装、部署或push。",
    "recorded_at": datetime.now(timezone.utc).isoformat()
})
data["pending_decision"] = None
data["status"] = "in_progress"
module["phase"] = "do"
module["approvals"]["plan"] = "D-M04B-SDK-INSTALL-071"
data["next_action"] = {
    "kind": "sdk_offline_install_and_fixture",
    "description": "按D071先复核SHA并离线安装SDK0.2.177/CLI2.1.317，再验证import/CLI版本与最小隔离；实现并测试本地假网关＋真实合成MCP的Skill路由→指标优先/受控SQL→确认→执行自动QA→回执发布及有限预算。禁止真实AIPlan/收费/生产查询。",
    "read_refs": ["project-control/modules/M04/SDK_S01_INSTALL_PLAN.md", "project-control/modules/M04/plan.md"],
    "commands": ["services/api/.venv/Scripts/python.exe skills/project-pdca/scripts/progress.py validate --root ."]
}
data["working_state"].insert(0, "2026-11-03用户已明确批准D071 A：固定SHA wheel项目venv离线安装＋离线/合成fixture S02。许可不含真实AIPlan/收费/生产SQL/新端点/结果行外发/WSL/container/部署/push；开始DO，M04仍not_verified。")
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
