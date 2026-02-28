"""add_event_fk_to_email_service_jobs

Revision ID: 52228cb6a47a
Revises: 81b4d5da1835
Create Date: 2026-02-28 07:40:58.276081

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "52228cb6a47a"
down_revision: Union[str, Sequence[str], None] = "81b4d5da1835"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "email_service_jobs_event_fk",
        "email_service_jobs",
        "events",
        ["event_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "email_service_jobs_event_fk", "email_service_jobs", type_="foreignkey"
    )
