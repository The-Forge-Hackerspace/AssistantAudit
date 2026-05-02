"""Tests d'integration pour le shutdown gracieux (TOS-79 / US046).

Couverture :
  - LocalTaskRunner.shutdown() pose _stop, join les threads, marque les
    taches encore actives comme CANCELLED.
  - LocalTaskRunner.shutdown() logge un warning si timeout depasse sans
    tous les threads joints (AC6).
  - LocalTaskRunner.submit() refuse les nouvelles taches apres shutdown.
  - ConnectionManager.shutdown() ferme toutes les WS avec code 1001 +
    vide les dicts (AC3).
  - ConnectionManager.shutdown() est resilient aux WS qui throw au close
    (return_exceptions=True).
"""
from __future__ import annotations

import logging
import threading
import time
from unittest.mock import AsyncMock

import pytest

from app.core.task_runner import LocalTaskRunner, TaskStatus
from app.core.websocket_manager import ConnectionManager


# ── LocalTaskRunner.shutdown ────────────────────────────────────────────


def test_local_runner_shutdown_signals_workers_and_joins_threads():
    """AC1 + AC2 : _stop is set, worker checking is_stopping() exits, thread joined."""
    runner = LocalTaskRunner()
    started = threading.Event()

    def long_worker():
        started.set()
        # Boucle qui sort si _stop est pose (pattern attendu dans execute_pipeline_background).
        while not runner.is_stopping():
            time.sleep(0.01)

    runner.submit(long_worker)
    assert started.wait(timeout=2.0), "worker n'a pas demarre"

    runner.shutdown(wait=True, timeout=2.0)

    assert runner.is_stopping() is True
    # Thread joint -> plus aucun thread vivant dans le snapshot.
    for _, thread in runner._threads.items():
        assert not thread.is_alive(), "thread non joint apres shutdown"


def test_local_runner_shutdown_marks_pending_tasks_cancelled():
    """AC5 partiel : taches encore PENDING/RUNNING -> CANCELLED, raison 'shutdown'."""
    runner = LocalTaskRunner()
    started = threading.Event()
    proceed = threading.Event()

    def waiter():
        started.set()
        # Bloque jusqu'au shutdown ou proceed.
        while not runner.is_stopping() and not proceed.is_set():
            time.sleep(0.01)

    task_id = runner.submit(waiter)
    assert started.wait(timeout=2.0)

    runner.shutdown(wait=True, timeout=2.0)

    info = runner._tasks[task_id]
    assert info.status == TaskStatus.CANCELLED
    assert info.error == "shutdown"


def test_local_runner_shutdown_warns_on_timeout(caplog):
    """AC6 : warning loggé si un thread refuse de sortir avant le timeout."""
    runner = LocalTaskRunner()
    started = threading.Event()

    def stubborn():
        started.set()
        # Ne checke pas is_stopping() volontairement -> ignore le shutdown.
        time.sleep(2.0)

    runner.submit(stubborn)
    assert started.wait(timeout=2.0)

    with caplog.at_level(logging.WARNING, logger="app.core.task_runner"):
        runner.shutdown(wait=True, timeout=0.2)

    assert any(
        "shutdown timeout" in rec.message and "still alive" in rec.message
        for rec in caplog.records
        if rec.levelno >= logging.WARNING
    ), "warning AC6 manquant"

    # Cleanup : laisser le thread finir pour ne pas polluer pytest.
    time.sleep(2.5)


def test_local_runner_submit_after_shutdown_is_refused():
    """Plus de nouvelles taches apres shutdown."""
    runner = LocalTaskRunner()
    runner.shutdown(wait=False)

    with pytest.raises(RuntimeError, match="shutting down"):
        runner.submit(lambda: None)


def test_local_runner_shutdown_idempotent():
    """Double shutdown : pas d'exception, _stop reste set."""
    runner = LocalTaskRunner()
    runner.shutdown(wait=False)
    # Deuxieme appel : no-op.
    runner.shutdown(wait=True, timeout=0.1)
    assert runner.is_stopping() is True


# ── ConnectionManager.shutdown ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_manager_shutdown_closes_users_and_agents_with_1001():
    """AC3 : ws.close(code=1001, reason=...) appele pour chaque user + agent."""
    manager = ConnectionManager()

    user_ws = AsyncMock()
    agent_ws = AsyncMock()
    manager.user_connections[1] = user_ws
    manager.agent_connections["agent-uuid-1"] = agent_ws
    manager.agent_owners["agent-uuid-1"] = 1

    drained = await manager.shutdown()

    assert drained == 2
    user_ws.close.assert_awaited_once_with(code=1001, reason="Server shutting down")
    agent_ws.close.assert_awaited_once_with(code=1001, reason="Server shutting down")
    assert manager.user_connections == {}
    assert manager.agent_connections == {}
    assert manager.agent_owners == {}


@pytest.mark.asyncio
async def test_ws_manager_shutdown_resilient_to_close_errors():
    """AC3 : si une WS throw au close, les autres sont quand meme fermees."""
    manager = ConnectionManager()

    failing_ws = AsyncMock()
    failing_ws.close.side_effect = RuntimeError("connection deja morte")
    healthy_ws = AsyncMock()

    manager.user_connections[1] = failing_ws
    manager.user_connections[2] = healthy_ws

    # Ne doit pas lever : asyncio.gather(return_exceptions=True).
    drained = await manager.shutdown()

    assert drained == 2
    failing_ws.close.assert_awaited_once()
    healthy_ws.close.assert_awaited_once()
    assert manager.user_connections == {}


@pytest.mark.asyncio
async def test_ws_manager_shutdown_empty_is_noop(caplog):
    """Shutdown sans connexion : log info '0 WS clients drained'."""
    manager = ConnectionManager()

    with caplog.at_level(logging.INFO, logger="app.core.websocket_manager"):
        drained = await manager.shutdown()

    assert drained == 0
    assert any(
        "0 WS clients drained" in rec.message
        for rec in caplog.records
        if rec.levelno >= logging.INFO
    )
