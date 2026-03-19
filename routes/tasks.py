import re
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, g, Response
from models import db, Task, TaskAssignment, Project, Person, Tag, StatusUpdate, TaskDependency, Milestone, Workspace
from datetime import date, datetime
from status_update_import import import_status_updates_from_text

bp = Blueprint('tasks', __name__)


@bp.url_value_preprocessor
def pull_workspace(endpoint, values):
    g.workspace_slug = values.pop('workspace_slug', None)
    g.workspace = Workspace.query.filter_by(slug=g.workspace_slug).first_or_404()


@bp.url_defaults
def inject_workspace(endpoint, values):
    if 'workspace_slug' not in values and hasattr(g, 'workspace_slug'):
        values['workspace_slug'] = g.workspace_slug


@bp.route('/tasks')
def list_tasks():
    status_filter = request.args.get('status', '')
    overdue = request.args.get('overdue', '')
    q = Task.query.filter_by(workspace_id=g.workspace.id)
    if overdue:
        q = q.filter(Task.end_date < date.today(), Task.status != 'done')
    elif status_filter:
        q = q.filter_by(status=status_filter)
    tasks = q.order_by(Task.end_date).all()
    return render_template('tasks/list.html', tasks=tasks,
                           status_filter=status_filter, overdue=overdue,
                           today=date.today())


@bp.route('/imports/status-updates', methods=['GET', 'POST'])
def import_status_updates():
    summary = None
    error = None
    preview_csv_text = None

    if request.method == 'POST':
        csv_text = None
        if request.form.get('commit_preview') == '1':
            csv_text = request.form.get('preview_csv_text', '')
            dry_run = False
        else:
            upload = request.files.get('csv_file')
            dry_run = request.form.get('dry_run') == '1'
            if not upload or not upload.filename:
                error = 'Choose a CSV file to import.'
            else:
                try:
                    csv_text = upload.stream.read().decode('utf-8-sig')
                except UnicodeDecodeError:
                    error = 'The uploaded file must be UTF-8 encoded.'

        if csv_text is not None and not error:
            try:
                summary = import_status_updates_from_text(
                    csv_text,
                    workspace_slug=g.workspace.slug,
                    dry_run=dry_run,
                )
                if dry_run:
                    preview_csv_text = csv_text
            except ValueError as exc:
                error = str(exc)

    return render_template('tasks/import_status_updates.html',
                           summary=summary, error=error,
                           preview_csv_text=preview_csv_text)


@bp.route('/imports/status-updates/parser-guide')
def download_status_update_parser_guide():
    guide = build_workspace_parser_guide(g.workspace)
    filename = f'{g.workspace.slug}-status-update-parser.md'
    return Response(
        guide,
        mimetype='text/markdown; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
        },
    )


def build_workspace_parser_guide(workspace: Workspace) -> str:
    base_guide = Path('STATUS_UPDATE_PARSER.md').read_text(encoding='utf-8').strip()
    projects = Project.query.filter_by(workspace_id=workspace.id).order_by(Project.name).all()
    people = Person.query.filter_by(workspace_id=workspace.id).order_by(Person.name).all()

    project_lines = []
    for project in projects:
        project_lines.append(f'- {project.name}')
        tasks = Task.query.filter_by(workspace_id=workspace.id, project_id=project.id).order_by(Task.title).all()
        if tasks:
            for task in tasks:
                project_lines.append(f'  - {task.title}')
        else:
            project_lines.append('  - (no tasks)')

    people_lines = [f'- {person.name}' for person in people] or ['- (no people)']
    projects_and_tasks = '\n'.join(project_lines)
    people_section = '\n'.join(people_lines)

    return (
        f'{base_guide}\n\n'
        '## Current Workspace Reference\n\n'
        f'- Workspace name: {workspace.name}\n'
        f'- Workspace slug: {workspace.slug}\n\n'
        '### Projects And Tasks\n\n'
        f'{projects_and_tasks}\n\n'
        '### People\n\n'
        f'{people_section}\n'
    )


