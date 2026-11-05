import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
data = json.loads((root / "project-control/progress.json").read_text(encoding="utf-8"))
assert data["revision"] == 171
refs = ["project-control/NEW_WINDOW_PROMPT.md", "project-control/HANDOFF_DETAILS.md", "project-control/STATUS.md"]
data["next_action"]["read_refs"] = refs + [path for path in data["next_action"]["read_refs"] if path not in refs]
data["working_state"].insert(0, "2026-11-03用户要求新窗口：已整理最终HANDOFF_DETAILS/STATUS/NEW_WINDOW_PROMPT；revision172仅交接和session更新，未重跑测试。S02 9项专项及602/17/44证据不变，真实AIPlan/Claude/生产/MVP仍not_run。")
data["session"] = {
    "recommend_new_chat": True,
    "reason": "用户明确要求新窗口第一句prompt；已保存S02全部成果和下一步只读网关门禁，续接文件已准备，不自动创建新聊天。"
}
(root / "project-control/progress.draft.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
