# Taskmaster

A Flask app for tracking projects across teams. Two main views: a Gantt-style project timeline and a people-centric workload view.

## Setup

### 1. Create the conda environment

```bash
conda env create -f environment.yml
conda activate taskmaster
```

### 2. Initialize the database

Seed with sample data:

```bash
python seed.py
```

Or start with an empty database — tables are created automatically when the app starts.

### 3. Run the app

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Database Migrations

Schema changes are managed with Flask-Migrate. After pulling new code with model changes:

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

- **Project Gantt view** — interactive timeline with drag-to-resize, dependency arrows, and click-to-edit popups. Zoom between Day/Week/Month/Year.
- **People workload view** — see each person's tasks across all projects, with workload bars and a timeline.
- **Multi-assignee tasks** — assign multiple people to a task with one designated as lead.
- **Status updates** — append updates to any task with `@"First Last"` mentions that link to person pages.
- **Tags, priorities, dependencies** — categorize tasks with free-form tags, priority levels, and blocked-by relationships.
