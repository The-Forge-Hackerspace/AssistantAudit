"""
Reference au loop asyncio principal de l'application + tracker des tasks
de fond.

Le loop est capture pendant `lifespan` au demarrage et expose ici pour que
le code synchrone (services tournant dans le threadpool de FastAPI) puisse
y planifier des coroutines via `asyncio.run_coroutine_threadsafe`.

Ne jamais appeler `asyncio.run()` depuis du code sync : cela cree un
nouveau loop, ce qui casse les ressources liees au loop principal
(WebSockets, connexions DB asynchrones, taches en cours, etc.).

Le `BackgroundTaskRegistry` (TOS-80 / US047 — finding C-001 ln-620) tracke
toutes les tasks lancees depuis les routes HTTP afin :
  - d'eviter les warnings `Task exception was never retrieved` ;
  - de pouvoir annuler proprement les scans en cours au shutdown.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)

_app_loop: asyncio.AbstractEventLoop | None = None
_background_tasks: set[asyncio.Task[Any]] = set()


def set_app_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Stocke la reference au loop principal (a appeler depuis lifespan)."""
    global _app_loop
    _app_loop = loop


def get_app_loop() -> asyncio.AbstractEventLoop | None:
    """Retourne le loop principal, ou None s'il n'a pas encore ete capture."""
    return _app_loop


def _on_task_done(task: asyncio.Task[Any]) -> None:
    """Callback nettoyant le registre et loggant les exceptions silencieuses."""
    _background_tasks.discard(task)
    if task.cancelled():
        logger.debug("Task de fond %r annulee", task.get_name())
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "Task de fond %r a leve une exception non rattrapee : %r",
            task.get_name(),
            exc,
            exc_info=exc,
        )


def register_bg_task(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str | None = None,
) -> asyncio.Task[Any]:
    """Cree une `asyncio.Task` tracee dans le registre global.

    Le done_callback :
      - retire la task du registre (eviter la fuite memoire) ;
      - log toute exception non rattrapee (sinon Python emet un warning
        `Task exception was never retrieved` au GC).

    Doit etre appele depuis le loop principal (route HTTP, handler WS, ...).
    Pour planifier depuis du code sync hors-loop, utiliser
    `asyncio.run_coroutine_threadsafe(coro, get_app_loop())`.
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_task_done)
    return task


def get_background_tasks() -> set[asyncio.Task[Any]]:
    """Retourne une copie du registre courant (lecture seule, tests/diag)."""
    return set(_background_tasks)


async def cancel_background_tasks(timeout: float = 5.0) -> None:
    """Annule toutes les tasks de fond et attend leur terminaison.

    Strategie :
      1. Snapshot du registre (les done_callbacks vont muter `_background_tasks`).
      2. `task.cancel()` sur chaque task encore pending.
      3. `gather(*, return_exceptions=True)` avec timeout — toute exception
         (y compris `CancelledError`) est avalee silencieusement, le log
         passe par le done_callback.
    """
    pending = [t for t in _background_tasks if not t.done()]
    if not pending:
        return
    for task in pending:
        task.cancel()
    try:
        await asyncio.wait_for(
            asyncio.gather(*pending, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Shutdown : %d task(s) de fond n'ont pas termine sous %.1fs",
            sum(1 for t in pending if not t.done()),
            timeout,
        )