@bp.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    if request.method == 'POST':
        task = Task(
            title=request.form['title'],
            description=request.form.get('description', ''),
            project_id=int(request.form['project_id']),
            workspace_id=g.workspace.id,
            start_date=date.fromisoformat(request.form['start_date']),
            end_date=date.fromisoformat(request.form['end_date']),
            status=request.form.get('status', 'todo'),
            priority=request.form.get('priority', 'medium'),
        )
        db.session.add(task)
        db.session.flush()  # get task.id

        # Handle assignees
        lead_id = request.form.get('lead_id')
        member_ids = request.form.getlist('member_ids')
        if lead_id:
            db.session.add(TaskAssignment(task_id=task.id, person_id=int(lead_id), is_lead=True))
        for mid in member_ids:
            if mid and mid != lead_id:
                db.session.add(TaskAssignment(task_id=task.id, person_id=int(mid), is_lead=False))

        # Handle tags
        tag_names = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        for name in tag_names:
            tag = Tag.query.filter_by(workspace_id=g.workspace.id, name=name).first()
            if not tag:
                tag = Tag(name=name, workspace_id=g.workspace.id)
                db.session.add(tag)
            task.tags.append(tag)

        # Handle dependencies
        dep_ids = request.form.getlist('dependencies')
        for dep_id in dep_ids:
            dep = TaskDependency(task_id=task.id, depends_on_id=int(dep_id))
            db.session.add(dep)

        # Handle milestones
        ms_names = request.form.getlist('milestone_names')
        ms_dates = request.form.getlist('milestone_dates')
        for name, ms_date in zip(ms_names, ms_dates):
            if name.strip() and ms_date:
                db.session.add(Milestone(task_id=task.id, name=name.strip(),
                                         date=date.fromisoformat(ms_date)))

        db.session.commit()
        return redirect(url_for('projects.detail', id=task.project_id))

    project_id = request.args.get('project_id', type=int)
    projects = Project.query.filter_by(workspace_id=g.workspace.id).order_by(Project.name).all()
    people = Person.query.filter_by(workspace_id=g.workspace.id).order_by(Person.name).all()
    # Available tasks for dependencies (from the same project)
    available_deps = []
    if project_id:
        available_deps = Task.query.filter_by(project_id=project_id, workspace_id=g.workspace.id).all()
    return render_template('tasks/form.html', task=None, projects=projects,
                           people=people, project_id=project_id,
                           available_deps=available_deps)


@bp.route('/tasks/<int:id>')
def detail(id):
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    return render_template('tasks/detail.html', task=task)


@bp.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description', '')
        task.start_date = date.fromisoformat(request.form['start_date'])
        task.end_date = date.fromisoformat(request.form['end_date'])
        task.status = request.form.get('status', 'todo')
        task.priority = request.form.get('priority', 'medium')

        # Update assignees
        TaskAssignment.query.filter_by(task_id=task.id).delete()
        lead_id = request.form.get('lead_id')
        member_ids = request.form.getlist('member_ids')
        if lead_id:
            db.session.add(TaskAssignment(task_id=task.id, person_id=int(lead_id), is_lead=True))
        for mid in member_ids:
            if mid and mid != lead_id:
                db.session.add(TaskAssignment(task_id=task.id, person_id=int(mid), is_lead=False))

        # Update tags
        task.tags.clear()
        tag_names = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        for name in tag_names:
            tag = Tag.query.filter_by(workspace_id=g.workspace.id, name=name).first()
            if not tag:
                tag = Tag(name=name, workspace_id=g.workspace.id)
                db.session.add(tag)
            task.tags.append(tag)

        # Update dependencies
        TaskDependency.query.filter_by(task_id=task.id).delete()
        dep_ids = request.form.getlist('dependencies')
        for dep_id in dep_ids:
            dep = TaskDependency(task_id=task.id, depends_on_id=int(dep_id))
            db.session.add(dep)

        # Update milestones
        Milestone.query.filter_by(task_id=task.id).delete()
        ms_names = request.form.getlist('milestone_names')
        ms_dates = request.form.getlist('milestone_dates')
        for name, ms_date in zip(ms_names, ms_dates):
            if name.strip() and ms_date:
                db.session.add(Milestone(task_id=task.id, name=name.strip(),
                                         date=date.fromisoformat(ms_date)))

        db.session.commit()
        return redirect(url_for('tasks.detail', id=task.id))

    projects = Project.query.filter_by(workspace_id=g.workspace.id).order_by(Project.name).all()
    people = Person.query.filter_by(workspace_id=g.workspace.id).order_by(Person.name).all()
    available_deps = Task.query.filter(
        Task.project_id == task.project_id, Task.id != task.id,
        Task.workspace_id == g.workspace.id
    ).all()
    return render_template('tasks/form.html', task=task, projects=projects,
                           people=people, project_id=task.project_id,
                           available_deps=available_deps)


