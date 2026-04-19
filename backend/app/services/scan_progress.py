"""Conversion de la progression nmap multi-phase en pourcentage global monotone.

Hybride :
- pondération par phase (SYN, Service, Scripts, ...) avec interpolation intra-phase
- plancher basé sur le nombre d'hôtes terminés / hôtes totaux
- garde monotone (la progression ne diminue jamais)
"""

import re
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

# Pondération de chaque phase nmap sur la progression globale (start%, end%)
# Les bornes sont volontairement larges pour couvrir les variations entre scans.
PHASE_WEIGHTS: list[tuple[str, int, int]] = [
    ("ARP Ping Scan", 0, 8),
    ("Ping Scan", 0, 10),
    ("Parallel DNS resolution", 10, 15),
    ("SYN Stealth Scan", 15, 60),
    ("Connect Scan", 15, 60),
    ("UDP Scan", 15, 60),
    ("Service scan", 60, 85),
    ("OS detection", 85, 92),
    ("NSE", 92, 98),
    ("Script scan", 92, 98),
]

_INITIATING_RE = re.compile(r"Initiating (.+?)(?:\s+at\s+\d|\s*$)", re.IGNORECASE)
_TIMING_RE = re.compile(r"(\d+(?:\.\d+)?)% done")
_TOTAL_HOSTS_RE = re.compile(r"Scanning (\d+) hosts?")
_HOSTS_DONE_RE = re.compile(r"(\d+) hosts? completed")


@dataclass
class _TaskState:
    phase_start: int = 0
    # Par défaut : aucune phase détectée, le raw_pct de l'agent couvre [0, 100].
    # Scaler sur [0, 15] masquait les scans courts qui n'émettent pas tous les marqueurs.
    phase_end: int = 100
    last_progress: int = 0
    total_hosts: int = 0
    hosts_completed: int = 0
    intra_phase_pct: Optional[float] = field(default=None)


_states: dict[str, _TaskState] = {}
_lock = Lock()


def _match_phase(name: str) -> Optional[tuple[int, int]]:
    name_l = name.lower().strip()
    for phase, start, end in PHASE_WEIGHTS:
        if phase.lower() in name_l:
            return start, end
    return None


def compute_progress(
    task_uuid: str,
    output_lines: Optional[list[str]] = None,
    fallback_pct: Optional[int] = None,
) -> int:
    """Calcule la progression globale en parsant les lignes nmap.

    Retourne un entier monotone dans [0, 100].
    """
    with _lock:
        state = _states.setdefault(task_uuid, _TaskState())

        for line in output_lines or []:
            m_total = _TOTAL_HOSTS_RE.search(line)
            if m_total:
                state.total_hosts = max(state.total_hosts, int(m_total.group(1)))

            m_done = _HOSTS_DONE_RE.search(line)
            if m_done:
                state.hosts_completed = max(state.hosts_completed, int(m_done.group(1)))

            m_init = _INITIATING_RE.search(line)
            if m_init:
                phase = _match_phase(m_init.group(1))
                if phase:
                    state.phase_start, state.phase_end = phase
                    # Pas de reset à 0.0 : on laisse fallback_pct piloter l'intra-phase
                    # tant que nmap n'a pas émis une ligne "Timing".
                    state.intra_phase_pct = None

            m_timing = _TIMING_RE.search(line)
            if m_timing:
                state.intra_phase_pct = float(m_timing.group(1))

        # Candidat 1 : progression pondérée par la phase courante
        if state.intra_phase_pct is not None:
            phase_progress = state.phase_start + (state.phase_end - state.phase_start) * (
                state.intra_phase_pct / 100
            )
        elif fallback_pct is not None:
            # Pas d'info de timing : on borne le pct brut de l'agent par la phase
            phase_progress = state.phase_start + (state.phase_end - state.phase_start) * (
                max(0, min(100, fallback_pct)) / 100
            )
        else:
            phase_progress = state.last_progress

        # Candidat 2 : plancher basé sur les hôtes terminés (si total connu)
        if state.total_hosts > 0:
            host_floor = (state.hosts_completed / state.total_hosts) * 100
        else:
            host_floor = 0

        # Garde monotone : on prend le max des candidats et du dernier point
        new_progress = max(
            state.last_progress,
            int(round(phase_progress)),
            int(round(host_floor)),
        )
        new_progress = max(0, min(100, new_progress))
        state.last_progress = new_progress
        return new_progress


def reset_task(task_uuid: str) -> None:
    """Nettoie l'état d'une tâche (à appeler à la fin de la tâche)."""
    with _lock:
        _states.pop(task_uuid, None)
