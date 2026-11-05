import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
base = root / "project-control/modules/M04/evidence/20261103T060255Z-sdk-install-plan"
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


package = json.loads((base / "package-verification.json").read_text(encoding="utf-8"))
wheel = json.loads((base / "wheel-inspection.json").read_text(encoding="utf-8"))
manifest = json.loads((base / "source-manifest.json").read_text(encoding="utf-8"))
release = json.loads((base / "downloads/github-release/latest.json").read_text(encoding="utf-8"))
check("sdk_release_version", package["release"]["sdk_version"] == "0.2.177" == release["tag_name"].removeprefix("v"))
check("cli_release_version", package["release"]["bundled_cli_version"] == "2.1.317" and "2.1.317" in release["body"])
artifact = next(item for item in package["artifacts"] if item["filename"].endswith("win_amd64.whl"))
wheel_path = base / "downloads/win-amd64" / artifact["filename"]
check("wheel_size", wheel_path.stat().st_size == artifact["size"] == 149800822)
check("wheel_hash", sha256(wheel_path) == artifact["sha256"] == wheel["sha256"])
check("wheel_crc", wheel["crc_failure"] is None)
check("wheel_not_executed", wheel["executed"] is False and wheel["installed"] is False)
check("offline_resolution", package["offline_resolution"]["exit_code"] == 0 and package["offline_resolution"]["existing_packages_replaced"] == [])
for source in manifest["sources"]:
    path = base / source["path"]
    check(f"source_bytes:{source['name']}", path.stat().st_size == source["bytes"])
    check(f"source_hash:{source['name']}", sha256(path) == source["sha256"])
texts = {source["name"]: (base / source["path"]).read_text(encoding="utf-8", errors="replace") for source in manifest["sources"]}
check("legal_unmodified_binary", "The Claude Code binary must not be modified" in texts["legal-and-compliance"])
check("legal_no_intermediation", "Customers may not pay for, resell, or intermediate Claude usage" in texts["legal-and-compliance"])
check("gateway_non_claude_unsupported", "doesn't support routing Claude Code to non-Claude models" in texts["llm-gateway"])
check("gateway_messages_endpoint", "/v1/messages" in texts["llm-gateway-protocol"] and "message_stop" in texts["llm-gateway-protocol"])
check("native_windows_unsandboxed", "On native Windows, Claude Code runs commands unsandboxed" in texts["sandboxing"])
check("cost_not_billing", "client-side estimates, not authoritative billing data" in texts["sdk-cost-tracking"])
check("settings_not_complete_isolation", "Always read" in texts["sdk-features"] and "Auto memory" in texts["sdk-features"])
check("custom_tool_policy_typescript_only", "The field is TypeScript-only" in texts["sdk-custom-tools"])
report = (root / "project-control/modules/M04/SDK_S01_INSTALL_PLAN.md").read_text(encoding="utf-8")
check("install_decision_present", "D-M04B-SDK-INSTALL-071" in report)
check("runtime_still_not_run", "SDK 安装、运行、真实网关与 MVP 仍 `not_run`" in report)
summary = {
    "status": "passed",
    "kind": "s01_evidence_self_review",
    "checks_passed": len(checks),
    "checks": checks,
    "scope": "Official metadata, downloaded source integrity, legal/protocol claims and plan consistency; not SDK install/runtime/gateway/product regression.",
    "not_run": ["SDK install/import/CLI", "real model/gateway", "tool_use/Skill/stream/usage E2E", "production/MVP"]
}
(base / "validation-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": summary["status"], "checks_passed": len(checks)}, ensure_ascii=False))