@bp.route('/tasks/<int:id>/status', methods=['POST'])
def add_status_update(id):
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    content = request.form.get('content', '').strip()
    if content:
        update = StatusUpdate(task_id=task.id, content=content, created_at=datetime.now())
        db.session.add(update)
        db.session.flush()

        # Parse @mentions — match @"First Last" or @FirstLast
        mention_names = re.findall(r'@"([^"]+)"|@(\w+(?:\s\w+)?)', content)
        for groups in mention_names:
            name = groups[0] or groups[1]
            person = Person.query.filter_by(workspace_id=g.workspace.id).filter(
                Person.name.ilike(name.strip())
            ).first()
            if person and person not in update.mentions:
                update.mentions.append(person)

        db.session.commit()
    return redirect(url_for('tasks.detail', id=task.id))


@bp.route('/tasks/<int:id>/quick-update', methods=['POST'])
def quick_update(id):
    """AJAX endpoint for inline Gantt edits (start, end, status)."""
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    data = request.get_json()
    if 'start_date' in data:
        task.start_date = date.fromisoformat(data['start_date'])
    if 'end_date' in data:
        task.end_date = date.fromisoformat(data['end_date'])
    if 'status' in data and data['status'] in ('todo', 'in_progress', 'on_hold', 'done'):
        task.status = data['status']
    db.session.commit()
    return jsonify({'ok': True, 'progress': task.progress})


@bp.route('/tasks/<int:id>/milestones', methods=['POST'])
def add_milestone(id):
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    name = request.form.get('name', '').strip()
    ms_date = request.form.get('date', '')
    if name and ms_date:
        milestone = Milestone(task_id=task.id, name=name,
                              date=date.fromisoformat(ms_date))
        db.session.add(milestone)
        db.session.commit()
    return redirect(url_for('tasks.detail', id=task.id))


@bp.route('/milestones/<int:id>/update', methods=['POST'])
def update_milestone(id):
    milestone = Milestone.query.get_or_404(id)
    # Verify the milestone belongs to this workspace via its task
    if milestone.task.workspace_id != g.workspace.id:
        from flask import abort
        abort(404)
    name = request.form.get('name', '').strip()
    ms_date = request.form.get('date', '')
    status = request.form.get('status_override', '')
    if name:
        milestone.name = name
    if ms_date:
        milestone.date = date.fromisoformat(ms_date)
    milestone.status_override = status if status else None
    db.session.commit()
    return redirect(url_for('tasks.detail', id=milestone.task_id))


@bp.route('/milestones/<int:id>/delete', methods=['GET', 'POST'])
def delete_milestone(id):
    milestone = Milestone.query.get_or_404(id)
    if milestone.task.workspace_id != g.workspace.id:
        from flask import abort
        abort(404)
    task_id = milestone.task_id
    if request.method == 'POST':
        db.session.delete(milestone)
        db.session.commit()
        return redirect(url_for('tasks.detail', id=task_id))
    return render_template('confirm_delete.html',
                           title='Delete Milestone',
                           message=f'Are you sure you want to delete the milestone "{milestone.name}"?',
                           cancel_url=url_for('tasks.detail', id=task_id))


@bp.route('/tasks/<int:id>/delete', methods=['GET', 'POST'])
def delete_task(id):
    task = Task.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    project_id = task.project_id
    if request.method == 'POST':
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for('projects.detail', id=project_id))
    return render_template('confirm_delete.html',
                           title='Delete Task',
                           message=f'Are you sure you want to delete task "{task.title}"? This cannot be undone.',
                           cancel_url=url_for('tasks.detail', id=task.id))
