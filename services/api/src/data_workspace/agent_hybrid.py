"""Select the governed SDK engine for the approved AI Plan model, legacy otherwise.

The selection is a server-side routing rule, not a runtime fallback: a failure
inside the selected engine stays a failure and is never retried on the other
engine. Personal-API/custom models keep the existing LangGraph task contract.
"""
import asyncio
import hashlib

from .agent_service import AgentService
from .auth import PublicError
from .model_routes import resolve_catalog_model
from .sdk_web_service import SdkWebAgentService

ACTIVE_PHASES = ("PLANNING", "VALIDATING", "EXECUTING", "CHECKING")


class HybridAgentService:
    def __init__(self, app):
        self.app = app
        self.legacy = AgentService(app)
        self.sdk = SdkWebAgentService(app)
        self._engines: dict[str, str] = {}
        self._order: dict[str, int] = {}
        self._counter = 0
        self._start_lock = asyncio.Lock()

    def auth(self, auth):
        self.legacy.auth(auth)

    def capabilities(self):
        sdk = self.sdk.capabilities()
        enabled = bool(getattr(self.app.state.settings, "sdk_web_agent", True))
        binding = bool(sdk["sdk_web_binding"] and enabled)
        engines = ["langgraph_governed_single_table_v1"]
        if binding:
            engines.append("claude_agent_sdk_skills_v1")
        return {
            "available": True,
            "implementation": "claude_agent_sdk_skills_v1" if binding else "langgraph_governed_single_table_v1",
            "sdk_web_binding": binding,
            "engines": engines,
        }

    @property
    def tasks(self):
        value = dict(self.legacy.tasks)
        value.update(self.sdk.tasks)
        return value

    @property
    def records(self):
        value = dict(self.legacy.records)
        value.update({
            task_id: {
                "owner": record.owner,
                "submitted": record.submitted,
                "fingerprint": record.fingerprint,
                "body": record.body,
            }
            for task_id, record in self.sdk.records.items()
        })
        return value

    def _engine(self, task_id):
        name = self._engines.get(task_id)
        if name == "sdk":
            return self.sdk
        if name == "legacy":
            return self.legacy
        if task_id in self.sdk.tasks:
            return self.sdk
        if task_id in self.legacy.tasks:
            return self.legacy
        raise PublicError(404, "AGENT_TASK_NOT_FOUND", "任务不在当前本机会话，请不要重提未知执行。")

    def get(self, auth, task_id):
        return self._engine(task_id).get(auth, task_id)

    def list(self, auth):
        self.auth(auth)
        tasks = self.legacy.list(auth) + self.sdk.list(auth)
        return sorted(tasks, key=lambda task: self._order.get(task.id, 0))

    async def start(self, auth, body):
        self.auth(auth)
        async with self._start_lock:
            owner = self.app.state.sources.owner(auth)
            digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
            for name, service in (("legacy", self.legacy), ("sdk", self.sdk)):
                key = (owner, body.request_id)
                if key not in service.keys:
                    continue
                task_id = service.keys[key]
                record = service.records[task_id]
                fingerprint = record.fingerprint if name == "sdk" else record["fingerprint"]
                if fingerprint != digest:
                    raise PublicError(409, "AGENT_REQUEST_CONFLICT", "同一编号不能用于不同问题。")
                self._engines[task_id] = name
                return service.tasks[task_id]
            legacy_active = any(task.phase in ACTIVE_PHASES for task in self.legacy.tasks.values())
            sdk_active = any(
                not record.terminal and record.task.phase in ACTIVE_PHASES
                for record in self.sdk.records.values()
            )
            if legacy_active or sdk_active:
                raise PublicError(409, "AGENT_BUSY", "已有任务处理，请等待。")
            provider = resolve_catalog_model(self.app, body.model_ref)
            use_sdk = bool(
                getattr(self.app.state.settings, "sdk_web_agent", True)
                and self.sdk.capabilities()["sdk_web_binding"]
                and self.sdk._eligible(provider)
            )
            if use_sdk:
                task = await self.sdk.start(auth, body)
                name = "sdk"
            else:
                task = await self.legacy.start(auth, body)
                name = "legacy"
            self._engines[task.id] = name
            self._counter += 1
            self._order[task.id] = self._counter
            return task

    async def confirm(self, auth, task_id, body):
        return await self._engine(task_id).confirm(auth, task_id, body)

    async def clarify(self, auth, task_id, body):
        engine = self._engine(task_id)
        if engine is not self.sdk:
            engine.get(auth, task_id)
            raise PublicError(409, "AGENT_CLARIFICATION_UNSUPPORTED", "此旧引擎不支持同任务澄清，请补充后新建问题。")
        return await engine.clarify(auth, task_id, body)

    async def cancel(self, auth, task_id):
        return await self._engine(task_id).cancel(auth, task_id)

    async def close(self):
        await self.legacy.close()
        await self.sdk.close()
