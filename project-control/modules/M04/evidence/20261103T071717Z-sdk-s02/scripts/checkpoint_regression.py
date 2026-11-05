import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
regression_dir = pathlib.Path(sys.argv[2]).resolve()
relative_regression = regression_dir.relative_to(root).as_posix()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 170
module = next(item for item in data["modules"] if item["id"] == "M04")
s02 = "project-control/modules/M04/evidence/20261103T071717Z-sdk-s02"
results = f"{s02}/results.json"
failures = f"{s02}/failure-history.json"
sources = f"{s02}/source-manifest.json"
regression = f"{relative_regression}/results.json"
regression_sources = f"{relative_regression}/sources.json"
documents = f"{s02}/document-validation-final.json"
summary = json.loads((root / results).read_text(encoding="utf-8"))
regression_summary = json.loads((root / regression).read_text(encoding="utf-8"))
assert summary["status"] == "passed" and summary["tests_passed"] == 9
assert all(check["status"] == "passed" for check in regression_summary["checks"])
fingerprint = summary["source_fingerprint"]
regression_fingerprint = regression_summary["code_fingerprint"]


def sha(path):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


for item in module["implementation_items"]:
    if item["id"] == "M04B-SDK-S02-OFFLINE-FIXTURE":
        item["description"] = "离线SDK/CLI＋受控plugin Skill＋本地假网关＋真实合成MCP：9项专项，8模型步/7工具，确认/自动QA/回执发布11325；路由失效/异常脱敏/usage门禁加强，非真实模型/网关"
        for path in ["services/api/requirements.sdk.lock.txt", "tests/connector.spec.mjs", "DEVELOPMENT.md"]:
            if path not in item["paths"]:
                item["paths"].append(path)
for test in module["tests"]:
    if test["id"] in {"sdk-runtime-compat", "sdk-tool-quality-e2e"}:
        test["code_fingerprint"] = fingerprint
        test["scope"] = test["scope"].replace("6项通过", "9项通过")
    if test["id"] == "sdk-full-regression":
        test.update({
            "status": "passed",
            "command": ["./services/api/.venv/Scripts/python.exe scripts/check.py --module M04 --browser"],
            "exit_code": 0,
            "code_fingerprint": regression_fingerprint,
            "log": regression,
            "evidence_id": "M04B-SDK-FULL-033",
            "scope": "最终源码实际602后端/17前端/44浏览器及types/build/pip全过；包含9项SDK离线fixture，不是实际AIPlan/Claude模型或生产验证"
        })
for evidence in module["evidence"]:
    if evidence["id"] == "M04B-SDK-S02-030":
        evidence["sha256"] = sha(results)
        evidence["stale"] = False
    if evidence["id"] == "M04B-SDK-FAILURES-031":
        evidence["sha256"] = sha(failures)
        evidence["stale"] = False
    if evidence["id"] == "M04B-SDK-SOURCES-032":
        evidence["sha256"] = sha(sources)
        evidence["stale"] = False
module["evidence"].extend([
    {"id": "M04B-SDK-FULL-033", "kind": "test", "path": regression, "sha256": sha(regression), "stale": False},
    {"id": "M04B-SDK-FULL-SOURCES-034", "kind": "review", "path": regression_sources, "sha256": sha(regression_sources), "stale": False},
    {"id": "M04B-SDK-DOCS-035", "kind": "test", "path": documents, "sha256": sha(documents), "stale": False},
])
for risk in module["risks"]:
    if risk["id"] == "M04B-R-SDK-ISOLATION":
        risk["description"] = "原生Windows最小环境＋受控plugin＋专属Job离线fixture已验证，宿主全局CLAUDE.md与结果行均未进入模型；生产文件/网络沙箱、多租户、WSL/container及长期资源恢复仍not_run。"
    if risk["id"] == "M04B-R-DEPENDENCY-EGRESS":
        risk["description"] = "SDK0.2.177/CLI2.1.317已按D071离线安装并锁hash，非必要流量/外部trace禁用；真实模型/第三方网关数据外发、部署分发条款和真实费用仍待独立门禁。"
data["next_action"] = {
    "kind": "sdk_real_gateway_prerequisites",
    "description": "S02离线SDK与全量回归已通过。下一步先只读确认AIPlan是否存在账号授权的Claude模型及对应base URL/auth和Messages/tool_use/Skill/stream/usage能力，再另列用户显式真实SDK最小测试许可；仅DeepSeek则真实SDK保持not_run，不自动收费、换模型/端点/供应商或回退LangGraph。",
    "read_refs": ["project-control/modules/M04/SDK_S02_OFFLINE_FIXTURE.md", results, regression],
    "commands": ["services/api/.venv/Scripts/python.exe skills/project-pdca/scripts/progress.py validate --root ."]
}
data["working_state"].insert(0, f"2026-11-03 S02最终：9项SDK离线专项与602后端/17前端/44浏览器/types/build/pip全部通过；S02指纹{fingerprint}，全回归指纹{regression_fingerprint}。宿主上下文/结果行隔离、路由失效、异常脱敏、usage与Windows Job上限均实测；真实AIPlan/Claude/生产仍not_run，M04未整体验收。")
data["session"] = {"recommend_new_chat": True, "reason": "S02离线实现与全量回归已保存，下一阶段转为真实网关模型/协议门禁，适合在检查点换窗口恢复，不自动创建。"}
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
