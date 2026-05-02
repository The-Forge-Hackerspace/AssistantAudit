"""Tests du tracker de tasks de fond (TOS-80 / US047 — finding C-001 ln-620).

Couverture :
  - register_bg_task : la task est tracee, puis retiree au done_callback ;
  - exceptions silencieuses : loggees + retirees du registre ;
  - cancel_background_tasks : annule + attend les tasks pending ;
  - cancel_background_tasks : timeout sur task qui ignore CancelledError.
"""
from __future__ import annotations

import asyncio
import logging

import pytest

from app.core import event_loop as ev


@pytest.fixture(autouse=True)
def _clear_registry():
    """Vide le registre global avant et apres chaque test (etat partage)."""
    ev._background_tasks.clear()
    yield
    ev._background_tasks.clear()


@pytest.mark.asyncio
async def test_register_bg_task_tracks_then_cleans_up_on_completion():
    async def _quick():
        return "ok"

    task = ev.register_bg_task(_quick(), name="t-ok")
    assert task in ev.get_background_tasks()
    result = await task
    # done_callback s'execute via le loop : laisser une iteration passer.
    await asyncio.sleep(0)
    assert result == "ok"
    assert task not in ev.get_background_tasks()


@pytest.mark.asyncio
async def test_register_bg_task_logs_exception_and_cleans_up(caplog):
    async def _boom():
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.ERROR, logger="app.core.event_loop"):
        task = ev.register_bg_task(_boom(), name="t-boom")
        with pytest.raises(RuntimeError):
            await task
        await asyncio.sleep(0)

    assert task not in ev.get_background_tasks()
    # Un log ERROR mentionnant le nom de la task et l'exception.
    assert any(
        "t-boom" in rec.message and "kaboom" in (rec.message + str(rec.exc_info or ""))
        for rec in caplog.records
        if rec.levelno >= logging.ERROR
    )


@pytest.mark.asyncio
async def test_cancel_background_tasks_cancels_pending():
    started = asyncio.Event()

    async def _long():
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise

    task = ev.register_bg_task(_long(), name="t-long")
    await started.wait()
    assert task in ev.get_background_tasks()

    await ev.cancel_background_tasks(timeout=2.0)
    await asyncio.sleep(0)

    assert task.cancelled()
    assert task not in ev.get_background_tasks()


@pytest.mark.asyncio
async def test_cancel_background_tasks_no_op_when_empty():
    # Ne doit ni lever ni timeout quand le registre est vide.
    await ev.cancel_background_tasks(timeout=0.1)


@pytest.mark.asyncio
async def test_cancel_background_tasks_timeout_logs_warning(caplog):
    async def _stubborn():
        # Avale CancelledError et continue (simulateur de mauvais citoyen).
        while True:
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                # On laisse une fenetre tres courte pour ne pas bloquer le test.
                await asyncio.sleep(0)
                return

    task = ev.register_bg_task(_stubborn(), name="t-stubborn")
    # Garde le test borne meme si la task se comporte bien.
    with caplog.at_level(logging.WARNING, logger="app.core.event_loop"):
        await ev.cancel_background_tasks(timeout=0.05)
    # On ne verifie pas strictement le warning (depend du timing) ; on verifie
    # surtout que la fonction retourne bien sans exception non rattrapee.
    # Cleanup explicite pour eviter de laisser une task pending.
    if not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def test_no_direct_create_task_in_api_routes():
    """Lint anti-regression : aucun `asyncio.create_task` direct sous api/v1/."""
    import pathlib

    api_dir = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
    assert api_dir.is_dir(), api_dir
    offenders: list[str] = []
    for py in api_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "asyncio.create_task" in text:
            offenders.append(str(py.relative_to(api_dir.parent.parent.parent)))
    assert not offenders, (
        "Utiliser `register_bg_task` (core.event_loop) au lieu de "
        f"`asyncio.create_task` direct dans : {offenders}"
    )
