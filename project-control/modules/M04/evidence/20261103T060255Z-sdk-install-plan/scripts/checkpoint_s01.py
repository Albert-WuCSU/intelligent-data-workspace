import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 166
module = next(item for item in data["modules"] if item["id"] == "M04")
base = "project-control/modules/M04/evidence/20261103T060255Z-sdk-install-plan"
report = "project-control/modules/M04/SDK_S01_INSTALL_PLAN.md"
manifest = f"{base}/source-manifest.json"
validation = f"{base}/validation-summary.json"
documents = f"{base}/document-validation.json"


def sha256(relative):
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


module["implementation_items"].append({
    "id": "M04B-SDK-S01-CONTRACT",
    "status": "done",
    "paths": [report, manifest, validation, documents, "project-control/modules/M04/plan.md", "project-control/prd/M04-B.md"],
    "description": "S01法律/AIPlan协议差距/Windows隔离/有限多轮预算/治理工具合同与D071安装许可点；SDK运行仍未实现"
})
module["tests"].append({
    "id": "sdk-s01-evidence-review",
    "required": True,
    "status": "passed",
    "environment": "local",
    "integration": "unit",
    "command": ["./services/api/.venv/Scripts/python.exe -I", f"{base}/scripts/verify_s01.py", "."],
    "exit_code": 0,
    "code_fingerprint": sha256(report),
    "log": validation,
    "evidence_id": "M04B-SDK-VALIDATION-027",
    "scope": "45项官方元数据/下载源hash/法律协议断言/计划一致性；另PRD13模块60需求、31tests+9subtests通过；非SDK运行或真实网关"
})
module["evidence"].extend([
    {"id": "M04B-SDK-S01-PLAN-025", "kind": "review", "path": report, "sha256": sha256(report), "stale": False},
    {"id": "M04B-SDK-SOURCES-026", "kind": "review", "path": manifest, "sha256": sha256(manifest), "stale": False},
    {"id": "M04B-SDK-VALIDATION-027", "kind": "test", "path": validation, "sha256": sha256(validation), "stale": False},
    {"id": "M04B-SDK-DOC-VALIDATION-028", "kind": "test", "path": documents, "sha256": sha256(documents), "stale": False}
])
for risk in module["risks"]:
    if risk["id"] == "M04B-R-SDK-COMPAT":
        risk["description"] = "官方不支持Claude Code经网关路由非Claude模型；现有AIPlan/DeepSeek文本与固定流式不属于受支持SDK路径。授权Claude模型、base URL/auth、tool_use/Skill/stream/usage实测仍not_run；不自动换模型/端点/供应商。"
    if risk["id"] == "M04B-R-SDK-ISOLATION":
        risk["description"] = "原生Windows官方命令沙箱不可用，WSL status exit50；最小父环境/独立cwd/config/版本化Skills/仅Skill+受治理MCP/资源墙钟门禁仅S01方案，runner实现与隔离攻击测试not_run。"
if not any(item.get("id") == "aiplan-claude-sdk-model" for item in data.get("open_questions", [])):
    data.setdefault("open_questions", []).append({
        "id": "aiplan-claude-sdk-model",
        "description": "真实SDK网关门禁前需用户确认AIPlan获授权Claude模型及对应base URL/auth和Messages/tool_use/Skill/stream/usage能力；不得猜目录或批量收费试模型。仅DeepSeek则真实SDK兼容保持not_run，不阻断离线安装/fixture。"
    })
data["pending_decision"] = {
    "id": "D-M04B-SDK-INSTALL-071",
    "blocking": True,
    "module_id": "M04",
    "cycle_id": "M04-C02-SDK",
    "question": "是否批准仅安装SHA已核的claude-agent-sdk 0.2.177（捆绑CLI 2.1.317）到项目venv，并实施离线/合成fixture S02，不进行真实模型收费或生产查询？",
    "recommended": "A",
    "options": [
        {
            "id": "A",
            "label": "仅安装＋离线/合成fixture（推荐）",
            "tradeoff": "固定wheel离线安装且不替换旧包；可验证Windows runner/Skills/治理工具与预算，但不证明AIPlan/Claude真实兼容。含每任务8模型步/10工具/100K tokens/300秒/2USD估算预留子合同。"
        },
        {
            "id": "B",
            "label": "暂不安装，仅保留S01报告",
            "tradeoff": "不改变环境，保留已核安装包与方案；SDK实现和离线证据继续not_run，方向不变。"
        }
    ],
    "affected_modules": ["M04"],
    "excludes": [
        "真实AIPlan或其他模型POST/收费",
        "生产SQL或新数据外发",
        "新模型/端点/账号或自动fallback",
        "结果行/完整结果回传模型",
        "WSL/container安装或生产部署",
        "宿主Key/settings/hooks读取",
        "Git push"
    ]
}
data["status"] = "awaiting_decision"
data["next_action"] = {
    "kind": "sdk_install_approval",
    "decision_id": "D-M04B-SDK-INSTALL-071",
    "description": "等待用户只回答D071安装许可；A为固定SHA wheel项目venv离线安装＋离线/合成fixture，B为暂不安装。未回答前不安装/不执行CLI/不调用真实模型。SDK方向、D053预算及PG/生产后补不重问。",
    "read_refs": [report, "project-control/modules/M04/plan.md", documents, f"{base}/package-verification.json"],
    "commands": ["services/api/.venv/Scripts/python.exe skills/project-pdca/scripts/progress.py validate --root ."]
}
data["working_state"].insert(0, "2026-11-03 S01完成：SDK0.2.177/CLI2.1.317包与Windows hash/许可/协议/隔离/预算/工具合同已归档；45项证据自审、PRD13模块60需求、31tests+9subtests通过，安装副本一致。AIPlan/DeepSeek非官方支持Claude Code模型路径，真实SDK需授权Claude模型。当前D071待用户批准仅离线安装+fixture；SDK安装/运行/真实网关仍not_run，未改产品源码/未push，MVP未完成。")
data["session"] = {"recommend_new_chat": False, "reason": "S01已形成单一安装许可点，用户可在当前对话直接回答D071；无需换窗口。"}
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
