"""Tests TOS-81 — cycle de vie session-par-phase dans pipeline_service.

Vérifie que `execute_pipeline_background` n'utilise PLUS une session DB unique
sur toute la durée du pipeline mais ouvre / ferme `get_db_session()` plusieurs
fois (au minimum une fois par phase + une fois par itération de polling).
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock


from app.services import pipeline_service


class _SessionCounter:
    """Compteur d'ouvertures/fermetures de get_db_session pour assertions."""

    def __init__(self, real_session_factory):
        self._real = real_session_factory
        self.open_count = 0
        self.close_count = 0

    @contextmanager
    def __call__(self):
        self.open_count += 1
        with self._real() as db:
            try:
                yield db
            finally:
                self.close_count += 1


def test_poll_agent_task_uses_short_session_per_iteration(monkeypatch):
    """`_poll_agent_task` ouvre une session courte à chaque itération de polling
    et ne tient PAS une session sur toute la durée d'attente.
    """
    # On simule 3 polls : les 2 premiers retournent un task non-terminal,
    # le 3ème retourne un task `completed`.
    fake_task_running = MagicMock()
    fake_task_running.status = "running"
    fake_task_done = MagicMock()
    fake_task_done.status = "completed"

    sessions_opened: list[MagicMock] = []
    fake_results = [fake_task_running, fake_task_running, fake_task_done]

    @contextmanager
    def fake_session():
        db = MagicMock()
        sessions_opened.append(db)
        # Chaque session retourne le résultat correspondant à son ordre d'ouverture
        idx = len(sessions_opened) - 1
        db.get.return_value = fake_results[idx] if idx < len(fake_results) else None
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(pipeline_service, "get_db_session", fake_session)
    # Speed up : pas de sleep réel
    monkeypatch.setattr(pipeline_service.time, "sleep", lambda _s: None)

    result = pipeline_service._poll_agent_task(task_id=42, timeout_sec=60, poll_interval_sec=0)

    assert result is fake_task_done
    # Au moins 3 sessions courtes ouvertes (une par itération)
    assert len(sessions_opened) >= 3
    # Chaque session a bien été utilisée pour un .get(AgentTask, 42)
    for db in sessions_opened:
        db.get.assert_called()


def test_poll_agent_task_returns_none_when_task_missing(monkeypatch):
    """Si le polling ne trouve PAS la task, `_poll_agent_task` retourne None
    sans avoir tenu une session pendant le timeout.
    """

    @contextmanager
    def fake_session():
        db = MagicMock()
        db.get.return_value = None
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(pipeline_service, "get_db_session", fake_session)
    monkeypatch.setattr(pipeline_service.time, "sleep", lambda _s: None)

    result = pipeline_service._poll_agent_task(task_id=99, timeout_sec=1, poll_interval_sec=0)
    assert result is None


def test_execute_pipeline_background_opens_multiple_short_sessions(monkeypatch):
    """`execute_pipeline_background` ouvre PLUSIEURS sessions courtes
    (au minimum 1 session pour init + 1 par phase + 1 finalize), et NON une
    seule session globale tenue pendant toute la durée.
    """
    counter = _SessionCounter(pipeline_service.get_db_session)

    # Mock get_db_session pour compter les ouvertures et déléguer à un faux
    @contextmanager
    def counting_session():
        counter.open_count += 1
        db = MagicMock()
        # `pipeline = db.get(CollectPipeline, ...)` renvoie un faux pipeline
        fake_pipeline = MagicMock()
        fake_pipeline.id = 1
        fake_pipeline.created_by = 7
        fake_pipeline.agent_id = None  # → agent introuvable, donc collects_phase saute
        fake_pipeline.collects_status = pipeline_service.PipelineStepStatus.SKIPPED
        fake_pipeline.collects_total = 0
        fake_pipeline.collects_failed = 0
        fake_pipeline.collects_done = 0
        fake_pipeline.hosts_discovered = 0
        fake_pipeline.equipments_created = 0
        fake_pipeline.hosts_skipped = 0
        fake_pipeline.error_message = None
        fake_pipeline.status = pipeline_service.PipelineStatus.PENDING
        fake_pipeline.scan_status = pipeline_service.PipelineStepStatus.PENDING
        fake_pipeline.equipments_status = pipeline_service.PipelineStepStatus.PENDING
        db.get.return_value = fake_pipeline
        try:
            yield db
        finally:
            counter.close_count += 1

    monkeypatch.setattr(pipeline_service, "get_db_session", counting_session)

    # Mock `_run_scan_phase` pour qu'il échoue rapidement (renvoie None) — pas
    # besoin de simuler le polling complet ; on veut juste prouver que la
    # fonction principale ouvre/ferme des sessions séparées.
    monkeypatch.setattr(pipeline_service, "_run_scan_phase", lambda pid, uid: None)
    # Et `_notify` pour ne pas faire de WS
    monkeypatch.setattr(pipeline_service, "_notify", lambda *a, **k: None)

    pipeline_service.execute_pipeline_background(
        pipeline_id=1,
        current_user_id=7,
        username="admin",
    )

    # Au minimum : init session + post-scan progress session + failure-finalize session
    assert counter.open_count >= 3, (
        f"Attendu >= 3 sessions courtes, observé {counter.open_count}"
    )
    # Toute session ouverte doit être fermée (pas de leak)
    assert counter.open_count == counter.close_count


def test_run_equipments_phase_uses_own_short_session(monkeypatch):
    """`_run_equipments_phase` ouvre/ferme sa propre session courte."""
    counter = {"open": 0, "close": 0}

    @contextmanager
    def fake_session():
        counter["open"] += 1
        db = MagicMock()
        fake_pipeline = MagicMock()
        fake_pipeline.site_id = 1
        fake_pipeline.hosts_skipped = 0
        fake_pipeline.equipments_created = 0
        db.get.return_value = fake_pipeline
        # Pas d'hôtes valides → boucle vide
        try:
            yield db
        finally:
            counter["close"] += 1

    monkeypatch.setattr(pipeline_service, "get_db_session", fake_session)
    monkeypatch.setattr(pipeline_service, "detect_collect_profile", lambda h: None)

    result = pipeline_service._run_equipments_phase(pipeline_id=1, hosts=[])
    assert result == []
    assert counter["open"] == 1
    assert counter["close"] == 1
