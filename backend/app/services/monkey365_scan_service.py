import asyncio
import json
import logging
import threading
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, cast

from ..core.config import get_settings
from ..core.database import SessionLocal
from ..core.storage import ensure_scan_directory, slugify, write_meta_json
from ..models.entreprise import Entreprise
from ..models.enums import AuthMethod
from ..models.monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus
from ..schemas.scan import Monkey365ConfigSchema
from ..tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor

logger = logging.getLogger(__name__)
settings = get_settings()

_scan_locks: dict[str, threading.Lock] = {}
_lock_registry_lock = threading.Lock()


class DBSession(Protocol):
    def get(self, entity: object, ident: object) -> object | None: ...
    def add(self, instance: object) -> None: ...
    def delete(self, instance: object) -> None: ...
    def commit(self) -> None: ...
    def refresh(self, instance: object) -> None: ...
    def query(self, entity: object) -> "QueryChain": ...
    def close(self) -> None: ...


class QueryChain(Protocol):
    def filter(self, *args: object, **kwargs: object) -> "QueryChain": ...
    def order_by(self, *args: object, **kwargs: object) -> "QueryChain": ...
    def offset(self, offset: int) -> "QueryChain": ...
    def limit(self, limit: int) -> "QueryChain": ...
    def all(self) -> list[object]: ...


