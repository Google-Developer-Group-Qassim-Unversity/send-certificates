"""fix_member_fk_cascade

Revision ID: 81b4d5da1835
Revises: 2e51b9150fbd
Create Date: 2026-02-27 14:10:10.650798

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "81b4d5da1835"
down_revision: Union[str, Sequence[str], None] = "2e51b9150fbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "email_service_recipients_member_fk",
        "email_service_recipients",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "email_service_recipients_member_fk",
        "email_service_recipients",
        "members",
        ["member_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "email_service_recipients_member_fk",
        "email_service_recipients",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "email_service_recipients_member_fk",
        "email_service_recipients",
        "members",
        ["member_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )
