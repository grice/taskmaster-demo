"""Bulk workspace import from CSV files.

Usage:
    python workspace_import.py <workspace_name> [input_dir]

    input_dir defaults to ./import
    Reads: <input_dir>/plan.csv (required), <input_dir>/people.csv (optional)
    Slug auto-derived: lowercase, spaces/punctuation → hyphens (e.g. "Eng Team" → "eng-team")
"""

import sys
import csv
import re
from pathlib import Path
from datetime import date

from app import create_app
from models import db, Workspace, Team, Person, Tag, Project, Task, TaskAssignment, TaskDependency


def fail(message: str):
    raise SystemExit(message)


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s


def parse_date(s: str, field: str, row_num: int) -> date:
    s = s.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        fail(f"Error: invalid date {s!r} in {field} (row {row_num})")


def load_people_csv(path: Path, workspace_id: int) -> tuple[dict, dict]:
    """Returns (team_by_name, person_by_name) dicts with created DB objects."""
    team_by_name: dict[str, Team] = {}
    person_by_name: dict[str, Person] = {}

    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # First pass: teams
    for i, row in enumerate(rows, start=2):
        rtype = row.get('type', '').strip().lower()
        if rtype != 'team':
            continue
        name = row['name'].strip()
        if not name:
            fail(f"Error: empty team name at people.csv row {i}")
        if name in team_by_name:
            fail(f"Error: duplicate team name {name!r} at people.csv row {i}")
        team = Team(name=name, workspace_id=workspace_id)
        db.session.add(team)
        team_by_name[name] = team

    db.session.flush()

    # Second pass: people
    for i, row in enumerate(rows, start=2):
        rtype = row.get('type', '').strip().lower()
        if rtype != 'person':
            continue
        name = row['name'].strip()
        if not name:
            fail(f"Error: empty person name at people.csv row {i}")
        if name in person_by_name:
            fail(f"Error: duplicate person name {name!r} at people.csv row {i}")
        email = row.get('email', '').strip() or None
        person = Person(name=name, email=email, workspace_id=workspace_id)
        db.session.add(person)
        person_by_name[name] = person

    db.session.flush()

    # Third pass: assign people to teams
    for i, row in enumerate(rows, start=2):
        rtype = row.get('type', '').strip().lower()
        if rtype != 'person':
            continue
        name = row['name'].strip()
        teams_str = row.get('teams', '').strip()
        if not teams_str:
            continue
        for tname in [t.strip() for t in teams_str.split(',') if t.strip()]:
            if tname not in team_by_name:
                print(f"  Warning: unknown team {tname!r} for person {name!r} (people.csv row {i}), skipping")
                continue
            team_by_name[tname].members.append(person_by_name[name])

    db.session.flush()
    return team_by_name, person_by_name


