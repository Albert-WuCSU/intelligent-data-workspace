import hashlib
import importlib.metadata
import json
import os
import pathlib
import subprocess
import sys

import claude_agent_sdk
from claude_agent_sdk._cli_version import __cli_version__


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    base = pathlib.Path(sys.argv[1]).resolve()
    probe = base / "runtime/cli-version-probe"
    home = probe / "home"
    config = probe / "config"
    temp = probe / "temp"
    for path in (home, config, temp):
        path.mkdir(parents=True, exist_ok=True)
    package_root = pathlib.Path(claude_agent_sdk.__file__).resolve().parent
    cli = package_root / "_bundled" / "claude.exe"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PATHEXT": os.environ.get("PATHEXT", ".EXE"),
        "COMSPEC": os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:/Windows"),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData/Roaming"),
        "LOCALAPPDATA": str(home / "AppData/Local"),
        "TEMP": str(temp),
        "TMP": str(temp),
        "CLAUDE_CONFIG_DIR": str(config),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
        "DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "NO_COLOR": "1",
    }
    completed = subprocess.run(
        [str(cli), "--version"],
        cwd=probe,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    version_output = (completed.stdout or completed.stderr).strip()
    sdk_version = importlib.metadata.version("claude-agent-sdk")
    result = {
        "status": "passed" if sdk_version == "0.2.177" and __cli_version__ == "2.1.317" and completed.returncode == 0 and "2.1.317" in version_output else "failed",
        "sdk_version": sdk_version,
        "cli_version_constant": __cli_version__,
        "cli_version_output": version_output,
        "cli_probe_exit_code": completed.returncode,
        "cli_sha256": sha256(cli),
        "cli_size": cli.stat().st_size,
        "package_root_is_project_venv": "services\\api\\.venv" in str(package_root).lower() or "services/api/.venv" in str(package_root).lower(),
        "network_calls": "not_requested; isolated config and nonessential traffic disabled for --version probe",
        "real_model_call": False,
        "environment_values_recorded": False,
    }
    assert result["status"] == "passed", result
    assert result["package_root_is_project_venv"], package_root
    (base / "install-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
