# Tideline

A Flask app for tracking projects across teams. Tideline supports multiple isolated workspaces, interactive Gantt charts, people workload views, milestones, @mention status updates, and more.

## Setup

### 1. Create the conda environment

```bash
conda env create -f environment.yml
conda activate taskmaster
```

### 2. Initialize the database

Seed with sample data (creates two workspaces: engineering and marketing):

```bash
python seed.py
flask db stamp head
```

Or start with an empty database — tables are created automatically when the app starts.

### 3. Run the app

```bash
flask --app app run
```

Open http://127.0.0.1:5000 in your browser. You'll land on the Tideline workspace selector.

## Database Migrations

Schema changes are managed with Flask-Migrate. After pulling new code with model changes:

```bash
flask db upgrade
```

To generate a migration after changing `models.py`:

```bash
flask db migrate -m "describe the change"
flask db upgrade
```

## Database Export / Import

Use `dbutil.py` to back up and restore data as CSV files.

### Export

```bash
python dbutil.py export              # saves to ./export/
python dbutil.py export mybackup     # saves to ./mybackup/
```

This creates one CSV file per table (teams, people, projects, tasks, etc.).

### Import

```bash
python dbutil.py import              # reads from ./export/
python dbutil.py import mybackup     # reads from ./mybackup/
```

Import replaces all existing data. You will be prompted to confirm before proceeding.

## Features

### Workspaces
- **Multiple workspaces** — each workspace is fully isolated with its own projects, tasks, people, and teams. URL structure: `/w/<slug>/`.
- **Workspace landing page** — lists all workspaces at `/`; create, edit, or open any workspace from there.

### Dashboard
- **Stats overview** — active project count, total tasks, in-progress tasks, and overdue count at a glance.
- **Multi-project Gantt** — all active projects rendered as a single timeline on the dashboard, color-coded by project with a legend. Zoom between Week and Month views. Today's date marked with a red vertical line.
- **Task breakdown** — todo/in-progress/done counts with a visual workload bar.
- **Recent projects** and team roster summary.

### Projects & Tasks
- **Project Gantt view** — interactive per-project timeline with drag-to-resize bars, dependency arrows, and click-to-edit popups. Zoom between Day/Week/Month/Year. View mode auto-selected based on project span. Today's date marked with a red vertical line.
- **Milestones** — add multiple milestone markers per task with name, date, and status (auto-calculated or manual override). Displayed as color-coded diamonds on the Gantt chart. Upcoming milestones surface on project and person detail pages.
- **Multi-assignee tasks** — assign multiple people to a task with one designated as lead.
- **Tags, priorities, dependencies** — categorize tasks with free-form tags, priority levels (low/medium/high/critical), and blocked-by relationships.
- **Status updates** — append timestamped updates to any task with `@"First Last"` mention autocomplete that links to person pages. File URLs (SharePoint, etc.) automatically condense to show an icon + filename.

### People & Teams
- **People workload view** — each person's tasks across all projects shown with status-colored workload bars, a personal timeline, upcoming milestones, and task statistics.
- **Teams** — group people into teams; team membership shown on person and team detail pages.

### General
- **Dark mode** — toggle via the moon/sun icon in the navbar. Preference persists across sessions via localStorage.
- **Database export/import** — back up and restore all data (including milestones) as CSV files with automatic backup before import.
