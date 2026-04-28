"""
Reference au loop asyncio principal de l'application.

Le loop est capture pendant `lifespan` au demarrage et expose ici pour que
le code synchrone (services tournant dans le threadpool de FastAPI) puisse
y planifier des coroutines via `asyncio.run_coroutine_threadsafe`.

Ne jamais appeler `asyncio.run()` depuis du code sync : cela cree un
nouveau loop, ce qui casse les ressources liees au loop principal
(WebSockets, connexions DB asynchrones, taches en cours, etc.).
"""
from __future__ import annotations

import asyncio

_app_loop: asyncio.AbstractEventLoop | None = None


def set_app_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Stocke la reference au loop principal (a appeler depuis lifespan)."""
    global _app_loop
    _app_loop = loop


def get_app_loop() -> asyncio.AbstractEventLoop | None:
    """Retourne le loop principal, ou None s'il n'a pas encore ete capture."""
    return _app_loop
