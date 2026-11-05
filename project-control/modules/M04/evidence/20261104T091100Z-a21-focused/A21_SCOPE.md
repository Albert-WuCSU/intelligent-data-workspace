# A2.1 R-U31/AC05 scope and intermediate CHECK

Self-review, not independent audit or user research. PRD already had D077 conversation principle, but not conventional-Agent observable interaction acceptance; D078 explicitly adds ordered public explanations/tool badges/clarification/prose report as the primary output.

Implemented AgentDialogueEntry: server allowlisted real backend events -> public summaries, stable IDs, compact known tools, ordered question and user answer. No raw model thinking, tool args, rows, SQL, runtime paths or host credentials. User replies remain session-memory only, not full-history model egress or production persistence. Public summaries labelled governed-event rather than model reasoning.

Final answer uses safe limited Markdown (heading/list/emphasis/code, escaped HTML, no links/images/scripts). Exact numeric sentence is rendered from receipt-gated backend result, not model guessing or extra result-row egress. SDK output uses plain inline evidence instead of dominant card shell; legacy baseline keeps its layout. Pipeline/themes/history/right actual evidence retained.

19 focused backend tests passed (new dialogue plus SDK Web), 23 frontend tests and tsc passed, 1 UI-only browser conversational flow passed with ordering/answer/actual badges/no result-card shell/receipt number/refresh/poll failure/themes/mobile. Then only final SDK answer-card CSS was simplified. Complete current-source regression now running; intermediate counts not whole-code acceptance.

No installs, subagents, real model calls, company data/SQL/images copied, host tool exposure, commit/push or budget reset. L2/L3/RAG/report downloads/PythonQA remain later. D053 last observed49/60 estimate units; real retest requires user key and explicit choice/possibly supplemental authorization. No module closure.
