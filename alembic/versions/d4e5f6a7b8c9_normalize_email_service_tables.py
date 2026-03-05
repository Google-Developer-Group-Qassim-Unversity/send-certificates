"""normalize email service tables

Revision ID: d4e5f6a7b8c9
Revises: c7f8e9a1b2d3
Create Date: 2026-03-04 10:00:00.000000

- Remove denormalized counter columns from email_service_jobs
- Drop unused custom_data column from email_service_recipients (if exists)
- Convert gender to ENUM for consistency
- Add unique constraints on (job_id, member_id) and (job_id, email)
- Clean up job_config for jobs with event_id (keep only for custom jobs)

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c7f8e9a1b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM information_schema.columns "
            f"WHERE table_schema = DATABASE() "
            f"AND table_name = '{table_name}' "
            f"AND column_name = '{column_name}'"
        )
    )
    return result.scalar() > 0


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM information_schema.statistics "
            f"WHERE table_schema = DATABASE() "
            f"AND table_name = '{table_name}' "
            f"AND index_name = '{index_name}'"
        )
    )
    return result.scalar() > 0


def upgrade() -> None:
    if column_exists('email_service_recipients', 'custom_data'):
        op.drop_column('email_service_recipients', 'custom_data')
    
    op.execute("""
        ALTER TABLE email_service_recipients 
        MODIFY COLUMN gender ENUM('Male', 'Female') NULL
    """)
    
    if not index_exists('email_service_recipients', 'idx_recipient_job_member_unique'):
        op.create_index(
            'idx_recipient_job_member_unique',
            'email_service_recipients',
            ['job_id', 'member_id'],
            unique=True
        )
    if not index_exists('email_service_recipients', 'idx_recipient_job_email_unique'):
        op.create_index(
            'idx_recipient_job_email_unique',
            'email_service_recipients',
            ['job_id', 'email'],
            unique=True
        )
    
    if column_exists('email_service_jobs', 'total'):
        op.drop_column('email_service_jobs', 'total')
    if column_exists('email_service_jobs', 'completed'):
        op.drop_column('email_service_jobs', 'completed')
    if column_exists('email_service_jobs', 'successful'):
        op.drop_column('email_service_jobs', 'successful')
    if column_exists('email_service_jobs', 'failed'):
        op.drop_column('email_service_jobs', 'failed')
    
    op.execute("""
        UPDATE email_service_jobs 
        SET job_config = NULL 
        WHERE event_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE email_service_jobs 
        SET job_config = JSON_OBJECT(
            'event_name', 'Unknown',
            'event_date', DATE_FORMAT(NOW(), '%Y-%m-%d'),
            'official', FALSE
        )
        WHERE event_id IS NOT NULL AND job_config IS NULL
    """)
    
    if not column_exists('email_service_jobs', 'failed'):
        op.add_column('email_service_jobs', sa.Column('failed', mysql.INTEGER(), server_default='0', nullable=False))
    if not column_exists('email_service_jobs', 'successful'):
        op.add_column('email_service_jobs', sa.Column('successful', mysql.INTEGER(), server_default='0', nullable=False))
    if not column_exists('email_service_jobs', 'completed'):
        op.add_column('email_service_jobs', sa.Column('completed', mysql.INTEGER(), server_default='0', nullable=False))
    if not column_exists('email_service_jobs', 'total'):
        op.add_column('email_service_jobs', sa.Column('total', mysql.INTEGER(), server_default='0', nullable=False))
    
    if index_exists('email_service_recipients', 'idx_recipient_job_email_unique'):
        op.drop_index('idx_recipient_job_email_unique', table_name='email_service_recipients')
    if index_exists('email_service_recipients', 'idx_recipient_job_member_unique'):
        op.drop_index('idx_recipient_job_member_unique', table_name='email_service_recipients')
    
    op.execute("""
        ALTER TABLE email_service_recipients 
        MODIFY COLUMN gender VARCHAR(20) NULL
    """)
    
    if not column_exists('email_service_recipients', 'custom_data'):
        op.add_column('email_service_recipients', sa.Column('custom_data', sa.JSON(), nullable=True))
