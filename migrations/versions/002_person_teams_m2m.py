"""Convert person team membership to many-to-many

Revision ID: 002_person_teams_m2m
Revises: 001_add_workspace_support
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = '002_person_teams_m2m'
down_revision = '001_add_workspace_support'
branch_labels = None
depends_on = None


def upgrade():
    # Create the person_teams association table
    op.create_table(
        'person_teams',
        sa.Column('person_id', sa.Integer, sa.ForeignKey('person.id'), primary_key=True),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('team.id'), primary_key=True),
    )

    # Migrate existing team_id data to the new join table
    op.execute("""
        INSERT INTO person_teams (person_id, team_id)
        SELECT id, team_id FROM person WHERE team_id IS NOT NULL
    """)

    # Drop the team_id column from person (SQLite requires batch mode)
    with op.batch_alter_table('person') as batch_op:
        batch_op.drop_column('team_id')


def downgrade():
    # Re-add team_id column (nullable — only stores one team per person)
    with op.batch_alter_table('person') as batch_op:
        batch_op.add_column(sa.Column('team_id', sa.Integer,
                                      sa.ForeignKey('team.id'), nullable=True))

    # Restore one team per person (take any row from person_teams)
    op.execute("""
        UPDATE person
        SET team_id = (
            SELECT team_id FROM person_teams
            WHERE person_teams.person_id = person.id
            LIMIT 1
        )
    """)

    op.drop_table('person_teams')
