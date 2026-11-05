# A2 implementation contract (self_review, not acceptance)

- Baseline recovery: revision186 valid. Existing reliability patch is being checked by `scripts/check.py --module M04 --browser`; only completed results.json can establish pass.
- Verified listener ancestry: API31844 -> venv launcher20800 -> dev launcher33624; Vite31644 ->33624. All are this project. No credentials inspected; no real model calls.
- A2 clarification uses the SAME running SDK tool request and task ID, not a new paid task or SDK resume. Server-authenticated answer file is bound to owner, generation, task binding, random clarification ID and idempotent answer request ID. Recheck current model/source/semantic/schema before delivering an answer.
- At most two clarification rounds; each answer <=1600 characters with explicit question-egress consent. No result rows or browser history sent to model. SQL confirmation remains separate and mandatory after re-planning.
- Waiting stays inside the existing 1260s outer wall / 600s model budget configuration; no automatic extension, reservation reset, refund, fallback or retry. Timeout/cancel/expired binding cannot resume. This is process-local continuity, NOT durable production persistence.
- UI puts Agent narration and clarification turns before embedded result evidence. Interleave each task under its original user message using request_id. Retain received tasks on transient polling failure; real progress only. SQL/receipt details stay collapsed.
- CHECK needs synthetic SDK+MCP same-task clarify/confirm/execute, stale/duplicate/cancel safety; browser continuity/theme/refresh/poll-failure checks; full backend/frontend/types/build/pip/browser. Real DeepSeek retest requires user Key and explicit actions; Claude/production/MVP remain not_run.
