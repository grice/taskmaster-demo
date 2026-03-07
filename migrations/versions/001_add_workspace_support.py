"""Add multi-workspace support

Revision ID: 001_add_workspace_support
Revises:
Create Date: 2026-03-07

Steps:
1. Create workspace table
2. Add nullable workspace_id to project, person, team, tag, task
3. Insert default workspace
4. Backfill all existing rows
5. Recreate tables with NOT NULL constraint (SQLite requires batch mode)
6. Replace tag.name unique index with (workspace_id, name)
"""
from alembic import op
import sqlalchemy as sa

revision = '001_add_workspace_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create workspace table
    op.create_table(
        'workspace',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # 2. Add nullable workspace_id columns to all affected tables
    with op.batch_alter_table('team') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('person') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('project') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('task') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('tag') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.Integer(), nullable=True))

    # 3. Insert the default workspace
    conn = op.get_bind()
    conn.execute(sa.text(
        "INSERT INTO workspace (name, slug) VALUES ('Default', 'default')"
    ))
    default_ws = conn.execute(sa.text("SELECT id FROM workspace WHERE slug = 'default'")).fetchone()
    default_id = default_ws[0]

    # 4. Backfill all existing rows to the default workspace
    conn.execute(sa.text(f"UPDATE team SET workspace_id = {default_id}"))
    conn.execute(sa.text(f"UPDATE person SET workspace_id = {default_id}"))
    conn.execute(sa.text(f"UPDATE project SET workspace_id = {default_id}"))
    conn.execute(sa.text(f"UPDATE task SET workspace_id = {default_id}"))
    conn.execute(sa.text(f"UPDATE tag SET workspace_id = {default_id}"))

    # 5. Recreate tables with NOT NULL constraints and foreign keys
    with op.batch_alter_table('team') as batch_op:
        batch_op.alter_column('workspace_id', nullable=False)
        batch_op.create_foreign_key('fk_team_workspace', 'workspace', ['workspace_id'], ['id'])

    with op.batch_alter_table('person') as batch_op:
        batch_op.alter_column('workspace_id', nullable=False)
        batch_op.create_foreign_key('fk_person_workspace', 'workspace', ['workspace_id'], ['id'])

    with op.batch_alter_table('project') as batch_op:
        batch_op.alter_column('workspace_id', nullable=False)
        batch_op.create_foreign_key('fk_project_workspace', 'workspace', ['workspace_id'], ['id'])

    with op.batch_alter_table('task') as batch_op:
        batch_op.alter_column('workspace_id', nullable=False)
        batch_op.create_foreign_key('fk_task_workspace', 'workspace', ['workspace_id'], ['id'])

    # 6. Replace tag.name unique with (workspace_id, name) unique
    with op.batch_alter_table('tag') as batch_op:
        batch_op.alter_column('workspace_id', nullable=False)
        batch_op.create_foreign_key('fk_tag_workspace', 'workspace', ['workspace_id'], ['id'])
        # Add composite unique constraint (batch mode recreates the table, so old
        # unique=True on name is dropped automatically in the process)
        batch_op.create_unique_constraint('uq_tag_workspace_name', ['workspace_id', 'name'])


def downgrade():
    with op.batch_alter_table('tag') as batch_op:
        batch_op.drop_constraint('uq_tag_workspace_name', type_='unique')
        batch_op.drop_constraint('fk_tag_workspace', type_='foreignkey')
        batch_op.drop_column('workspace_id')
        batch_op.create_unique_constraint('uq_tag_name', ['name'])

    with op.batch_alter_table('task') as batch_op:
        batch_op.drop_constraint('fk_task_workspace', type_='foreignkey')
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('project') as batch_op:
        batch_op.drop_constraint('fk_project_workspace', type_='foreignkey')
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('person') as batch_op:
        batch_op.drop_constraint('fk_person_workspace', type_='foreignkey')
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('team') as batch_op:
        batch_op.drop_constraint('fk_team_workspace', type_='foreignkey')
        batch_op.drop_column('workspace_id')

    op.drop_table('workspace')