def load_plan_csv(path: Path, workspace_id: int, person_by_name: dict) -> tuple[dict, dict, dict]:
    """Parse plan.csv; create projects, tags, tasks, assignments, dependencies.

    Returns (project_by_name, tag_by_name, task_by_name).
    """
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # ── Collect raw data in a single pass ────────────────────────────────────
    project_rows: list[dict] = []
    task_rows: list[dict] = []
    current_project_name: str | None = None

    for i, row in enumerate(rows, start=2):
        rtype = row.get('type', '').strip().lower()
        if rtype == 'project':
            name = row['name'].strip()
            if not name:
                fail(f"Error: empty project name at plan.csv row {i}")
            if any(pr['name'] == name for pr in project_rows):
                fail(f"Error: duplicate project name {name!r} at plan.csv row {i}")
            project_rows.append({'row': i, 'name': name,
                                  'description': row.get('description', '').strip(),
                                  'start_date': row.get('start_date', '').strip(),
                                  'end_date': row.get('end_date', '').strip(),
                                  'status': row.get('status', '').strip() or 'active'})
            current_project_name = name

        elif rtype == 'task':
            if current_project_name is None:
                fail(f"Error: task at plan.csv row {i} has no preceding project row")
            name = row['name'].strip()
            if not name:
                fail(f"Error: empty task name at plan.csv row {i}")
            if any(tr['name'] == name for tr in task_rows):
                fail(f"Error: duplicate task name {name!r} at plan.csv row {i}; task titles must be unique within an import so dependencies are unambiguous")
            start_str = row.get('start_date', '').strip()
            end_str = row.get('end_date', '').strip()
            if not start_str or not end_str:
                fail(f"Error: task {name!r} (row {i}) is missing start_date or end_date")
            task_rows.append({
                'row': i,
                'name': name,
                'project': current_project_name,
                'description': row.get('description', '').strip(),
                'start_date': start_str,
                'end_date': end_str,
                'status': row.get('status', '').strip() or 'todo',
                'priority': row.get('priority', '').strip() or 'medium',
                'assignees': row.get('assignees', '').strip(),
                'tags': row.get('tags', '').strip(),
                'depends_on': row.get('depends_on', '').strip(),
            })
        else:
            fail(f"Error: unknown type {row.get('type')!r} at plan.csv row {i}")

    # ── Create projects ───────────────────────────────────────────────────────
    project_by_name: dict[str, Project] = {}
    for pr in project_rows:
        status = pr['status'] if pr['status'] in ('active', 'completed', 'on_hold') else 'active'
        proj = Project(
            name=pr['name'],
            description=pr['description'] or None,
            start_date=parse_date(pr['start_date'], 'start_date', pr['row']),
            end_date=parse_date(pr['end_date'], 'end_date', pr['row']),
            status=status,
            workspace_id=workspace_id,
        )
        db.session.add(proj)
        project_by_name[pr['name']] = proj

    db.session.flush()

    # ── Collect and create tags ───────────────────────────────────────────────
    all_tag_names: set[str] = set()
    for tr in task_rows:
        if tr['tags']:
            for t in tr['tags'].split(','):
                t = t.strip()
                if t:
                    all_tag_names.add(t)

    tag_by_name: dict[str, Tag] = {}
    for tname in sorted(all_tag_names):
        tag = Tag(name=tname, workspace_id=workspace_id)
        db.session.add(tag)
        tag_by_name[tname] = tag

    db.session.flush()

    # ── Create tasks ──────────────────────────────────────────────────────────
    task_by_name: dict[str, Task] = {}
    # Track (task_raw, [dep_names]) for dependency wiring later
    task_deps_pending: list[tuple[Task, list[str], int]] = []

    for tr in task_rows:
        proj = project_by_name[tr['project']]
        status = tr['status'] if tr['status'] in ('todo', 'in_progress', 'on_hold', 'done') else 'todo'
        priority = tr['priority'] if tr['priority'] in ('low', 'medium', 'high', 'critical') else 'medium'

        task = Task(
            title=tr['name'],
            description=tr['description'] or None,
            project_id=proj.id,
            workspace_id=workspace_id,
            start_date=parse_date(tr['start_date'], 'start_date', tr['row']),
            end_date=parse_date(tr['end_date'], 'end_date', tr['row']),
            status=status,
            priority=priority,
        )
        db.session.add(task)
        task_by_name[tr['name']] = task

        # Tags
        if tr['tags']:
            for tname in [t.strip() for t in tr['tags'].split(',') if t.strip()]:
                if tname in tag_by_name:
                    task.tags.append(tag_by_name[tname])

        # Dependencies (deferred — tasks may reference later rows by name)
        if tr['depends_on']:
            dep_names = [d.strip() for d in tr['depends_on'].split(',') if d.strip()]
            task_deps_pending.append((task, dep_names, tr['row']))

        # Assignments
        if tr['assignees']:
            for raw in [a.strip() for a in tr['assignees'].split(',') if a.strip()]:
                is_lead = raw.startswith('*')
                pname = raw.lstrip('*').strip()
                if pname not in person_by_name:
                    print(f"  Warning: unknown person {pname!r} in assignees (plan.csv row {tr['row']}), skipping")
                    continue
                db.session.add(TaskAssignment(
                    task=task,
                    person=person_by_name[pname],
                    is_lead=is_lead,
                ))

    db.session.flush()

    # ── Wire up dependencies now that all tasks exist ─────────────────────────
    dep_count = 0
    for task, dep_names, row_num in task_deps_pending:
        for dname in dep_names:
            if dname not in task_by_name:
                print(f"  Warning: unknown task {dname!r} in depends_on (plan.csv row {row_num}), skipping")
                continue
            db.session.add(TaskDependency(
                task_id=task.id,
                depends_on_id=task_by_name[dname].id,
            ))
            dep_count += 1

    db.session.flush()
    return project_by_name, tag_by_name, task_by_name


def main():
    if len(sys.argv) < 2:
        fail("Usage: python workspace_import.py <workspace_name> [input_dir]")

    workspace_name = sys.argv[1]
    input_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('import')

    plan_path = input_dir / 'plan.csv'
    people_path = input_dir / 'people.csv'

    if not plan_path.exists():
        fail(f"Error: {plan_path} not found")

    slug = slugify(workspace_name)

    app = create_app()
    with app.app_context():
        try:
            # Abort if workspace slug already taken
            if Workspace.query.filter_by(slug=slug).first():
                fail(f"Error: workspace with slug {slug!r} already exists")

            # Create workspace
            ws = Workspace(name=workspace_name, slug=slug)
            db.session.add(ws)
            db.session.flush()

            # People + teams (optional)
            team_by_name: dict = {}
            person_by_name: dict = {}
            if people_path.exists():
                team_by_name, person_by_name = load_people_csv(people_path, ws.id)
            else:
                print(f"  (no people.csv found in {input_dir}, skipping teams/people)")

            # Plan
            project_by_name, tag_by_name, task_by_name = load_plan_csv(
                plan_path, ws.id, person_by_name
            )

            db.session.commit()

            # Count assignments and dependencies from task objects
            assign_count = sum(len(t.assignments) for t in task_by_name.values())
            dep_count = TaskDependency.query.join(
                Task, TaskDependency.task_id == Task.id
            ).filter(Task.workspace_id == ws.id).count()

            print(f"Created workspace: {workspace_name} ({slug})")
            print(f"  {len(team_by_name)} teams, {len(person_by_name)} people")
            print(f"  {len(project_by_name)} projects, {len(task_by_name)} tasks, "
                  f"{len(tag_by_name)} tags, {assign_count} assignments, {dep_count} dependencies")
            print("Done.")

        except SystemExit:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            fail(f"Error: {e}")


if __name__ == '__main__':
    main()
