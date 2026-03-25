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
    def move_results_to_archive(
        scan_id: str, source_path: Path
    ) -> Path:
        """
        Move Monkey365 report from source_path to the configured archive directory.

        source_path: the actual monkey-reports/{MONKEY_GUID}/ directory.
        Destination: {MONKEY365_ARCHIVE_PATH}/{scan_id}/{FORMAT}/{FILE}

        Skips powershell_raw_output.json.
        """
        archive_base = Path(settings.MONKEY365_ARCHIVE_PATH)
        archive_path = archive_base / scan_id

        if archive_path.exists():
            shutil.rmtree(archive_path)

        archive_path.mkdir(parents=True, exist_ok=True)

        if source_path.exists():
            for item in source_path.rglob("*"):
                if item.is_file():
                    if item.name == "powershell_raw_output.json":
                        continue

                    rel_path = item.relative_to(source_path)
                    target_file = archive_path / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(target_file))
                    logger.info("[MONKEY365] Moved %s → %s", item.name, target_file)

            try:
                shutil.rmtree(source_path)
                logger.info("[MONKEY365] Cleaned up source: %s", source_path)
            except Exception:
                logger.warning("[MONKEY365] Could not remove source: %s", source_path)
        else:
            logger.warning("[MONKEY365] Source not found: %s", source_path)

        logger.info("[MONKEY365] Results archived to %s", archive_path)
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
                output_dir=result.output_path or "./monkey365_output",
                spo_sites=config.spo_sites,
                export_to=config.export_to,
            )

            executor = Monkey365Executor(executor_config, settings.MONKEY365_PATH or None)

            # MONKEY365_PATH may be a .ps1 file — resolve to install dir (where monkey-reports/ lives)
            monkey365_base = Path(settings.MONKEY365_PATH) if settings.MONKEY365_PATH else Path(".")
            if monkey365_base.is_file():
                monkey365_base = monkey365_base.parent
            dirs_before = Monkey365ScanService._snapshot_report_dirs(monkey365_base)

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

                new_report_dir = Monkey365ScanService._find_new_report_dir(
                    monkey365_base, dirs_before
                )
                if new_report_dir:
                    archive_path = Monkey365ScanService.move_results_to_archive(
                        result.scan_id, new_report_dir
                    )
                    result.archive_path = str(archive_path)
                    logger.info("[MONKEY365] Scan #%s archived to %s", result_id, archive_path)
                else:
                    logger.warning(
                        "[MONKEY365] Scan #%s succeeded but no new report dir found in %s/monkey-reports/",
                        result_id, monkey365_base,
                    )
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