class Monkey365ScanService:
    @staticmethod
    def _open_db() -> DBSession:
        """Ouvre une nouvelle session SQLAlchemy pour les threads en arrière-plan.

        Les threads background ne peuvent pas réutiliser la session liée à la
        requête HTTP (fermée dès que la réponse est envoyée). Cette méthode
        centralise la création de session pour éviter d'importer SessionLocal
        directement dans execute_scan_background.
        """
        return cast(DBSession, SessionLocal())

    @staticmethod
    def create_pending_scan(
        db: DBSession,
        entreprise_id: int,
        config: Monkey365ConfigSchema,
    ) -> Monkey365ScanResult:
        entreprise = cast(Entreprise | None, db.get(Entreprise, entreprise_id))
        if not entreprise:
            raise ValueError(f"Entreprise #{entreprise_id} introuvable")

        scan_id = str(uuid.uuid4())
        entreprise_slug = slugify(entreprise.nom)
        output_path = ensure_scan_directory(entreprise.nom, scan_id, tool="M365")

        config_snapshot = {
            "spo_sites": config.spo_sites,
            "export_to": config.export_to,
            "output_dir": str(output_path),
        }

        result = Monkey365ScanResult(
            entreprise_id=entreprise_id,
            status=Monkey365ScanStatus.RUNNING,
            scan_id=scan_id,
            config_snapshot=config_snapshot,
            output_path=str(output_path),
            entreprise_slug=entreprise_slug,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def _snapshot_report_dirs(monkey365_base: Path) -> set[str]:
        """Return names of existing subdirs in monkey-reports/ before a scan."""
        reports_dir = monkey365_base / "monkey-reports"
        if not reports_dir.exists():
            return set()
        return {d.name for d in reports_dir.iterdir() if d.is_dir()}

    @staticmethod
    def _find_new_report_dir(
        monkey365_base: Path, before_snapshot: set[str]
    ) -> Path | None:
        """Find the new directory Monkey365 created during the scan."""
        reports_dir = monkey365_base / "monkey-reports"
        if not reports_dir.exists():
            return None
        for d in reports_dir.iterdir():
            if d.is_dir() and d.name not in before_snapshot:
                return d
        return None

    @staticmethod
    def move_results_to_output(source_path: Path, dest_path: Path) -> None:
        """
        Move Monkey365 report files from source_path into dest_path.

        source_path: the monkey-reports/{MONKEY_GUID}/ directory Monkey365 created.
        dest_path:   the scan output_path (data/{slug}/Cloud/M365/{scan_id}/).

        Files are merged into dest_path preserving sub-directory structure.
        powershell_raw_output.json is skipped (large, not useful).
        Source directory is removed after move.
        """
        dest_path.mkdir(parents=True, exist_ok=True)

        if source_path.exists():
            for item in source_path.rglob("*"):
                if item.is_file():
                    if item.name == "powershell_raw_output.json":
                        continue

                    rel_path = item.relative_to(source_path)
                    target_file = dest_path / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(target_file))
                    logger.info("[MONKEY365] Moved %s → %s", item.name, target_file)

            try:
                shutil.rmtree(source_path)
                logger.info("[MONKEY365] Cleaned up source: %s", source_path)
            except OSError as exc:
                logger.warning("[MONKEY365] Could not remove source: %s — %s", source_path, exc)
        else:
            logger.warning("[MONKEY365] Source not found: %s", source_path)

        logger.info("[MONKEY365] Results moved to %s", dest_path)

    @staticmethod
    def _get_scan_lock(monkey365_base: Path) -> threading.Lock:
        """Return (or create) the per-instance lock for monkey365_base."""
        key = str(monkey365_base)
        with _lock_registry_lock:
            if key not in _scan_locks:
                _scan_locks[key] = threading.Lock()
            return _scan_locks[key]

    @staticmethod
    def _count_json_findings(output_path: Path) -> int:
        """Count findings from JSON files after results have been moved to output_path."""
        INTERNAL_FILES = frozenset({"scan_params.json", "meta.json", "powershell_raw_output.json"})
        total = 0
        for json_file in output_path.rglob("*.json"):
            if json_file.name in INTERNAL_FILES:
                continue
            try:
                data = json.loads(json_file.read_text(encoding="utf-8", errors="replace"))
                if isinstance(data, list):
                    total += len(data)
            except Exception:
                pass
        return total

    @staticmethod
    def execute_scan_background(result_id: int, config_data: dict[str, object]) -> None:
        db = Monkey365ScanService._open_db()
        final_status = Monkey365ScanStatus.FAILED
        final_error: str | None = None
        findings_count: int | None = None
        duration_seconds: int = 0

        try:
            result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
            if not result:
                logger.error("[MONKEY365] Résultat #%s introuvable en BDD", result_id)
                return

            config = Monkey365ConfigSchema(**config_data)
            executor_config = Monkey365Config(
                output_dir=result.output_path or "./monkey365_output",
                spo_sites=config.spo_sites,
                export_to=config.export_to,
                device_code=config.device_code,
            )

            executor = Monkey365Executor(executor_config, settings.MONKEY365_PATH or None, allow_auto_clone=settings.MONKEY365_AUTO_CLONE)

            # Derive base dir from the executor's resolved path so it stays in sync
            # even when MONKEY365_PATH is unset and the executor falls back to DEFAULT_MONKEY365_DIR.
            monkey365_base = executor.monkey365_base_dir
            with Monkey365ScanService._get_scan_lock(monkey365_base):
                dirs_before = Monkey365ScanService._snapshot_report_dirs(monkey365_base)
                run_result = executor.run_scan(result.scan_id)
                new_report_dir = Monkey365ScanService._find_new_report_dir(
                    monkey365_base, dirs_before
                )

            if run_result.get("status") == "success":
                final_status = Monkey365ScanStatus.SUCCESS
                completed_at = datetime.now(timezone.utc)

                if new_report_dir:
                    dest = Path(result.output_path) if result.output_path else None
                    if dest:
                        Monkey365ScanService.move_results_to_output(new_report_dir, dest)
                        findings_count = Monkey365ScanService._count_json_findings(dest)
                        logger.info("[MONKEY365] Scan #%s results moved to %s", result_id, dest)
                    else:
                        logger.warning("[MONKEY365] Scan #%s: output_path non défini, résultats non déplacés", result_id)
                else:
                    logger.warning(
                        "[MONKEY365] Scan #%s succeeded but no new report dir found in %s/monkey-reports/",
                        result_id, monkey365_base,
                    )

                meta = {
                    "scan_id": result.scan_id,
                    "entreprise_id": result.entreprise_id,
                    "entreprise_slug": result.entreprise_slug,
                    "status": Monkey365ScanStatus.SUCCESS.value,
                    "created_at": result.created_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "output_path": result.output_path,
                    "findings_count": findings_count,
                }
                if result.output_path:
                    write_meta_json(Path(result.output_path), meta)
            else:
                error = run_result.get("error", "Erreur inconnue")
                final_error = str(error)[:500]

        except Exception as exc:
            logger.exception("[MONKEY365] Erreur fatale scan #%s", result_id)
            final_status = Monkey365ScanStatus.FAILED
            final_error = str(exc)[:500]
        finally:
            try:
                result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
                if result:
                    if result.status == Monkey365ScanStatus.CANCELLED:
                        logger.info(
                            "[MONKEY365] Scan #%s annulé par l'utilisateur — finalisation ignorée",
                            result_id,
                        )
                        return
                    completed_at = datetime.now(timezone.utc)
                    result.status = final_status
                    result.completed_at = completed_at

                    created_at = result.created_at
                    if created_at is None:
                        created_at = completed_at
                    elif created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    else:
                        created_at = created_at.astimezone(timezone.utc)

                    duration_seconds = int((completed_at - created_at).total_seconds())
                    result.duration_seconds = max(duration_seconds, 0)

                    if findings_count is not None:
                        result.findings_count = findings_count

                    if final_status == Monkey365ScanStatus.FAILED:
                        result.error_message = final_error or "Échec du scan Monkey365"
                    else:
                        result.error_message = None

                    db.commit()
                    logger.info(
                        "[MONKEY365] Scan #%s finalized: %s (duration: %ss)",
                        result_id,
                        final_status.value,
                        duration_seconds,
                    )
            except Exception:
                logger.exception("[MONKEY365] Impossible de finaliser le scan #%s", result_id)
            finally:
                db.close()

    @staticmethod
    def launch_scan(
        db: DBSession,
        entreprise_id: int,
        config: Monkey365ConfigSchema,
    ) -> Monkey365ScanResult:
        return Monkey365ScanService.create_pending_scan(
            db=db,
            entreprise_id=entreprise_id,
            config=config,
        )

    @staticmethod
    def list_scans(
        db: DBSession,
        entreprise_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Monkey365ScanResult]:
        return cast(
            list[Monkey365ScanResult],
            db.query(Monkey365ScanResult)
            .filter(Monkey365ScanResult.entreprise_id == entreprise_id)
            .order_by(Monkey365ScanResult.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_scan(db: DBSession, scan_id: int) -> Monkey365ScanResult | None:
        return cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, scan_id))

    # ── Streaming scan (Device Code Flow) ─────────────────────────

    @staticmethod
    def create_streaming_scan(
        db: DBSession,
        entreprise_id: int,
        tenant_id: str,
        auth_method: str,
        config: Monkey365ConfigSchema,
    ) -> Monkey365ScanResult:
        """Cree un scan en mode streaming avec status AUTHENTICATING."""
        entreprise = cast(Entreprise | None, db.get(Entreprise, entreprise_id))
        if not entreprise:
            raise ValueError(f"Entreprise #{entreprise_id} introuvable")

        scan_id = str(uuid.uuid4())
        entreprise_slug = slugify(entreprise.nom)
        output_path = ensure_scan_directory(entreprise.nom, scan_id, tool="M365")

        config_snapshot = {
            "tenant_id": tenant_id,
            "auth_method": auth_method,
            "spo_sites": config.spo_sites,
            "export_to": config.export_to,
            "output_dir": str(output_path),
        }

        result = Monkey365ScanResult(
            entreprise_id=entreprise_id,
            status=Monkey365ScanStatus.AUTHENTICATING,
            scan_id=scan_id,
            auth_method=auth_method,
            config_snapshot=config_snapshot,
            output_path=str(output_path),
            entreprise_slug=entreprise_slug,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    async def execute_streaming_scan(
        result_id: int,
        user_id: int,
        tenant_id: str,
        subscriptions: list[str],
        ruleset: str,
        auth_method_str: str,
    ) -> None:
        """
        Tache async en background : lance le scan streaming et streame via WebSocket.
        """
        from ..core.websocket_manager import ws_manager
        from .monkey365_streaming_executor import Monkey365StreamingExecutor

        db = Monkey365ScanService._open_db()
        try:
            result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
            if not result:
                logger.error("[MONKEY365-STREAM] Scan #%s introuvable", result_id)
                return

            auth_method = AuthMethod(auth_method_str)

            async def ws_callback(event_type: str, data: dict) -> None:
                await ws_manager.send_to_user(user_id, event_type, data)

            executor = Monkey365StreamingExecutor(
                scan_id=result_id,
                ws_callback=ws_callback,
            )

            # Passer en RUNNING des que l'auth est faite (device code envoye)
            result.status = Monkey365ScanStatus.RUNNING
            db.commit()

            run_result = await executor.run_scan_streaming(
                tenant_id=tenant_id,
                subscriptions=subscriptions,
                ruleset=ruleset,
                auth_method=auth_method,
            )

            if run_result.get("status") == "success":
                result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
                if result and result.status != Monkey365ScanStatus.CANCELLED:
                    result.status = Monkey365ScanStatus.SUCCESS
                    result.completed_at = datetime.now(timezone.utc)
                    if result.created_at:
                        created = result.created_at
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                        result.duration_seconds = max(
                            0, int((result.completed_at - created).total_seconds())
                        )
                    db.commit()
            else:
                result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
                if result and result.status != Monkey365ScanStatus.CANCELLED:
                    result.status = Monkey365ScanStatus.FAILED
                    result.error_message = str(run_result.get("error", ""))[:500]
                    result.completed_at = datetime.now(timezone.utc)
                    db.commit()

        except Exception as exc:
            logger.exception("[MONKEY365-STREAM] Erreur fatale scan #%s", result_id)
            try:
                result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
                if result and result.status != Monkey365ScanStatus.CANCELLED:
                    result.status = Monkey365ScanStatus.FAILED
                    result.error_message = str(exc)[:500]
                    result.completed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                logger.exception("[MONKEY365-STREAM] Impossible de finaliser #%s", result_id)
        finally:
            db.close()

    @staticmethod
    def delete_scan(db: DBSession, scan_id: int) -> bool:
        """Delete a Monkey365 scan and clean up associated files."""
        result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, scan_id))
        if not result:
            return False

        # Clean up output directory (contains logs, meta and reports)
        if result.output_path:
            try:
                output_path = Path(result.output_path)
                if output_path.exists():
                    shutil.rmtree(output_path)
                    logger.info("[MONKEY365] Cleaned up output directory: %s", result.output_path)
            except OSError as exc:
                logger.warning("[MONKEY365] Could not delete output directory %s: %s", result.output_path, exc)

        # Delete from database
        db.delete(result)
        db.commit()
        logger.info("[MONKEY365] Scan #%s deleted from database", scan_id)
        return True
