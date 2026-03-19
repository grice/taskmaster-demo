"""CLI for bulk importing task status updates from CSV."""

from __future__ import annotations

import sys
from pathlib import Path

from app import create_app
from status_update_import import import_status_updates_from_text


def main() -> int:
    if len(sys.argv) < 3:
        print('Usage: python import_status_updates.py <workspace_slug> <csv_path> [--dry-run]')
        return 1

    workspace_slug = sys.argv[1]
    csv_path = Path(sys.argv[2])
    dry_run = '--dry-run' in sys.argv[3:]

    if not csv_path.exists():
        print(f'Error: {csv_path} not found')
        return 1

    app = create_app()
    with app.app_context():
        summary = import_status_updates_from_text(
            csv_path.read_text(encoding='utf-8'),
            workspace_slug=workspace_slug,
            dry_run=dry_run,
        )

    print(
        f'Workspace: {summary.workspace_slug}\n'
        f'Mode: {"dry-run" if summary.dry_run else "import"}\n'
        f'Imported: {summary.imported}\n'
        f'Skipped: {summary.skipped}\n'
        f'Errors: {summary.errors}\n'
    )
    for result in summary.results:
        print(f'row {result.row_num}: {result.status} - {result.message}')

    return 0 if summary.errors == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
