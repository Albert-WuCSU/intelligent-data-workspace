"""Process-local task receipts; no durable recovery or cancel claim."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from threading import Lock
from uuid import uuid4
import duckdb
from pydantic import ValidationError
from .policy import PreviewRequest, QueryDenied, compile_preview
from .engine import WarehouseError

class ExecutionService:
    def __init__(self, warehouse):
        self.warehouse = warehouse
        self.lock = Lock()
        self.running = False
        self.tasks = {}
        self.keys = {}

    def submit(self, request, key):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key):
            return {"ok": False, "error": {"code": "INVALID_REQUEST", "safe_message": "Invalid idempotency key."}}
        _, _, request = compile_preview(request,getattr(self.warehouse,"catalog",None))
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        with self.lock:
            if key in self.keys:
                task_id = self.keys[key]
                if self.tasks[task_id]["fingerprint"] != fingerprint:
                    return {"ok": False, "error": {"code": "IDEMPOTENCY_CONFLICT", "safe_message": "Key already used for a different plan."}}
                return {"ok": True, "task": self.status(task_id, locked=True)}
            if self.running or len(self.tasks) >= 100:
                return {"ok": False, "error": {"code": "CAPACITY_EXCEEDED", "safe_message": "One active query and 100 receipts per process are allowed."}}
            task_id = str(uuid4())
            self.tasks[task_id] = {"task_id": task_id, "status": "RUNNING", "created_at": datetime.now(timezone.utc).isoformat(), "fingerprint": fingerprint, "result": None, "error": None}
            self.keys[key] = task_id
            self.running = True
        result, error = None, None
        try:
            result = self.warehouse.preview(request)
        except duckdb.InterruptException:
            error = {"code": "QUERY_INTERRUPTED", "safe_message": "The engine was interrupted by the local deadline; no result was published."}
        except Exception:
            error = {"code": "QUERY_FAILED", "safe_message": "Local query failed; no raw SQL or engine exception is returned."}
        with self.lock:
            task = self.tasks[task_id]
            task.update(status="FAILED" if error else "SUCCEEDED", result=result, error=error)
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.running = False
            return {"ok": True, "task": self.status(task_id, locked=True)}

    def status(self, task_id, locked=False):
        if not locked:
            with self.lock:
                return self.status(task_id, locked=True)
        if task_id not in self.tasks:
            return {"ok": False, "error": {"code": "TASK_NOT_FOUND", "safe_message": "Task unavailable in this process scope."}}
        return deepcopy({k:v for k,v in self.tasks[task_id].items() if k not in {"result", "fingerprint"}})

    def result(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                return {"ok": False, "error": {"code": "TASK_NOT_FOUND", "safe_message": "Task unavailable in this process scope."}}
            task = self.tasks[task_id]
            if task["status"] != "SUCCEEDED":
                return {"ok": False, "error": task["error"] or {"code": "NOT_READY", "safe_message": "Query still running."}}
            return {"ok": True, "result": deepcopy(task["result"])}
