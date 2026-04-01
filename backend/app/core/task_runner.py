"""
Abstraction pour l'exécution de tâches longues en background.

Aujourd'hui : exécution in-process via threading (LocalTaskRunner).
Futur : Celery workers distribués (CeleryTaskRunner — même interface).

Usage dans les routes FastAPI :
    from app.core.task_runner import get_task_runner
    task_runner = get_task_runner()
    task_id = task_runner.submit(my_func, arg1, arg2, kwarg1=val)
"""

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    task_id: str
    status: TaskStatus
    created_at: datetime
    error: str | None = None


class TaskRunner(ABC):
    """Interface commune pour l'exécution de tâches en background."""

    @abstractmethod
    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Soumet une tâche. Retourne un task_id unique."""
        ...

    @abstractmethod
    def get_status(self, task_id: str) -> TaskStatus:
        """Retourne le statut d'une tâche."""
        ...

    @abstractmethod
    def cancel(self, task_id: str) -> bool:
        """Annule une tâche. Retourne True si la tâche a été trouvée et annulée."""
        ...


class LocalTaskRunner(TaskRunner):
    """Implémentation in-process via threading.

    Chaque appel à submit() lance un daemon thread. Le statut est suivi
    dans un dictionnaire en mémoire. Adapté au dev et aux déploiements
    mono-worker. Pour du multi-worker distribué, utiliser CeleryTaskRunner.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        task_id = str(uuid.uuid4())
        info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._tasks[task_id] = info

        def _wrapper() -> None:
            with self._lock:
                if self._tasks[task_id].status == TaskStatus.CANCELLED:
                    return
                self._tasks[task_id].status = TaskStatus.RUNNING
            try:
                func(*args, **kwargs)
                with self._lock:
                    if self._tasks[task_id].status != TaskStatus.CANCELLED:
                        self._tasks[task_id].status = TaskStatus.COMPLETED
            except Exception as exc:
                logger.exception("Task %s failed", task_id)
                with self._lock:
                    self._tasks[task_id].status = TaskStatus.FAILED
                    self._tasks[task_id].error = str(exc)[:500]

        thread = threading.Thread(target=_wrapper, daemon=True, name=f"task-{task_id[:8]}")
        with self._lock:
            self._threads[task_id] = thread
        thread.start()

        logger.info("Task %s submitted (func=%s)", task_id, getattr(func, "__qualname__", repr(func)))
        return task_id

    def get_status(self, task_id: str) -> TaskStatus:
        with self._lock:
            info = self._tasks.get(task_id)
        if info is None:
            raise KeyError(f"Task {task_id} inconnue")
        return info.status

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            info = self._tasks.get(task_id)
            if info is None:
                return False
            if info.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            info.status = TaskStatus.CANCELLED
        logger.info("Task %s marked as cancelled", task_id)
        return True


class SyncTaskRunner(TaskRunner):
    """Implémentation synchrone pour les tests.

    Exécute les tâches immédiatement dans le thread appelant.
    Ne pas utiliser en production.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        task_id = str(uuid.uuid4())
        info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
        )
        self._tasks[task_id] = info
        try:
            func(*args, **kwargs)
            info.status = TaskStatus.COMPLETED
        except Exception as exc:
            info.status = TaskStatus.FAILED
            info.error = str(exc)[:500]
        return task_id

    def get_status(self, task_id: str) -> TaskStatus:
        info = self._tasks.get(task_id)
        if info is None:
            raise KeyError(f"Task {task_id} inconnue")
        return info.status

    def cancel(self, task_id: str) -> bool:
        return False  # Synchronous tasks are already done


# ── Singleton ─────────────────────────────────────────────────────────

_task_runner: TaskRunner | None = None
_runner_lock = threading.Lock()


def get_task_runner() -> TaskRunner:
    """Retourne le TaskRunner singleton (LocalTaskRunner par défaut)."""
    global _task_runner
    if _task_runner is None:
        with _runner_lock:
            if _task_runner is None:
                _task_runner = LocalTaskRunner()
    return _task_runner


def set_task_runner(runner: TaskRunner) -> None:
    """Remplace le TaskRunner singleton (utile pour les tests ou Celery)."""
    global _task_runner
    with _runner_lock:
        _task_runner = runner
