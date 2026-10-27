from threading import Lock
from typing import Protocol
from .contracts import AuthContext, Task
from .auth import PublicError

class TaskRepository(Protocol):
    def add(self, task: Task) -> Task: ...
    def get(self, task_id: str, auth: AuthContext) -> Task: ...

class MemoryTaskRepository:
    """Bounded, process-local storage. Not a durable queue or production repository."""
    def __init__(self, capacity=1000):
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()
        self.capacity = capacity

    def add(self, task):
        with self._lock:
            if len(self._tasks) >= self.capacity:
                raise PublicError(503, "CAPACITY_EXCEEDED", "本地任务容量已满，请重启开发服务。")
            if task.task_id in self._tasks:
                raise PublicError(409, "TASK_CONFLICT", "任务已存在。")
            self._tasks[task.task_id] = task.model_copy(deep=True)
            return task.model_copy(deep=True)

    def get(self, task_id, auth):
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or (task.tenant_id, task.principal_id) != (auth.tenant_id, auth.principal_id):
                raise PublicError(404, "TASK_NOT_FOUND", "任务不存在或不可访问。")
            return task.model_copy(deep=True)
