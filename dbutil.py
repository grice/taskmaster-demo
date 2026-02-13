"""Export and import the Taskmaster database to/from CSV files.

Usage:
    python dbutil.py export [output_dir]   # default: ./export
    python dbutil.py import [input_dir]    # default: ./export
"""
import csv
import os
import sys
from datetime import date, datetime
from app import create_app
from models import (db, Team, Person, Project, Task, TaskAssignment,
                    TaskDependency, Tag, StatusUpdate, task_tags,
                    status_update_mentions)

app = create_app()

# Table export order (respects foreign key dependencies)
TABLES = [
    ('teams.csv', Team, ['id', 'name']),
    ('people.csv', Person, ['id', 'name', 'email', 'team_id']),
    ('projects.csv', Project, ['id', 'name', 'description', 'start_date', 'end_date', 'status']),
    ('tags.csv', Tag, ['id', 'name']),
    ('tasks.csv', Task, ['id', 'title', 'description', 'project_id', 'start_date', 'end_date', 'status', 'priority']),
    ('task_assignments.csv', TaskAssignment, ['id', 'task_id', 'person_id', 'is_lead']),
    ('task_dependencies.csv', TaskDependency, ['id', 'task_id', 'depends_on_id']),
    ('status_updates.csv', StatusUpdate, ['id', 'task_id', 'content', 'created_at']),
]

# Many-to-many association tables
ASSOC_TABLES = [
    ('task_tags.csv', task_tags, ['task_id', 'tag_id']),
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


def import_db(input_dir):
    with app.app_context():
        # Auto-backup before overwriting
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backup_{timestamp}'
        print(f'Backing up current database to {backup_dir}/...\n')
        export_db(backup_dir)
        print(f'\nBackup complete. Proceeding with import...\n')

        # Clear all data in reverse order to respect foreign keys
        db.session.execute(status_update_mentions.delete())
        db.session.execute(task_tags.delete())
        for filename, model, columns in reversed(TABLES):
            db.session.query(model).delete()
        db.session.commit()

        for filename, model, columns in TABLES:
            path = os.path.join(input_dir, filename)
            if not os.path.exists(path):
                print(f'  Skipped {filename} (not found)')
                continue
            count = 0
            with open(path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert empty strings to None for nullable fields
                    for key in row:
                        if row[key] == '':
                            row[key] = None
                    # Convert types
                    if 'id' in row and row['id'] is not None:
                        row['id'] = int(row['id'])
                    for col in columns:
                        if col.endswith('_id') and row.get(col) is not None:
                            row[col] = int(row[col])
                        # Date fields (YYYY-MM-DD)
                        if col.endswith('_date') and col != 'created_at' and row.get(col) is not None:
                            row[col] = date.fromisoformat(row[col])
                        # Datetime fields
                        if col == 'created_at' and row.get(col) is not None:
                            row[col] = datetime.fromisoformat(row[col])
                    if 'is_lead' in row and row['is_lead'] is not None:
                        row['is_lead'] = row['is_lead'] in ('True', 'true', '1')
                    obj = model(**{c: row[c] for c in columns})
                    db.session.add(obj)
                    count += 1
            db.session.flush()
            print(f'  Imported {count:>4} rows <- {filename}')

        # Import association tables
        for filename, table, columns in ASSOC_TABLES:
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
