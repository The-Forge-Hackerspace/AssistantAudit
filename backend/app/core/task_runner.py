"""
Abstraction pour l'exécution de tâches longues en background.

Aujourd'hui : exécution in-process via threading (LocalTaskRunner).
Futur : Celery workers distribués (CeleryTaskRunner — même interface).

Usage dans les routes FastAPI :
    from app.core.task_runner import get_task_runner
    task_runner = get_task_runner()
    task_id = task_runner.submit(my_func, arg1, arg2, kwarg1=val)

Shutdown gracieux (TOS-79 / US046) :
    runner.shutdown(timeout=10.0)  # pose _stop, join chaque thread.
    Les workers longs doivent regulierement checker `runner.is_stopping()`
    pour sortir proprement avant le timeout.
"""

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
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

    def is_stopping(self) -> bool:
        """Indique si le runner est en train de s'arrêter (par défaut False)."""
        return False

    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Arrêt gracieux. Implémentation par défaut : no-op."""
        return None


class LocalTaskRunner(TaskRunner):
    """Implémentation in-process via threading.

    Chaque appel à submit() lance un daemon thread. Le statut est suivi
    dans un dictionnaire en mémoire. Adapté au dev et aux déploiements
    mono-worker. Pour du multi-worker distribué, utiliser CeleryTaskRunner.

    Shutdown gracieux (TOS-79) :
      - `_stop` est un `threading.Event` partagé. Les workers longs doivent
        appeler periodiquement `runner.is_stopping()` pour sortir avant
        que `shutdown()` ne timeout.
      - `submit()` apres `shutdown()` est rejete (RuntimeError).
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        # Event partage : pose par shutdown(), check par les workers via is_stopping().
        self._stop = threading.Event()

    def is_stopping(self) -> bool:
        """True si shutdown() a ete demande. Les workers doivent sortir proprement."""
        return self._stop.is_set()

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        if self._stop.is_set():
            # Plus aucune nouvelle tache acceptee une fois shutdown declenche.
            raise RuntimeError("TaskRunner is shutting down; submit refused")

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

    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Arrêt gracieux du runner (TOS-79 / AC1, AC6).

        - Pose `_stop` (les workers checkent `is_stopping()` pour sortir).
        - Marque toutes les taches encore PENDING/RUNNING comme CANCELLED
          (visibilite ops + AC5 partiel).
        - Si `wait=True` : join chaque thread vivant avec `timeout` *partage*
          (le total ne depasse pas timeout, pas par-thread).
        - Logge un warning par thread non joint pour visibilite ops (AC6).
        """
        if self._stop.is_set():
            # shutdown idempotent.
            return
        self._stop.set()

        # Snapshot threads + marquer CANCELLED les taches encore actives.
        with self._lock:
            threads = list(self._threads.items())
            cancelled = 0
            for tid, info in self._tasks.items():
                if info.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    info.status = TaskStatus.CANCELLED
                    info.error = "shutdown"
                    cancelled += 1

        logger.info(
            "LocalTaskRunner graceful shutdown initiated (threads=%d, cancelled_marks=%d)",
            len(threads),
            cancelled,
        )

        if not wait:
            return

        # On utilise un budget global de `timeout` secondes plutot que `timeout`
        # par thread (sinon N threads bloquants -> N*timeout d'attente reelle).
        import time

        deadline = time.monotonic() + max(0.0, timeout)
        not_joined: list[str] = []
        for tid, thread in threads:
            if not thread.is_alive():
                continue
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)
            if thread.is_alive():
                not_joined.append(tid)

        if not_joined:
            logger.warning(
                "LocalTaskRunner shutdown timeout: %d thread(s) still alive after %.1fs (task_ids=%s)",
                len(not_joined),
                timeout,
                ", ".join(t[:8] for t in not_joined),
            )


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
