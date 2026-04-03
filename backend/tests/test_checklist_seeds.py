"""Tests TDD — Seeds checklists salle serveur, documentation, départ (step 33)."""


class TestChecklistSeedData:
    """CK-005, CK-006, CK-007 : contenu des seeds checklists."""

    def test_server_room_seed_structure(self):
        """La checklist salle serveur a 7 sections et ~38 items."""
        from scripts.seed_checklist_server_room import CHECKLIST_SERVER_ROOM

        sections = CHECKLIST_SERVER_ROOM["sections"]
        assert len(sections) == 7
        total_items = sum(len(s["items"]) for s in sections)
        assert total_items >= 35
        assert CHECKLIST_SERVER_ROOM["category"] == "server_room"

    def test_documentation_seed_structure(self):
        """La checklist documentation a 5 sections et ~22 items."""
        from scripts.seed_checklist_documentation import CHECKLIST_DOCUMENTATION

        sections = CHECKLIST_DOCUMENTATION["sections"]
        assert len(sections) == 5
        total_items = sum(len(s["items"]) for s in sections)
        assert total_items >= 20
        assert CHECKLIST_DOCUMENTATION["category"] == "documentation"

    def test_departure_seed_structure(self):
        """La checklist départ a 5 sections et ~18 items."""
        from scripts.seed_checklist_departure import CHECKLIST_DEPARTURE

        sections = CHECKLIST_DEPARTURE["sections"]
        assert len(sections) == 5
        total_items = sum(len(s["items"]) for s in sections)
        assert total_items >= 15
        assert CHECKLIST_DEPARTURE["category"] == "departure"

    def test_all_items_have_ref_and_label(self):
        """Chaque item a un ref_code et un label."""
        from scripts.seed_checklist_departure import CHECKLIST_DEPARTURE
        from scripts.seed_checklist_documentation import CHECKLIST_DOCUMENTATION
        from scripts.seed_checklist_server_room import CHECKLIST_SERVER_ROOM

        for checklist in [CHECKLIST_SERVER_ROOM, CHECKLIST_DOCUMENTATION, CHECKLIST_DEPARTURE]:
            for section in checklist["sections"]:
                for item in section["items"]:
                    assert "ref" in item, f"Item sans ref dans {checklist['name']}"
                    assert "label" in item, f"Item sans label dans {checklist['name']}"
                    assert len(item["label"]) > 5, f"Label trop court: {item['label']}"

    def test_server_room_seed_idempotent(self, db_session):
        """Le seed est idempotent — pas de doublon si lancé 2 fois."""
        from app.models.checklist import ChecklistTemplate
        from scripts.seed_checklist_server_room import seed

        seed(db_session)
        count1 = db_session.query(ChecklistTemplate).filter_by(category="server_room").count()
        seed(db_session)  # 2e exécution
        count2 = db_session.query(ChecklistTemplate).filter_by(category="server_room").count()
        assert count1 == count2

    def test_documentation_seed_idempotent(self, db_session):
        """Le seed documentation est idempotent — pas de doublon si lancé 2 fois."""
        from app.models.checklist import ChecklistTemplate
        from scripts.seed_checklist_documentation import seed

        seed(db_session)
        count1 = db_session.query(ChecklistTemplate).filter_by(category="documentation").count()
        seed(db_session)
        count2 = db_session.query(ChecklistTemplate).filter_by(category="documentation").count()
        assert count1 == count2

    def test_departure_seed_idempotent(self, db_session):
        """Le seed départ est idempotent — pas de doublon si lancé 2 fois."""
        from app.models.checklist import ChecklistTemplate
        from scripts.seed_checklist_departure import seed

        seed(db_session)
        count1 = db_session.query(ChecklistTemplate).filter_by(category="departure").count()
        seed(db_session)
        count2 = db_session.query(ChecklistTemplate).filter_by(category="departure").count()
        assert count1 == count2
