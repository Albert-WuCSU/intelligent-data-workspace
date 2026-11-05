import hashlib
import json
import pathlib
import sys
import zipfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    wheel = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2])
    result = {
        "file": wheel.name,
        "size": wheel.stat().st_size,
        "sha256": sha256(wheel),
        "executed": False,
        "installed": False,
    }
    with zipfile.ZipFile(wheel) as archive:
        result["crc_failure"] = archive.testzip()
        infos = archive.infolist()
        result["file_count"] = len(infos)
        result["largest_files"] = [
            {"name": item.filename, "size": item.file_size, "compressed_size": item.compress_size}
            for item in sorted(infos, key=lambda entry: entry.file_size, reverse=True)[:20]
        ]
        result["cli_candidates"] = [
            item.filename
            for item in infos
            if item.filename.lower().endswith((".exe", ".cmd", ".bat", "cli.js"))
            or "cli_version" in item.filename.lower()
        ]
        metadata_names = [
            item.filename
            for item in infos
            if item.filename.endswith((".dist-info/METADATA", ".dist-info/WHEEL"))
            or "license" in pathlib.PurePosixPath(item.filename).name.lower()
        ]
        result["metadata"] = {}
        for name in metadata_names:
            data = archive.read(name)
            if len(data) <= 300_000:
                result["metadata"][name] = data.decode("utf-8", errors="replace")
        needles = (
            "2.1.317",
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "setting_sources",
            "max_budget_usd",
            "max_turns",
            "allowed_tools",
            "disallowed_tools",
            "can_use_tool",
            "permission_mode",
            "skills",
            "env=",
        )
        matches = []
        for item in infos:
            if not item.filename.endswith((".py", ".json", ".md", ".txt")) or item.file_size > 2_000_000:
                continue
            text = archive.read(item).decode("utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if any(needle in line for needle in needles):
                    matches.append({"file": item.filename, "line": number, "text": line.strip()[:1000]})
        result["source_matches"] = matches
        result["source_match_count"] = len(matches)
        excerpt_specs = {
            "claude_agent_sdk/types.py": [(2338, 2362), (2660, 2710)],
            "claude_agent_sdk/_internal/transport/subprocess_cli.py": [
                (527, 568),
                (591, 637),
                (813, 881),
            ],
        }
        result["source_excerpts"] = {}
        for name, ranges in excerpt_specs.items():
            lines = archive.read(name).decode("utf-8", errors="replace").splitlines()
            result["source_excerpts"][name] = [
                {
                    "start": start,
                    "end": end,
                    "text": "\n".join(
                        f"{number}: {lines[number - 1]}"
                        for number in range(start, min(end, len(lines)) + 1)
                    ),
                }
                for start, end in ranges
            ]
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"metadata", "source_matches"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
