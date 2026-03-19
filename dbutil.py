"""Export and import the Tideline database to/from CSV files.

Usage:
    python dbutil.py export [output_dir]   # default: ./export
    python dbutil.py import [input_dir]    # default: ./export
"""
import csv
import os
import sys
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError
from app import create_app
from models import (db, Workspace, Team, Person, Project, Task, TaskAssignment,
                    TaskDependency, Tag, Milestone, StatusUpdate, task_tags,
                    person_teams, status_update_mentions)

app = create_app()

# Table export order (respects foreign key dependencies)
TABLES = [
    ('workspaces.csv', Workspace, ['id', 'name', 'slug']),
    ('teams.csv', Team, ['id', 'name', 'workspace_id']),
    ('people.csv', Person, ['id', 'name', 'email', 'workspace_id']),
    ('projects.csv', Project, ['id', 'name', 'description', 'start_date', 'end_date', 'status', 'workspace_id']),
    ('tags.csv', Tag, ['id', 'name', 'workspace_id']),
    ('tasks.csv', Task, ['id', 'title', 'description', 'project_id', 'start_date', 'end_date', 'status', 'priority', 'workspace_id']),
    ('task_assignments.csv', TaskAssignment, ['id', 'task_id', 'person_id', 'is_lead']),
    ('task_dependencies.csv', TaskDependency, ['id', 'task_id', 'depends_on_id']),
    ('milestones.csv', Milestone, ['id', 'task_id', 'name', 'date', 'status_override']),
    ('status_updates.csv', StatusUpdate, ['id', 'task_id', 'content', 'created_at', 'external_id']),
]

# Many-to-many association tables
ASSOC_TABLES = [
    ('task_tags.csv', task_tags, ['task_id', 'tag_id']),
    ('person_teams.csv', person_teams, ['person_id', 'team_id']),
    ('status_update_mentions.csv', status_update_mentions, ['status_update_id', 'person_id']),
]


