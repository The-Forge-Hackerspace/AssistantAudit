"""
WebSocket endpoint pour le terminal interactif PingCastle.

Permet de lancer PingCastle.exe en mode interactif (menu principal)
et de streamer stdout/stderr vers le client WebSocket en temps réel,
tout en transmettant les saisies clavier du client vers stdin.

Authentification via query parameter ?token=<JWT>.
"""
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ...core.config import get_settings
from ...core.security import decode_token
from ...core.database import SessionLocal
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> User | None:
    """
    Authentifie un utilisateur via :
      1. Cookie httpOnly « aa_access_token » (prioritaire — SEC-03)
      2. Query parameter ?token=<JWT> (fallback — legacy / API clients)
    """
    effective_token = websocket.cookies.get("aa_access_token") or token
    if not effective_token:
        return None

    payload = decode_token(effective_token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    db = SessionLocal()
    try:
        user = db.get(User, int(user_id))
        if user and user.is_active:
            return user
        return None
    finally:
        db.close()


@router.websocket("/pingcastle/terminal")
async def pingcastle_terminal(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    """
    Terminal interactif PingCastle via WebSocket.

    - Authentification via ?token=<JWT> (rôle admin ou auditeur requis).
    - Lance PingCastle.exe en mode interactif (sans arguments healthcheck).
    - Streame stdout/stderr → WebSocket (texte).
    - Transmet les saisies WebSocket → stdin du process.
    """
    # ── Authentification ──
    user = await _authenticate_ws(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Non authentifié")
        return

    if user.role not in ("admin", "auditeur"):
        await websocket.close(code=4003, reason="Rôle insuffisant")
        return

    await websocket.accept()
    logger.info(f"[PINGCASTLE_WS] Terminal ouvert par {user.username} (id={user.id})")

    settings = get_settings()
    pingcastle_path = settings.PINGCASTLE_PATH

    # ── Vérification de PingCastle ──
    if not pingcastle_path:
        await websocket.send_text(
            "\r\n❌ ERREUR : PINGCASTLE_PATH non configuré.\r\n"
            "Définissez le chemin vers PingCastle.exe dans la configuration (.env).\r\n"
        )
        await websocket.close()
        return

    exe_path = Path(pingcastle_path)
    if not exe_path.exists():
        await websocket.send_text(
            f"\r\n❌ ERREUR : PingCastle.exe introuvable : {pingcastle_path}\r\n"
        )
        await websocket.close()
        return

    # ── Lancement du process PingCastle ──
    process = None
    try:
        await websocket.send_text(
            f"\r\n🏰 Démarrage de PingCastle...\r\n"
            f"   Exécutable : {pingcastle_path}\r\n"
            f"   Utilisateur : {user.username}\r\n\r\n"
        )

        process = await asyncio.create_subprocess_exec(
            str(exe_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(exe_path.parent),
        )

        # ── Tâches concurrentes : stdout→ws et ws→stdin ──
        async def read_stdout():
            """Lit stdout du process et envoie vers le WebSocket."""
            assert process.stdout is not None
            try:
                while True:
                    data = await process.stdout.read(4096)
                    if not data:
                        break
                    try:
                        text = data.decode("utf-8", errors="replace")
                    except Exception:
                        text = data.decode("latin-1", errors="replace")
                    # Convertir LF en CR+LF pour le terminal xterm.js
                    text = text.replace("\n", "\r\n")
                    await websocket.send_text(text)
            except (WebSocketDisconnect, ConnectionError):
                pass
            except Exception as e:
                logger.debug(f"[PINGCASTLE_WS] stdout reader error: {e}")

        async def read_stderr():
            """Lit stderr du process et envoie vers le WebSocket."""
            assert process.stderr is not None
            try:
                while True:
                    data = await process.stderr.read(4096)
                    if not data:
                        break
                    try:
                        text = data.decode("utf-8", errors="replace")
                    except Exception:
                        text = data.decode("latin-1", errors="replace")
                    text = text.replace("\n", "\r\n")
                    await websocket.send_text(text)
            except (WebSocketDisconnect, ConnectionError):
                pass
            except Exception as e:
                logger.debug(f"[PINGCASTLE_WS] stderr reader error: {e}")

        async def write_stdin():
            """Lit les messages du WebSocket et écrit dans stdin du process."""
            assert process.stdin is not None
            try:
                while True:
                    data = await websocket.receive_text()
                    # Envoyer tel quel au process - pas de conversion de line endings
                    # Le process Windows gère nativement CRLF et LF
                    process.stdin.write(data.encode("utf-8"))
                    await process.stdin.drain()
            except (WebSocketDisconnect, ConnectionError):
                pass
            except Exception as e:
                logger.debug(f"[PINGCASTLE_WS] stdin writer error: {e}")

        # Lancer les 3 tâches en parallèle, attendre la fin de la première
        tasks = [
            asyncio.create_task(read_stdout(), name="stdout"),
            asyncio.create_task(read_stderr(), name="stderr"),
            asyncio.create_task(write_stdin(), name="stdin"),
        ]

        # Attendre que le process se termine OU que le WebSocket se ferme
        done, pending = await asyncio.wait(
            [*tasks, asyncio.create_task(process.wait(), name="process")],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Annuler les tâches restantes
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        # ── Message de fin ──
        exit_code = process.returncode
        try:
            await websocket.send_text(
                f"\r\n\r\n{'─' * 50}\r\n"
                f"🏰 PingCastle terminé (code de sortie : {exit_code})\r\n"
                f"{'─' * 50}\r\n"
            )
        except Exception:
            pass

    except WebSocketDisconnect:
        logger.info(f"[PINGCASTLE_WS] Client déconnecté ({user.username})")
    except Exception as e:
        logger.exception(f"[PINGCASTLE_WS] Erreur inattendue")
        try:
            await websocket.send_text(f"\r\n❌ Erreur : {str(e)}\r\n")
        except Exception:
            pass
    finally:
        # Nettoyer le process si encore en cours
        if process and process.returncode is None:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(f"[PINGCASTLE_WS] Terminal fermé ({user.username})")
