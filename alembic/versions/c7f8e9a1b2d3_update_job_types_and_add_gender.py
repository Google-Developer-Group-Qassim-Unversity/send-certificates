"""update job types and add gender

Revision ID: c7f8e9a1b2d3
Revises: 52228cb6a47a
Create Date: 2026-03-02 05:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "c7f8e9a1b2d3"
down_revision: Union[str, Sequence[str], None] = "52228cb6a47a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE email_service_jobs 
        MODIFY COLUMN job_type ENUM(
            'certificate_attendance',
            'certificate_custom',
            'email_blast',
            'reminder',
            'notification'
        ) NOT NULL
    """)
    
    op.execute("""
        UPDATE email_service_jobs 
        SET job_type = 'certificate_attendance' 
        WHERE job_type = 'certificate'
    """)
    
    op.execute("""
        UPDATE email_service_jobs 
        SET job_type = 'certificate_custom' 
        WHERE job_type = 'custom'
    """)
    
    op.add_column(
        "email_service_recipients",
        sa.Column("gender", mysql.VARCHAR(length=20), nullable=True)
    )


def downgrade() -> None:
    op.execute("""
        ALTER TABLE email_service_jobs 
        MODIFY COLUMN job_type ENUM(
            'certificate',
            'reminder',
            'notification',
            'custom'
        ) NOT NULL
    """)
    
    op.execute("""
        UPDATE email_service_jobs 
        SET job_type = 'certificate' 
        WHERE job_type = 'certificate_attendance'
    """)
    
    op.execute("""
        UPDATE email_service_jobs 
        SET job_type = 'custom' 
        WHERE job_type = 'certificate_custom'
    """)
    
    op.drop_column("email_service_recipients", "gender")