def export_db(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with app.app_context():
        for filename, model, columns in TABLES:
            path = os.path.join(output_dir, filename)
            rows = model.query.all()
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([getattr(row, col) for col in columns])
            print(f'  Exported {len(rows):>4} rows -> {filename}')

        for filename, table, columns in ASSOC_TABLES:
            path = os.path.join(output_dir, filename)
            rows = db.session.execute(table.select()).fetchall()
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(list(row))
            print(f'  Exported {len(rows):>4} rows -> {filename}')

    print(f'\nExport complete: {output_dir}/')


def _count_csv_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', newline='') as f:
        return sum(1 for _ in csv.DictReader(f))


def _verify_import(input_dir, legacy_mode=False):
    print('\nPost-import verification:')

    for filename, model, columns in TABLES:
        expected = _count_csv_rows(os.path.join(input_dir, filename))
        if legacy_mode and filename == 'workspaces.csv' and expected is None:
            expected = 1
        actual = model.query.count()
        if expected is None:
            print(f'  {filename:<24} skipped (file not present), db has {actual}')
        else:
            status = 'OK' if actual == expected else 'MISMATCH'
            print(f'  {filename:<24} expected {expected:>4}, actual {actual:>4}  [{status}]')

    for filename, table, columns in ASSOC_TABLES:
        expected = _count_csv_rows(os.path.join(input_dir, filename))
        if legacy_mode and filename == 'person_teams.csv' and expected is None:
            people_path = os.path.join(input_dir, 'people.csv')
            expected = 0
            if os.path.exists(people_path):
                with open(people_path, 'r', newline='') as f:
                    for row in csv.DictReader(f):
                        if row.get('team_id'):
                            expected += 1
        actual = len(db.session.execute(table.select()).fetchall())
        if expected is None:
            print(f'  {filename:<24} skipped (file not present), db has {actual}')
        else:
            status = 'OK' if actual == expected else 'MISMATCH'
            print(f'  {filename:<24} expected {expected:>4}, actual {actual:>4}  [{status}]')


def import_db(input_dir):
    with app.app_context():
        # Auto-backup before overwriting
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backup_{timestamp}'
        print(f'Backing up current database to {backup_dir}/...\n')
        export_db(backup_dir)
        print(f'\nBackup complete. Proceeding with import...\n')

        legacy_mode = not os.path.exists(os.path.join(input_dir, 'workspaces.csv'))
        default_workspace_id = None

        try:
            # Clear all association tables first, then model tables. This avoids
            # duplicate composite-key rows on re-import, especially in person_teams.
            for filename, table, columns in reversed(ASSOC_TABLES):
                db.session.execute(table.delete())
            for filename, model, columns in reversed(TABLES):
                db.session.query(model).delete()

            if legacy_mode:
                default_workspace = Workspace(id=1, name='Imported Workspace', slug='imported-workspace')
                db.session.add(default_workspace)
                db.session.flush()
                default_workspace_id = default_workspace.id
                print('  Legacy import mode: created default workspace for pre-workspace backup')

            pending_person_teams = []

            for filename, model, columns in TABLES:
                path = os.path.join(input_dir, filename)
                if not os.path.exists(path):
                    print(f'  Skipped {filename} (not found)')
                    continue
                count = 0
                with open(path, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    header = set(reader.fieldnames or [])
                    for row in reader:
                        # Fill missing columns with None so older backups still import
                        # after additive schema changes like StatusUpdate.external_id.
                        for col in columns:
                            row.setdefault(col, None)
                        # Convert empty strings to None for nullable fields
                        for key in row:
                            if row[key] == '':
                                row[key] = None
                        # Convert types
                        if 'id' in row and row['id'] is not None:
                            row['id'] = int(row['id'])
                        for col in columns:
                            if col.endswith('_id') and col != 'external_id' and row.get(col) is not None:
                                row[col] = int(row[col])
                            # Date fields (YYYY-MM-DD)
                            if (col == 'date' or col.endswith('_date')) and col != 'created_at' and row.get(col) is not None:
                                row[col] = date.fromisoformat(row[col])
                            # Datetime fields
                            if col == 'created_at' and row.get(col) is not None:
                                row[col] = datetime.fromisoformat(row[col])

                        if legacy_mode and default_workspace_id is not None:
                            if 'workspace_id' in columns and 'workspace_id' not in header:
                                row['workspace_id'] = default_workspace_id
                            if filename == 'people.csv' and 'team_id' in header and row.get('team_id') is not None:
                                pending_person_teams.append((int(row['id']), int(row['team_id'])))

                        if 'is_lead' in row and row['is_lead'] is not None:
                            row['is_lead'] = row['is_lead'] in ('True', 'true', '1')
                        obj = model(**{c: row.get(c) for c in columns})
                        db.session.add(obj)
                        count += 1
                db.session.flush()
                print(f'  Imported {count:>4} rows <- {filename}')

            if legacy_mode and pending_person_teams:
                for person_id, team_id in pending_person_teams:
                    db.session.execute(person_teams.insert().values(person_id=person_id, team_id=team_id))
                print(f'  Imported {len(pending_person_teams):>4} rows <- person_teams.csv (derived from legacy people.csv)')

            # Import association tables
            for filename, table, columns in ASSOC_TABLES:
                if legacy_mode and filename == 'person_teams.csv' and pending_person_teams:
                    continue
                path = os.path.join(input_dir, filename)
                if not os.path.exists(path):
                    print(f'  Skipped {filename} (not found)')
                    continue
                count = 0
                with open(path, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        values = {c: int(row[c]) for c in columns}
                        db.session.execute(table.insert().values(**values))
                        count += 1
                print(f'  Imported {count:>4} rows <- {filename}')

            db.session.commit()
            _verify_import(input_dir, legacy_mode=legacy_mode)
        except (ValueError, SQLAlchemyError) as exc:
            db.session.rollback()
            print(f'\nImport failed: {exc}')
            print(f'Current database was left unchanged. Backup is available at: {backup_dir}/')
            sys.exit(1)

    print(f'\nImport complete from: {input_dir}/')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('export', 'import'):
        print('Usage:')
        print('  python dbutil.py export [output_dir]')
        print('  python dbutil.py import [input_dir]')
        sys.exit(1)

    command = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else 'export'

    if command == 'export':
        print(f'Exporting database to {directory}/...\n')
        export_db(directory)
    else:
        if not os.path.isdir(directory):
            print(f'Error: directory "{directory}" not found')
            sys.exit(1)
        answer = input(f'This will REPLACE all data with contents of {directory}/. Continue? [y/N] ')
        if answer.lower() != 'y':
            print('Aborted.')
            sys.exit(0)
        print(f'\nImporting database from {directory}/...\n')
        import_db(directory)
