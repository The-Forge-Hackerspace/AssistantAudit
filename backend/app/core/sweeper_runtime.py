"""
Helpers communs aux sweepers asyncio (heartbeat, collect, ...).

Les sweepers detectent en base des entites obsoletes (agents timeout, collectes
orphelines), les marquent en echec et notifient les clients via WebSocket. La
detection + l'ecriture en base sont synchrones (SQLAlchemy sync), tandis que
les notifications WS sont async.

Pour ne pas bloquer l'event loop pendant la requete/commit, le travail DB est
delegue a `asyncio.to_thread` ; seules les notifications WS restent sur la
boucle.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from .websocket_manager import ws_manager

logger = logging.getLogger(__name__)


async def run_sweep_iteration(
    sync_iteration: Callable[[], list[tuple[int, dict]]],
    event_type: str,
) -> None:
    """Execute une passe de sweep : DB hors event loop, notifications dessus.

    `sync_iteration` est un callable sync qui ouvre/ferme sa propre session
    SQLAlchemy et retourne la liste des notifications `(owner_id, payload)`
    a envoyer aux clients connectes. En cas d'exception non rattrapee, la
    passe est ignoree (on ne notifie rien) ; les sweepers continuent.
    """
    try:
        notifications = await asyncio.to_thread(sync_iteration)
    except Exception:
        logger.exception("Sweep iteration failed (event=%s)", event_type)
        return

    for owner_id, payload in notifications:
        try:
            await ws_manager.send_to_user(owner_id, event_type, payload)
        except Exception:
            logger.exception("Failed to notify owner %s (event=%s)", owner_id, event_type)
