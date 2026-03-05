"""refactor job event data and blasts

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-05 10:00:00.000000

- Add event columns to email_service_jobs (event_name, event_start_datetime, event_end_datetime, is_official)
- Remove job_config from email_service_jobs
- Rename email_service_email_blasts to email_service_blasts
- Add recipients column to email_service_blasts
- Remove is_templated, sent_count, failed_count, provider_response, sent_at from email_service_blasts

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
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
    row = result.scalar()
    return row is not None and row > 0


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM information_schema.tables "
            f"WHERE table_schema = DATABASE() "
            f"AND table_name = '{table_name}'"
        )
    )
    row = result.scalar()
    return row is not None and row > 0


def upgrade() -> None:
    # Part 1: Rename email_service_email_blasts to email_service_blasts FIRST
    if table_exists('email_service_email_blasts') and not table_exists('email_service_blasts'):
        op.execute("RENAME TABLE email_service_email_blasts TO email_service_blasts")
    
    # Part 2: Add recipients column to email_service_blasts
    if not column_exists('email_service_blasts', 'recipients'):
        op.add_column('email_service_blasts', sa.Column('recipients', sa.JSON(), nullable=True))
    
    # Migrate recipients from job_config to blasts table (before job_config is dropped)
    op.execute("""
        UPDATE email_service_blasts b
        JOIN email_service_jobs j ON b.job_id = j.id
        SET b.recipients = JSON_EXTRACT(j.job_config, '$.recipients')
        WHERE j.job_type = 'email_blast' AND j.job_config IS NOT NULL
    """)
    
    # Set empty array for any remaining NULL recipients
    op.execute("""
        UPDATE email_service_blasts 
        SET recipients = JSON_ARRAY()
        WHERE recipients IS NULL
    """)
    
    # Make recipients NOT NULL after migration
    op.execute("""
        ALTER TABLE email_service_blasts 
        MODIFY COLUMN recipients JSON NOT NULL
    """)
    
    # Part 3: Remove columns from email_service_blasts
    if column_exists('email_service_blasts', 'is_templated'):
        op.drop_column('email_service_blasts', 'is_templated')
    if column_exists('email_service_blasts', 'sent_count'):
        op.drop_column('email_service_blasts', 'sent_count')
    if column_exists('email_service_blasts', 'failed_count'):
        op.drop_column('email_service_blasts', 'failed_count')
    if column_exists('email_service_blasts', 'provider_response'):
        op.drop_column('email_service_blasts', 'provider_response')
    if column_exists('email_service_blasts', 'sent_at'):
        op.drop_column('email_service_blasts', 'sent_at')
    
    # Part 4: email_service_jobs - add event columns
    if not column_exists('email_service_jobs', 'event_name'):
        op.add_column('email_service_jobs', sa.Column('event_name', sa.VARCHAR(150), nullable=True))
    if not column_exists('email_service_jobs', 'event_start_datetime'):
        op.add_column('email_service_jobs', sa.Column('event_start_datetime', sa.DateTime(), nullable=True))
    if not column_exists('email_service_jobs', 'event_end_datetime'):
        op.add_column('email_service_jobs', sa.Column('event_end_datetime', sa.DateTime(), nullable=True))
    if not column_exists('email_service_jobs', 'is_official'):
        op.add_column('email_service_jobs', sa.Column('is_official', mysql.TINYINT(1), nullable=True))
    
    # Migrate existing job_config data to new columns (for custom jobs without event_id)
    # Only migrate if event_date is a valid date format (not placeholder "string")
    op.execute("""
        UPDATE email_service_jobs 
        SET 
            event_name = JSON_UNQUOTE(job_config->'$.event_name'),
            event_start_datetime = CASE 
                WHEN JSON_UNQUOTE(job_config->'$.event_date') REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                THEN STR_TO_DATE(JSON_UNQUOTE(job_config->'$.event_date'), '%Y-%m-%d')
                ELSE NULL
            END,
            event_end_datetime = CASE 
                WHEN JSON_UNQUOTE(job_config->'$.event_date') REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                THEN STR_TO_DATE(JSON_UNQUOTE(job_config->'$.event_date'), '%Y-%m-%d')
                ELSE NULL
            END,
            is_official = CASE 
                WHEN job_config->'$.official' = true THEN 1
                WHEN job_config->'$.official' = false THEN 0
                ELSE COALESCE(CAST(job_config->'$.official' AS SIGNED), 0)
            END
        WHERE event_id IS NULL AND job_config IS NOT NULL
    """)
    
    # Drop job_config column
    if column_exists('email_service_jobs', 'job_config'):
        op.drop_column('email_service_jobs', 'job_config')


def downgrade() -> None:
    # Part 4 reverse: Restore job_config and remove event columns
    if not column_exists('email_service_jobs', 'job_config'):
        op.add_column('email_service_jobs', sa.Column('job_config', sa.JSON(), nullable=True))
    
    # Migrate data back to job_config
    op.execute("""
        UPDATE email_service_jobs 
        SET job_config = JSON_OBJECT(
            'event_name', COALESCE(event_name, 'Unknown'),
            'event_date', DATE_FORMAT(event_start_datetime, '%Y-%m-%d'),
            'official', COALESCE(is_official, 0)
        )
        WHERE event_id IS NULL
    """)
    
    if column_exists('email_service_jobs', 'is_official'):
        op.drop_column('email_service_jobs', 'is_official')
    if column_exists('email_service_jobs', 'event_end_datetime'):
        op.drop_column('email_service_jobs', 'event_end_datetime')
    if column_exists('email_service_jobs', 'event_start_datetime'):
        op.drop_column('email_service_jobs', 'event_start_datetime')
    if column_exists('email_service_jobs', 'event_name'):
        op.drop_column('email_service_jobs', 'event_name')
    
    # Part 3 reverse: Restore email_service_blasts columns
    if not column_exists('email_service_blasts', 'sent_at'):
        op.add_column('email_service_blasts', sa.Column('sent_at', sa.DateTime(), nullable=True))
    if not column_exists('email_service_blasts', 'provider_response'):
        op.add_column('email_service_blasts', sa.Column('provider_response', sa.JSON(), nullable=True))
    if not column_exists('email_service_blasts', 'failed_count'):
        op.add_column('email_service_blasts', sa.Column('failed_count', mysql.INTEGER(), server_default='0', nullable=False))
    if not column_exists('email_service_blasts', 'sent_count'):
        op.add_column('email_service_blasts', sa.Column('sent_count', mysql.INTEGER(), server_default='0', nullable=False))
    if not column_exists('email_service_blasts', 'is_templated'):
        op.add_column('email_service_blasts', sa.Column('is_templated', mysql.TINYINT(1), server_default='0', nullable=False))
    
    # Drop recipients column
    if column_exists('email_service_blasts', 'recipients'):
        op.drop_column('email_service_blasts', 'recipients')
    
    # Part 1 reverse: Rename table back
    if table_exists('email_service_blasts') and not table_exists('email_service_email_blasts'):
        op.execute("RENAME TABLE email_service_blasts TO email_service_email_blasts")
