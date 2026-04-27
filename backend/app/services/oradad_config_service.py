"""
Service OradadConfig : CRUD profils de configuration, taches ORADAD, analyse.
"""

import logging

from ..core.errors import BusinessRuleError, NotFoundError
from sqlalchemy.orm import Session

from ..models.agent_task import AgentTask
from ..models.oradad_config import OradadConfig
from .oradad_analysis_service import OradadAnalysisService

logger = logging.getLogger(__name__)


class OradadConfigService:
    # ── Config CRUD ──────────────────────────────────────────────────────

    @staticmethod
    def list_configs(
        db: Session,
        owner_id: int,
        is_admin: bool = False,
    ) -> list[OradadConfig]:
        query = db.query(OradadConfig)
        if not is_admin:
            query = query.filter(OradadConfig.owner_id == owner_id)
        return query.order_by(OradadConfig.created_at.desc()).all()

    @staticmethod
    def get_config(
        db: Session,
        config_id: int,
        owner_id: int,
        is_admin: bool = False,
    ) -> OradadConfig:
        config = db.query(OradadConfig).filter(OradadConfig.id == config_id).first()
        if config is None:
            raise NotFoundError("Profil de configuration introuvable")
        if config.owner_id != owner_id and not is_admin:
            raise NotFoundError("Profil de configuration introuvable")
        return config

    @staticmethod
    def create_config(db: Session, data, owner_id: int) -> OradadConfig:
        config = OradadConfig(
            name=data.name,
            owner_id=owner_id,
            auto_get_domain=data.auto_get_domain,
            auto_get_trusts=data.auto_get_trusts,
            level=data.level,
            confidential=data.confidential,
            process_sysvol=data.process_sysvol,
            sysvol_filter=data.sysvol_filter,
            output_files=data.output_files,
            output_mla=data.output_mla,
            sleep_time=data.sleep_time,
        )
        if data.explicit_domains:
            config.set_domains_list([d.model_dump() for d in data.explicit_domains])
        db.add(config)
        db.flush()
        db.refresh(config)
        return config

    @staticmethod
    def update_config(
        db: Session,
        config_id: int,
        data,
        owner_id: int,
        is_admin: bool = False,
    ) -> OradadConfig:
        config = OradadConfigService.get_config(db, config_id, owner_id, is_admin)
        update_data = data.model_dump(exclude_unset=True)

        if "explicit_domains" in update_data:
            domains_raw = update_data.pop("explicit_domains")
            if domains_raw is not None:
                existing_domains = config.get_domains_list()
                new_domains = [d.model_dump() for d in data.explicit_domains]
                for new_d in new_domains:
                    if new_d.get("password") == "••••••":
                        for old_d in existing_domains:
                            if old_d.get("server") == new_d.get("server") and old_d.get("domain_name") == new_d.get(
                                "domain_name"
                            ):
                                new_d["password"] = old_d.get("password", "")
                                break
                config.set_domains_list(new_domains)
            else:
                config.set_domains_list(None)

        for field, value in update_data.items():
            setattr(config, field, value)

        db.flush()
        db.refresh(config)
        return config

    @staticmethod
    def delete_config(
        db: Session,
        config_id: int,
        owner_id: int,
        is_admin: bool = False,
    ) -> None:
        config = OradadConfigService.get_config(db, config_id, owner_id, is_admin)
        db.delete(config)
        db.flush()

    # ── Taches ORADAD ────────────────────────────────────────────────────

    @staticmethod
    def get_task(
        db: Session,
        task_uuid: str,
        owner_id: int,
        is_admin: bool = False,
    ) -> AgentTask:
        task = (
            db.query(AgentTask)
            .filter(
                AgentTask.task_uuid == task_uuid,
                AgentTask.tool == "oradad",
            )
            .first()
        )
        if task is None:
            raise NotFoundError("Tache ORADAD introuvable")
        if task.owner_id != owner_id and not is_admin:
            raise NotFoundError("Tache ORADAD introuvable")
        return task

    @staticmethod
    def list_tasks(
        db: Session,
        owner_id: int,
        is_admin: bool = False,
    ) -> list[AgentTask]:
        query = db.query(AgentTask).filter(AgentTask.tool == "oradad")
        if not is_admin:
            query = query.filter(AgentTask.owner_id == owner_id)
        return query.order_by(AgentTask.created_at.desc()).all()

    @staticmethod
    def analyze(db: Session, task: AgentTask) -> dict:
        """Lance l'analyse ANSSI et persiste le rapport dans result_summary."""
        if task.status != "completed":
            raise BusinessRuleError(f"La tache n'est pas terminee (status: {task.status})")

        if task.result_summary and "anssi_report" in task.result_summary:
            return task.result_summary["anssi_report"]

        if not task.result_raw:
            raise BusinessRuleError("Aucune donnee brute disponible pour cette tache")

        try:
            raw_bytes = task.result_raw.encode("utf-8") if isinstance(task.result_raw, str) else task.result_raw
            parsed_data = OradadAnalysisService.parse_oradad_tar(raw_bytes)
        except ValueError as exc:
            raise BusinessRuleError(str(exc))

        findings = OradadAnalysisService.run_anssi_checks(db, parsed_data)
        score = OradadAnalysisService.calculate_score(findings)

        report = {
            "findings": findings,
            "score": score["score"],
            "level": score["level"],
            "stats": {
                "total_checks": score["total_checks"],
                "passed": score["passed"],
                "failed": score["failed"],
                "warning": score["warning"],
                "not_checked": score["not_checked"],
            },
        }

        summary = dict(task.result_summary) if task.result_summary else {}
        summary["anssi_report"] = report
        task.result_summary = summary
        db.flush()

        logger.info(
            "Analyse ANSSI terminee pour la tache %s — score: %s, level: %s",
            task.task_uuid,
            report["score"],
            report["level"],
        )

        return report
