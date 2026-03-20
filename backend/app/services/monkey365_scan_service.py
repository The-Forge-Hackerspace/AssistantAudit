import logging
import threading
import uuid
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

        auth_mode = config.auth_mode.value if hasattr(config.auth_mode, "value") else str(config.auth_mode)
        config_snapshot = {
            "provider": config.provider,
            "auth_mode": auth_mode,
            "tenant_id": config.tenant_id,
            "client_id": config.client_id,
            "output_dir": str(output_path),
            "rulesets": config.rulesets,
            "plugins": config.plugins,
            "collect": config.collect,
            "include_entra_id": config.include_entra_id,
            "export_to": config.export_to,
            "scan_sites": config.scan_sites,
            "verbose": config.verbose,
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
            auth_mode = config.auth_mode.value if hasattr(config.auth_mode, "value") else str(config.auth_mode)
            executor_config = Monkey365Config(
                provider=config.provider,
                auth_mode=auth_mode,
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=config.client_secret,
                username=config.username,
                password=config.password,
                output_dir=result.output_path or config.output_dir,
                rulesets=config.rulesets,
                plugins=config.plugins,
                collect=config.collect,
                include_entra_id=config.include_entra_id,
                export_to=config.export_to,
                scan_sites=config.scan_sites,
                verbose=config.verbose,
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
                    "provider": config.provider,
                    "auth_mode": auth_mode,
                    "tenant_id": config.tenant_id,
                    "client_id": config.client_id,
                    "output_path": result.output_path,
                    "findings_count": findings_count,
                }
                if result.output_path:
                    _ = write_meta_json(Path(result.output_path), meta)
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
