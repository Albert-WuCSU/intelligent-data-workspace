import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 169
module = next(item for item in data["modules"] if item["id"] == "M04")
base = "project-control/modules/M04/evidence/20261103T071717Z-sdk-s02"
results = f"{base}/results.json"
failures = f"{base}/failure-history.json"
sources = f"{base}/source-manifest.json"
summary = json.loads((root / results).read_text(encoding="utf-8"))
fingerprint = summary["source_fingerprint"]


def sha(path):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


module["implementation_items"].append({
    "id": "M04B-SDK-S02-OFFLINE-FIXTURE",
    "status": "done",
    "paths": [
        "services/api/src/data_workspace/sdk_agent_backend.py",
        "services/api/src/data_workspace/sdk_agent_runner.py",
        "services/api/src/data_workspace/sdk_process.py",
        "services/api/src/data_workspace/sdk_runner_entry.py",
        "services/api/src/data_workspace/sdk_skills/data-query/SKILL.md",
        "services/api/tests/test_sdk_agent.py",
        results,
    ],
    "description": "离线SDK/CLI＋受控plugin Skill＋本地假网关＋真实合成MCP：8模型步/7工具，确认/自动QA/回执发布11325；非真实模型/网关"
})
for test in module["tests"]:
    if test["id"] in {"sdk-runtime-compat", "sdk-tool-quality-e2e"}:
        test.update({
            "status": "passed",
            "command": ["./services/api/.venv/Scripts/python.exe -m pytest services/api/tests/test_sdk_agent.py -q"],
            "exit_code": 0,
            "code_fingerprint": fingerprint,
            "log": results,
            "evidence_id": "M04B-SDK-S02-030",
            "scope": "SDK0.2.177/CLI2.1.317真实Windows子进程＋受控plugin Skill＋loopback假Messages＋真实合成MCP；6项通过，8模型步/7工具，宿主全局上下文与结果行均未进模型；不是实际模型/AIPlan证据" if test["id"] == "sdk-tool-quality-e2e" else "SDK0.2.177/CLI2.1.317安装、许可与原生Windows Job隔离fixture通过；非生产/真实网关"
        })
module["evidence"].extend([
    {"id": "M04B-SDK-S02-030", "kind": "test", "path": results, "sha256": sha(results), "stale": False},
    {"id": "M04B-SDK-FAILURES-031", "kind": "review", "path": failures, "sha256": sha(failures), "stale": False},
    {"id": "M04B-SDK-SOURCES-032", "kind": "review", "path": sources, "sha256": sha(sources), "stale": False},
])
data["next_action"]["description"] = "S02离线SDK工具循环已通过：受控plugin Skill→指标优先/受控SQL→明确确认→真实合成MCP→自动QA→回执发布；宿主上下文隔离与Job资源实测通过。下一步冻结指纹并跑完整后端/前端/types/build/pip及文档回归；真实AIPlan/Claude网关仍not_run，不自动收费或生产查询。"
data["next_action"]["read_refs"] = [results, failures, sources, "project-control/modules/M04/SDK_S01_INSTALL_PLAN.md"]
data["working_state"].insert(0, f"2026-11-03 S02离线fixture通过：SDK0.2.177/CLI2.1.317，6项专项，8模型步/7工具/2元数据，真实合成150行聚合11325，自动QA与回执发布；结果行未回传模型，宿主全局CLAUDE.md已隔离。Windows Job峰值8/上限10、内存约531MiB/2GiB；源码指纹{fingerprint}。失败历史保留，真实网关仍not_run。")
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
