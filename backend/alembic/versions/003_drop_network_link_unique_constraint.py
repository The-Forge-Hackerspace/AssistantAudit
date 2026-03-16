from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_drop_network_link_unique"
down_revision: Union[str, None] = "002_add_network_map_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("network_links") as batch_op:
        batch_op.drop_constraint("uq_network_link_pair", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("network_links") as batch_op:
        batch_op.create_unique_constraint(
            "uq_network_link_pair",
            ["source_equipement_id", "target_equipement_id", "source_interface", "target_interface"],
        )
