"""
Service Framework : chargement, import/export de référentiels YAML, versioning.

100% dynamique : les fichiers YAML du dossier frameworks/ sont la source de vérité.
Au démarrage du serveur, les référentiels sont automatiquement synchronisés en base.
Un nouveau fichier YAML est détecté et importé sans modification de code.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.framework import CheckType, Control, ControlSeverity, Framework, FrameworkCategory

logger = logging.getLogger(__name__)


class FrameworkService:
    # ------------------------------------------------------------------ #
    #  Listing / get
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_frameworks(
        db: Session, active_only: bool = True, offset: int = 0, limit: int = 20
    ) -> tuple[list[Framework], int]:
        """Liste les référentiels"""
        query = db.query(Framework)
        if active_only:
            query = query.filter(Framework.is_active.is_(True))
        total = query.count()
        frameworks = query.order_by(Framework.name).offset(offset).limit(limit).all()
        return frameworks, total

    @staticmethod
    def get_framework(db: Session, framework_id: int) -> Optional[Framework]:
        """Récupère un référentiel avec ses catégories et contrôles"""
        return db.get(Framework, framework_id)

    @staticmethod
    def get_framework_by_ref(db: Session, ref_id: str) -> Optional[Framework]:
        """Récupère un référentiel par son ref_id"""
        return db.query(Framework).filter(Framework.ref_id == ref_id).first()

    # ------------------------------------------------------------------ #
    #  Import (YAML → BDD)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _file_hash(path: Path) -> str:
        """Calcule un hash SHA-256 du contenu d'un fichier YAML."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def import_from_yaml(db: Session, yaml_path: str | Path) -> Framework:
        """
        Importe un référentiel depuis un fichier YAML.
        Crée ou met à jour le framework en base de données.
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Fichier YAML introuvable : {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        fw_data = data.get("framework", data)
        file_hash = FrameworkService._file_hash(yaml_path)
        return FrameworkService._import_from_data(db, fw_data, yaml_path, file_hash)

    @staticmethod
    def _import_from_data(db: Session, fw_data: dict, yaml_path: Path, file_hash: str) -> Framework:
        """
        Importe un framework à partir de données YAML déjà parsées.
        Évite le double parsing quand les données sont déjà lues.
        """
        ref_id = fw_data.get("ref_id", yaml_path.stem)
        name = fw_data["name"]
        version = fw_data.get("version", "1.0")

        # Vérifier si le framework existe déjà (même ref_id + version)
        existing = db.query(Framework).filter(Framework.ref_id == ref_id, Framework.version == version).first()
        if existing:
            # Si le fichier n'a pas changé, skip
            if existing.source_hash == file_hash:
                logger.debug(f"Framework '{ref_id}' v{version} inchangé, skip")
                return existing

            logger.info(f"Mise à jour du framework '{ref_id}' v{version} depuis {yaml_path.name}")
            # Supprimer les anciennes catégories (cascade supprimera les contrôles)
            for cat in existing.categories:
                db.delete(cat)
            db.flush()
            framework = existing
            framework.name = name
            framework.version = version
            framework.description = fw_data.get("description")
            framework.engine = fw_data.get("engine")
            framework.engine_config = fw_data.get("engine_config")
            framework.source = fw_data.get("source")
            framework.author = fw_data.get("author")
            framework.source_file = str(yaml_path)
            framework.source_hash = file_hash
        else:
            logger.info(f"Import du nouveau framework '{ref_id}' v{version} depuis {yaml_path.name}")
            framework = Framework(
                ref_id=ref_id,
                name=name,
                description=fw_data.get("description"),
                version=version,
                engine=fw_data.get("engine"),
                engine_config=fw_data.get("engine_config"),
                source=fw_data.get("source"),
                author=fw_data.get("author"),
                source_file=str(yaml_path),
                source_hash=file_hash,
            )
            db.add(framework)
            db.flush()

        # Importer les catégories et contrôles
        for cat_order, cat_data in enumerate(fw_data.get("categories", []), start=1):
            category = FrameworkCategory(
                name=cat_data["name"],
                description=cat_data.get("description"),
                order=cat_order,
                framework_id=framework.id,
            )
            db.add(category)
            db.flush()

            for ctrl_order, ctrl_data in enumerate(cat_data.get("controls", []), start=1):
                control = Control(
                    ref_id=ctrl_data["id"],
                    title=ctrl_data["title"],
                    description=ctrl_data.get("description"),
                    severity=ControlSeverity(ctrl_data.get("severity", "medium")),
                    check_type=CheckType(ctrl_data.get("check_type", "manual")),
                    order=ctrl_order,
                    auto_check_function=ctrl_data.get("auto_check"),
                    engine_rule_id=ctrl_data.get("engine_rule_id", ctrl_data.get("monkey365_rule")),
                    cis_reference=ctrl_data.get("cis_reference"),
                    remediation=ctrl_data.get("remediation"),
                    evidence_required=ctrl_data.get("evidence_required", False),
                    category_id=category.id,
                )
                db.add(control)

        db.flush()
        db.refresh(framework)
        logger.info(
            f"Framework '{framework.ref_id}' importé : "
            f"{len(framework.categories)} catégories, "
            f"{framework.total_controls} contrôles"
        )
        return framework

    @staticmethod
    def import_all_from_directory(db: Session, directory: str | Path) -> list[Framework]:
        """Importe tous les fichiers YAML d'un répertoire"""
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Répertoire de frameworks inexistant : {directory}")
            return []

        frameworks = []
        for yaml_file in sorted(directory.glob("*.yaml")):
            try:
                fw = FrameworkService.import_from_yaml(db, yaml_file)
                frameworks.append(fw)
            except Exception as e:
                logger.error(f"Erreur import de {yaml_file.name}: {e}")
                continue

        logger.info(f"{len(frameworks)} frameworks importés depuis {directory}")
        return frameworks

    # ------------------------------------------------------------------ #
    #  Sync automatique (détection fichiers nouveaux/modifiés)
    # ------------------------------------------------------------------ #

    @staticmethod
    def sync_from_directory(db: Session, directory: str | Path) -> dict:
        """
        Synchronise les frameworks YAML ↔ BDD.
        - Importe les nouveaux fichiers YAML
        - Met à jour les frameworks dont le fichier a changé (hash différent)
        - Skipe les fichiers inchangés

        Retourne un résumé : {imported, updated, unchanged, errors}
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Répertoire de frameworks inexistant : {directory}")
            return {"imported": 0, "updated": 0, "unchanged": 0, "errors": []}

        result = {"imported": 0, "updated": 0, "unchanged": 0, "errors": []}

        for yaml_file in sorted(directory.glob("*.yaml")):
            try:
                file_hash = FrameworkService._file_hash(yaml_file)

                # Lire le ref_id et version du fichier
                with open(yaml_file, "r", encoding="utf-8") as f:
                    fw_data_raw = yaml.safe_load(f)
                fw_data = fw_data_raw.get("framework", fw_data_raw)
                ref_id = fw_data.get("ref_id", yaml_file.stem)
                version = fw_data.get("version", "1.0")

                # Chercher en base
                existing = db.query(Framework).filter(Framework.ref_id == ref_id, Framework.version == version).first()

                if existing and existing.source_hash == file_hash:
                    result["unchanged"] += 1
                    continue

                # Import (crée ou met à jour) en passant les données déjà lues
                FrameworkService._import_from_data(db, fw_data, yaml_file, file_hash)
                if existing:
                    result["updated"] += 1
                else:
                    result["imported"] += 1

            except Exception as e:
                logger.error(f"Erreur sync de {yaml_file.name}: {e}")
                result["errors"].append(f"{yaml_file.name}: {str(e)}")
                continue

        total = result["imported"] + result["updated"] + result["unchanged"]
        logger.info(
            f"Sync frameworks : {total} fichiers traités "
            f"({result['imported']} nouveaux, {result['updated']} mis à jour, "
            f"{result['unchanged']} inchangés)"
        )
        return result

    @staticmethod
    def export_to_yaml(db: Session, framework_id: int, output_path: str | Path) -> Path:
        """Exporte un framework en YAML"""
        fw = db.get(Framework, framework_id)
        if not fw:
            raise ValueError(f"Framework {framework_id} introuvable")

        output_path = Path(output_path)
        data = {
            "framework": {
                "ref_id": fw.ref_id,
                "name": fw.name,
                "description": fw.description,
                "version": fw.version,
                "engine": fw.engine,
                "source": fw.source,
                "author": fw.author,
                "engine_config": fw.engine_config,
                "categories": [],
            }
        }

        for cat in fw.categories:
            cat_data = {
                "name": cat.name,
                "description": cat.description,
                "controls": [],
            }
            for ctrl in cat.controls:
                ctrl_data = {
                    "id": ctrl.ref_id,
                    "title": ctrl.title,
                    "description": ctrl.description,
                    "severity": ctrl.severity.value,
                    "check_type": ctrl.check_type.value,
                    "remediation": ctrl.remediation,
                    "evidence_required": ctrl.evidence_required,
                }
                if ctrl.auto_check_function:
                    ctrl_data["auto_check"] = ctrl.auto_check_function
                if ctrl.engine_rule_id:
                    ctrl_data["engine_rule_id"] = ctrl.engine_rule_id
                if ctrl.cis_reference:
                    ctrl_data["cis_reference"] = ctrl.cis_reference
                cat_data["controls"].append(ctrl_data)
            data["framework"]["categories"].append(cat_data)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Framework '{fw.ref_id}' exporté vers {output_path}")
        return output_path

    @staticmethod
    def clone_as_new_version(db: Session, framework_id: int, new_version: str, new_name: str = None) -> Framework:
        """
        Clone un framework existant en tant que nouvelle version.
        L'ancienne version est désactivée, la nouvelle hérite de tous
        les catégories et contrôles.
        """
        original = db.get(Framework, framework_id)
        if not original:
            raise ValueError(f"Framework {framework_id} introuvable")

        # Créer le clone
        clone = Framework(
            ref_id=original.ref_id,
            name=new_name or original.name,
            description=original.description,
            version=new_version,
            engine=original.engine,
            engine_config=original.engine_config,
            source=original.source,
            author=original.author,
            source_file=original.source_file,
            parent_version_id=original.id,
        )
        db.add(clone)
        db.flush()

        # Cloner catégories + contrôles
        for cat in original.categories:
            new_cat = FrameworkCategory(
                name=cat.name,
                description=cat.description,
                order=cat.order,
                framework_id=clone.id,
            )
            db.add(new_cat)
            db.flush()
            for ctrl in cat.controls:
                new_ctrl = Control(
                    ref_id=ctrl.ref_id,
                    title=ctrl.title,
                    description=ctrl.description,
                    severity=ctrl.severity,
                    check_type=ctrl.check_type,
                    order=ctrl.order,
                    auto_check_function=ctrl.auto_check_function,
                    engine_rule_id=ctrl.engine_rule_id,
                    cis_reference=ctrl.cis_reference,
                    remediation=ctrl.remediation,
                    evidence_required=ctrl.evidence_required,
                    category_id=new_cat.id,
                )
                db.add(new_ctrl)

        # Désactiver l'ancienne version
        original.is_active = False

        db.flush()
        db.refresh(clone)
        logger.info(
            f"Framework '{clone.ref_id}' cloné : v{original.version} -> v{new_version} "
            f"({clone.total_controls} contrôles)"
        )
        return clone

    @staticmethod
    def list_versions(db: Session, ref_id: str) -> list[Framework]:
        """Liste toutes les versions d'un framework par ref_id"""
        return db.query(Framework).filter(Framework.ref_id == ref_id).order_by(Framework.id.desc()).all()

    # ------------------------------------------------------------------ #
    #  CRUD manuel (éditeur de référentiels)
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_framework(
        db: Session,
        ref_id: str,
        name: str,
        version: str = "1.0",
        description: str | None = None,
        engine: str | None = None,
        engine_config: dict | None = None,
        source: str | None = None,
        author: str | None = None,
        categories: list[dict] | None = None,
    ) -> Framework:
        """Crée un nouveau framework depuis l'éditeur (pas YAML)."""
        existing = db.query(Framework).filter(Framework.ref_id == ref_id, Framework.version == version).first()
        if existing:
            raise ValueError(f"Un référentiel '{ref_id}' v{version} existe déjà")

        framework = Framework(
            ref_id=ref_id,
            name=name,
            description=description,
            version=version,
            engine=engine,
            engine_config=engine_config,
            source=source,
            author=author,
        )
        db.add(framework)
        db.flush()

        for cat_order, cat_data in enumerate(categories or [], start=1):
            category = FrameworkCategory(
                name=cat_data["name"],
                description=cat_data.get("description"),
                order=cat_order,
                framework_id=framework.id,
            )
            db.add(category)
            db.flush()
            for ctrl_order, ctrl_data in enumerate(cat_data.get("controls", []), start=1):
                control = Control(
                    ref_id=ctrl_data["ref_id"],
                    title=ctrl_data["title"],
                    description=ctrl_data.get("description"),
                    severity=ControlSeverity(ctrl_data.get("severity", "medium")),
                    check_type=CheckType(ctrl_data.get("check_type", "manual")),
                    order=ctrl_order,
                    auto_check_function=ctrl_data.get("auto_check_function"),
                    engine_rule_id=ctrl_data.get("engine_rule_id"),
                    cis_reference=ctrl_data.get("cis_reference"),
                    remediation=ctrl_data.get("remediation"),
                    evidence_required=ctrl_data.get("evidence_required", False),
                    category_id=category.id,
                )
                db.add(control)

        db.flush()
        db.refresh(framework)
        logger.info(
            f"Framework '{framework.ref_id}' v{framework.version} créé : "
            f"{len(framework.categories)} catégories, {framework.total_controls} contrôles"
        )

        # Auto-export YAML vers le dossier frameworks/
        try:
            yaml_path = Path(get_settings().FRAMEWORKS_DIR) / f"{framework.ref_id}_v{framework.version}.yaml"
            FrameworkService.export_to_yaml(db, framework.id, yaml_path)
            framework.source_file = str(yaml_path.name)
        except Exception as e:
            logger.warning(f"Export YAML automatique échoué : {e}")

        return framework

    @staticmethod
    def update_framework(
        db: Session,
        framework_id: int,
        data: dict,
    ) -> Framework:
        """
        Met à jour un framework existant.
        Si 'categories' est fourni, remplace intégralement les catégories/contrôles.
        """
        framework = db.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework {framework_id} introuvable")

        # Champs simples
        for field in ("name", "description", "engine", "engine_config", "source", "author"):
            if field in data:
                setattr(framework, field, data[field])

        # Remplacement des catégories/contrôles
        if "categories" in data:
            for cat in framework.categories:
                db.delete(cat)
            db.flush()

            for cat_order, cat_data in enumerate(data["categories"], start=1):
                category = FrameworkCategory(
                    name=cat_data["name"],
                    description=cat_data.get("description"),
                    order=cat_order,
                    framework_id=framework.id,
                )
                db.add(category)
                db.flush()
                for ctrl_order, ctrl_data in enumerate(cat_data.get("controls", []), start=1):
                    control = Control(
                        ref_id=ctrl_data["ref_id"],
                        title=ctrl_data["title"],
                        description=ctrl_data.get("description"),
                        severity=ControlSeverity(ctrl_data.get("severity", "medium")),
                        check_type=CheckType(ctrl_data.get("check_type", "manual")),
                        order=ctrl_order,
                        auto_check_function=ctrl_data.get("auto_check_function"),
                        engine_rule_id=ctrl_data.get("engine_rule_id"),
                        cis_reference=ctrl_data.get("cis_reference"),
                        remediation=ctrl_data.get("remediation"),
                        evidence_required=ctrl_data.get("evidence_required", False),
                        category_id=category.id,
                    )
                    db.add(control)

        db.flush()
        db.refresh(framework)
        logger.info(f"Framework '{framework.ref_id}' v{framework.version} mis à jour")

        # Auto-export YAML vers le dossier frameworks/
        try:
            yaml_name = framework.source_file or f"{framework.ref_id}_v{framework.version}.yaml"
            yaml_path = Path(get_settings().FRAMEWORKS_DIR) / yaml_name
            FrameworkService.export_to_yaml(db, framework.id, yaml_path)
        except Exception as e:
            logger.warning(f"Export YAML automatique échoué : {e}")

        return framework

    @staticmethod
    def delete_framework(db: Session, framework_id: int) -> None:
        """Supprime un framework et toutes ses catégories/contrôles en cascade."""
        framework = db.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework {framework_id} introuvable")
        ref = f"{framework.ref_id} v{framework.version}"
        source_file = framework.source_file
        db.delete(framework)
        db.flush()
        logger.info(f"Framework '{ref}' supprimé")

        # Supprimer le fichier YAML associé
        if source_file:
            try:
                yaml_path = Path(get_settings().FRAMEWORKS_DIR) / source_file
                if yaml_path.exists():
                    yaml_path.unlink()
                    logger.info(f"Fichier YAML '{source_file}' supprimé")
            except Exception as e:
                logger.warning(f"Suppression du fichier YAML échouée : {e}")
