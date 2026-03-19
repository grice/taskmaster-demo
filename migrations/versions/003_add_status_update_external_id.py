"""Add external_id to status updates

Revision ID: 003_add_status_update_external_id
Revises: 002_person_teams_m2m
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_status_update_external_id'
down_revision = '002_person_teams_m2m'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('status_update') as batch_op:
        batch_op.add_column(sa.Column('external_id', sa.String(length=255), nullable=True))
        batch_op.create_index('ix_status_update_external_id', ['external_id'], unique=False)


def downgrade():
    with op.batch_alter_table('status_update') as batch_op:
        batch_op.drop_index('ix_status_update_external_id')
        batch_op.drop_column('external_id')
