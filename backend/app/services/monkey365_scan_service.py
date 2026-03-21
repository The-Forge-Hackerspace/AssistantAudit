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
from ..models.monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus
from ..schemas.scan import Monkey365ConfigSchema
from ..tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor

logger = logging.getLogger(__name__)
settings = get_settings()


class DBSession(Protocol):
    def get(self, entity: object, ident: object) -> object | None: ...
    def add(self, instance: object) -> None: ...
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
            "auth_mode": config.auth_mode,
            "force_msal_desktop": config.force_msal_desktop,
            "powershell_config": config.powershell_config,
        }

        result = Monkey365ScanResult(
            entreprise_id=entreprise_id,
            status=Monkey365ScanStatus.RUNNING,
            scan_id=scan_id,
            config_snapshot=config_snapshot,
            output_path=str(output_path),
            entreprise_slug=entreprise_slug,
            auth_mode=config.auth_mode,
            force_msal_desktop=config.force_msal_desktop or False,
            powershell_config=config.powershell_config,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def move_results_to_archive(scan_id: str, source_path: Path) -> Path:
        """
        Move Monkey365 results from monkey-reports/{GUID}/ to configured archive path.
        Preserves JSON and HTML files, removing duplicate JSON from powershell_raw_output.json
        """
        archive_base = Path(settings.MONKEY365_ARCHIVE_PATH)
        archive_base.mkdir(parents=True, exist_ok=True)
        archive_path = archive_base / scan_id
        
        if archive_path.exists():
            shutil.rmtree(archive_path)
        
        archive_path.mkdir(parents=True, exist_ok=True)
        
        for item in source_path.rglob("*"):
            if item.is_file():
                if item.name == "powershell_raw_output.json":
                    continue
                
                rel_path = item.relative_to(source_path)
                target_file = archive_path / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_file)
                logger.info(f"[MONKEY365] Copied {item.name} to {target_file}")
        
        logger.info(f"[MONKEY365] Results archived to {archive_path}")
        return archive_path

    @staticmethod
    def execute_scan_background(result_id: int, config_data: dict[str, object]) -> None:
        db = cast(DBSession, SessionLocal())
        final_status = Monkey365ScanStatus.FAILED
        final_error: str | None = None
        findings_count: int | None = None

        try:
            result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, result_id))
            if not result:
                logger.error("[MONKEY365] Résultat #%s introuvable en BDD", result_id)
                return

            config = Monkey365ConfigSchema(**config_data)
            executor_config = Monkey365Config(
                output_dir=result.output_path or config.output_dir,
                spo_sites=config.spo_sites,
                export_to=config.export_to,
            )

            executor = Monkey365Executor(executor_config, settings.MONKEY365_PATH or None)
            run_result = executor.run_scan(result.scan_id)

            if run_result.get("status") == "success":
                final_status = Monkey365ScanStatus.SUCCESS
                raw_findings = run_result.get("results", [])
                if isinstance(raw_findings, list):
                    findings_count = len(raw_findings)

                completed_at = datetime.now(timezone.utc)
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
                    
                    archive_path = Monkey365ScanService.move_results_to_archive(
                        result.scan_id, 
                        Path(result.output_path)
                    )
                    result.archive_path = str(archive_path)
                    logger.info(f"[MONKEY365] Scan #{result_id} archived to {archive_path}")
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
        pending = Monkey365ScanService.create_pending_scan(
            db=db,
            entreprise_id=entreprise_id,
            config=config,
        )

        thread = threading.Thread(
            target=Monkey365ScanService.execute_scan_background,
            args=(pending.id, config.model_dump()),
            daemon=True,
            name=f"monkey365-scan-{pending.id}",
        )
        thread.start()
        return pending

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

    @staticmethod
    def delete_scan(db: DBSession, scan_id: int) -> bool:
        """Delete a Monkey365 scan and clean up associated files."""
        result = cast(Monkey365ScanResult | None, db.get(Monkey365ScanResult, scan_id))
        if not result:
            return False

        # Clean up output directory
        if result.output_path:
            try:
                output_path = Path(result.output_path)
                if output_path.exists():
                    shutil.rmtree(output_path)
                    logger.info(f"[MONKEY365] Cleaned up output directory: {result.output_path}")
            except Exception as exc:
                logger.warning(f"[MONKEY365] Could not delete output directory {result.output_path}: {exc}")

        # Clean up archive path
        if result.archive_path:
            try:
                archive_path = Path(result.archive_path)
                if archive_path.exists():
                    shutil.rmtree(archive_path)
                    logger.info(f"[MONKEY365] Cleaned up archive directory: {result.archive_path}")
            except Exception as exc:
                logger.warning(f"[MONKEY365] Could not delete archive directory {result.archive_path}: {exc}")

        # Delete from database
        db.delete(result)
        db.commit()
        logger.info(f"[MONKEY365] Scan #{scan_id} deleted from database")
        return True
