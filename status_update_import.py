"""Bulk import task status updates from CSV.

CSV columns:
    project_name,task_title,created_at,content,mentions,external_id

Required:
    project_name, task_title, content

Optional:
    created_at  ISO datetime, defaults to current UTC time
    mentions    comma-separated person names
    external_id stable source identifier used to deduplicate imports
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func

from models import db, Person, Project, StatusUpdate, Task, Workspace

REQUIRED_COLUMNS = {'project_name', 'task_title', 'content'}
OPTIONAL_COLUMNS = {'created_at', 'mentions', 'external_id'}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


@dataclass
class ImportRowResult:
    row_num: int
    status: str
    message: str


@dataclass
class ImportSummary:
    workspace_slug: str
    dry_run: bool
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[ImportRowResult] = field(default_factory=list)


def parse_created_at(raw: str, row_num: int) -> datetime:
    value = raw.strip()
    if not value:
        return datetime.utcnow()
    normalized = value.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        raise ValueError(f'row {row_num}: invalid created_at {raw!r}; expected ISO format')


def parse_mentions(raw: str, workspace_id: int) -> list[Person]:
    names = [part.strip() for part in raw.split(',') if part.strip()]
    if not names:
        return []

    people = []
    seen_ids = set()
    for name in names:
        person = Person.query.filter_by(workspace_id=workspace_id).filter(
            func.lower(Person.name) == name.lower()
        ).first()
        if person and person.id not in seen_ids:
            people.append(person)
            seen_ids.add(person.id)
    return people


def _validate_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise ValueError('CSV is missing a header row')
    header = {name.strip() for name in fieldnames if name}
    missing = REQUIRED_COLUMNS - header
    if missing:
        raise ValueError(f'CSV is missing required columns: {", ".join(sorted(missing))}')
    unknown = header - ALL_COLUMNS
    if unknown:
        raise ValueError(f'CSV has unsupported columns: {", ".join(sorted(unknown))}')


def _resolve_task(workspace_id: int, project_name: str, task_title: str) -> Task | None:
    return Task.query.join(Project, Task.project_id == Project.id).filter(
        Task.workspace_id == workspace_id,
        Project.workspace_id == workspace_id,
        func.lower(Project.name) == project_name.lower(),
        func.lower(Task.title) == task_title.lower(),
    ).first()


def import_status_updates_from_text(csv_text: str, workspace_slug: str, dry_run: bool = False) -> ImportSummary:
    workspace = Workspace.query.filter_by(slug=workspace_slug).first()
    if not workspace:
        raise ValueError(f'workspace {workspace_slug!r} not found')

    reader = csv.DictReader(io.StringIO(csv_text))
    _validate_columns(reader.fieldnames)

    summary = ImportSummary(workspace_slug=workspace_slug, dry_run=dry_run)

    for row_num, row in enumerate(reader, start=2):
        extra_values = row.get(None) or []
        if extra_values:
            summary.errors += 1
            summary.results.append(ImportRowResult(
                row_num=row_num,
                status='error',
                message=(
                    'Malformed CSV row with extra columns. '
                    'If mentions contains multiple people, keep them in one quoted field like '
                    '"Jane Smith,Sam Lee".'
                ),
            ))
            continue

        project_name = (row.get('project_name') or '').strip()
        task_title = (row.get('task_title') or '').strip()
        content = (row.get('content') or '').strip()
        raw_created_at = row.get('created_at') or ''
        mentions_raw = row.get('mentions') or ''
        external_id = (row.get('external_id') or '').strip() or None

        if not project_name or not task_title or not content:
            summary.errors += 1
            summary.results.append(ImportRowResult(
                row_num=row_num,
                status='error',
                message='Missing one of: project_name, task_title, content',
            ))
            continue

        if external_id:
            existing = StatusUpdate.query.join(Task, StatusUpdate.task_id == Task.id).filter(
                StatusUpdate.external_id == external_id,
                Task.workspace_id == workspace.id,
            ).first()
            if existing:
                summary.skipped += 1
                summary.results.append(ImportRowResult(
                    row_num=row_num,
                    status='skipped',
                    message=f'Duplicate external_id {external_id!r}',
                ))
                continue

        task = _resolve_task(workspace.id, project_name, task_title)
        if not task:
            summary.errors += 1
            summary.results.append(ImportRowResult(
                row_num=row_num,
                status='error',
                message=f'No task match for project {project_name!r} and task {task_title!r}',
            ))
            continue

        try:
            created_at = parse_created_at(raw_created_at, row_num)
        except ValueError as exc:
            summary.errors += 1
            summary.results.append(ImportRowResult(
                row_num=row_num,
                status='error',
                message=str(exc),
            ))
            continue

        mentions = parse_mentions(mentions_raw, workspace.id)
        missing_mentions = [part.strip() for part in mentions_raw.split(',') if part.strip() and all(
            person.name.lower() != part.strip().lower() for person in mentions
        )]

        update = StatusUpdate(
            task_id=task.id,
            content=content,
            created_at=created_at,
            external_id=external_id,
        )
        for person in mentions:
            update.mentions.append(person)

        summary.imported += 1
        msg = f'Prepared update for {project_name} / {task_title}'
        if missing_mentions:
            msg += f'; unmatched mentions: {", ".join(missing_mentions)}'
        summary.results.append(ImportRowResult(
            row_num=row_num,
            status='imported' if not dry_run else 'preview',
            message=msg,
        ))

        if not dry_run:
            db.session.add(update)

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    return summary
