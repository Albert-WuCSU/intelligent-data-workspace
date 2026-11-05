import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
progress_path = root / "project-control/progress.json"
data = json.loads(progress_path.read_text(encoding="utf-8"))
assert data["revision"] == 165
module = next(item for item in data["modules"] if item["id"] == "M04")
base = "project-control/modules/M04/evidence/20261103T060255Z-sdk-install-plan"


def sha256(relative):
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


package = f"{base}/package-verification.json"
wheel = f"{base}/wheel-inspection.json"
module["implementation_items"].append({
    "id": "M04B-SDK-S01-PACKAGE",
    "status": "done",
    "paths": [package, wheel],
    "description": "锁定SDK0.2.177/CLI2.1.317与Windows wheel哈希；离线dry-run仅新增SDK，未安装/执行/调用模型"
})
module["tests"].append({
    "id": "sdk-package-offline-resolution",
    "required": True,
    "status": "passed",
    "environment": "local",
    "integration": "unit",
    "command": [
        "./services/api/.venv/Scripts/python.exe -I -m pip install --dry-run --no-index --no-cache-dir",
        f"{base}/downloads/win-amd64/claude_agent_sdk-0.2.177-py3-none-win_amd64.whl"
    ],
    "exit_code": 0,
    "code_fingerprint": "7997db488354a539c08b5b6b16717d99ae67903ae7351da43d51b68b80097fad",
    "log": package,
    "evidence_id": "M04B-SDK-PACKAGE-023",
    "scope": "PyPI/GitHub release, Windows wheel SHA/CRC/content, existing dependency versions and offline dry-run; not install/runtime/gateway"
})
module["evidence"].extend([
    {"id": "M04B-SDK-PACKAGE-023", "kind": "test", "path": package, "sha256": sha256(package), "stale": False},
    {"id": "M04B-SDK-WHEEL-024", "kind": "review", "path": wheel, "sha256": sha256(wheel), "stale": False}
])
data["working_state"].insert(0, "2026-11-03 S01包核验：官方SDK0.2.177/捆绑CLI2.1.317；win_amd64 wheel 149800822字节SHA7997db48...与PyPI一致，CRC通过且包含claude.exe；Python3.12.14/AMD64匹配，离线dry-run仅新增SDK且无旧包替换，pip check通过。未安装/执行binary/真实模型调用；WSL status exit50，Windows沙箱可用性未证实。")
data["next_action"]["description"] = "S01包版本/hash/Windows wheel及离线依赖解析已核；继续完成CommercialTerms、AIPlan/Claude模型与Messages tool_use/Skill/stream/usage协议差距、原生Windows runner隔离、有限turn/tool/token/墙钟预算和治理工具合同，再提出明确安装许可点。SDK仍未安装/运行，不重问D070方向、D053预算或PG/生产后补。"
data["next_action"]["read_refs"] = [package, wheel] + [p for p in data["next_action"]["read_refs"] if p not in {package, wheel}]
data["session"] = {"recommend_new_chat": False, "reason": "同一M04-C02-SDK S01调查已续接并在推进，先保存各检查点，无需换窗口。"}
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
