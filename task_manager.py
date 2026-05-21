"""
任务管理器 — 长时间运行任务的进度跟踪和状态查询

支持：
- 任务注册（自动生成 ID）
- 进度更新（当前步骤 / 总步骤 / 状态）
- 状态查询（运行中 / 已完成 / 失败）
- 结果保留（最多保留最近 50 个已完成任务）
- 定时清理过期任务
"""

import time
import uuid
import threading
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """单个任务的状态和结果"""

    def __init__(self, user_input: str):
        self.id: str = uuid.uuid4().hex[:12]
        self.user_input: str = user_input
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.completed_at: float | None = None

        # 进度信息
        self.current_step: int = 0
        self.total_steps: int = 0
        self.step_details: list[dict] = []  # 每步的执行记录

        # 最终结果
        self.result_summary: str = ""
        self.result_data: Any = None
        self.error: str = ""

    def update_progress(self, current: int, total: int, detail: str = ""):
        self.current_step = current
        self.total_steps = total
        self.updated_at = time.time()
        if detail:
            self.step_details.append({
                "step": current,
                "total": total,
                "detail": detail,
                "time": time.time(),
            })

    def mark_completed(self, summary: str = "成功", data: Any = None):
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.updated_at = time.time()
        self.result_summary = summary
        self.result_data = data

    def mark_failed(self, error: str):
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.updated_at = time.time()
        self.error = error

    def mark_cancelled(self):
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_input": self.user_input[:200],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_details": self.step_details[-10:],  # 只返回最近 10 步
            "result_summary": self.result_summary,
            "error": self.error[:500] if self.error else "",
            "elapsed": round(time.time() - self.created_at, 1) if self.status == TaskStatus.RUNNING else (
                round(self.completed_at - self.created_at, 1) if self.completed_at else 0
            ),
        }


class TaskManager:
    """全局任务管理器"""

    def __init__(self, max_completed: int = 50):
        self._tasks: dict[str, Task] = {}
        self._max_completed = max_completed
        self._lock = threading.Lock()

    def create(self, user_input: str) -> Task:
        """创建新任务并返回"""
        with self._lock:
            task = Task(user_input)
            task.status = TaskStatus.RUNNING
            self._tasks[task.id] = task
            return task

    def get(self, task_id: str) -> Task | None:
        """按 ID 查询任务"""
        return self._tasks.get(task_id)

    def all_tasks(self, limit: int = 20) -> list[Task]:
        """获取所有任务，按创建时间倒序"""
        tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return tasks[:limit]

    def active_tasks(self) -> list[Task]:
        """获取正在运行的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def _cleanup_completed(self):
        """清理过多的已完成任务，保留最近 max_completed 个"""
        completed = [t for t in self._tasks.values()
                     if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)]
        if len(completed) > self._max_completed:
            # 按完成时间排序，删除最旧的
            completed.sort(key=lambda t: t.completed_at or 0)
            for t in completed[:len(completed) - self._max_completed]:
                del self._tasks[t.id]

    def remove(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def cleanup_expired(self, max_hours: int = 24):
        """清理超过指定小时数的已完成任务"""
        now = time.time()
        cutoff = now - max_hours * 3600
        with self._lock:
            expired = [
                tid for tid, t in self._tasks.items()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                and (t.completed_at or 0) < cutoff
            ]
            for tid in expired:
                del self._tasks[tid]


# 全局单例
_manager = TaskManager()


def get_task_manager() -> TaskManager:
    return _manager
