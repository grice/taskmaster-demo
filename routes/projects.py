from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Project, Task, StatusUpdate, Milestone
from datetime import date

bp = Blueprint('projects', __name__)


@bp.route('/projects')
def list_projects():
    projects = Project.query.order_by(Project.start_date.desc()).all()
    return render_template('projects/list.html', projects=projects)


@bp.route('/projects/new', methods=['GET', 'POST'])
def new_project():
    if request.method == 'POST':
        from datetime import date
        project = Project(
            name=request.form['name'],
            description=request.form.get('description', ''),
            start_date=date.fromisoformat(request.form['start_date']) if request.form.get('start_date') else None,
            end_date=date.fromisoformat(request.form['end_date']) if request.form.get('end_date') else None,
            status=request.form.get('status', 'active'),
        )
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('projects.detail', id=project.id))
    return render_template('projects/form.html', project=None)


@bp.route('/projects/<int:id>')
def detail(id):
    project = Project.query.get_or_404(id)
    # Collect all status updates across this project's tasks, newest first
    task_ids = [t.id for t in project.tasks]
    all_updates = StatusUpdate.query.filter(
        StatusUpdate.task_id.in_(task_ids)
    ).order_by(StatusUpdate.created_at.desc()).all() if task_ids else []
    upcoming_milestones = Milestone.query.filter(
        Milestone.task_id.in_(task_ids),
        Milestone.date >= date.today()
    ).order_by(Milestone.date).all() if task_ids else []
    return render_template('projects/detail.html', project=project,
                           all_updates=all_updates,
                           upcoming_milestones=upcoming_milestones)


@bp.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    if request.method == 'POST':
        from datetime import date
        project.name = request.form['name']
        project.description = request.form.get('description', '')
        project.start_date = date.fromisoformat(request.form['start_date']) if request.form.get('start_date') else None
        project.end_date = date.fromisoformat(request.form['end_date']) if request.form.get('end_date') else None
        project.status = request.form.get('status', 'active')
        db.session.commit()
        return redirect(url_for('projects.detail', id=project.id))
    return render_template('projects/form.html', project=project)


@bp.route('/projects/<int:id>/delete', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('projects.list_projects'))


@bp.route('/projects/<int:id>/gantt-data')
def gantt_data(id):
    project = Project.query.get_or_404(id)
    tasks = []
    for task in project.tasks:
        dep_ids = ','.join(f'task-{d.id}' for d in task.dependencies)
        lead = task.lead
        assignee_names = []
        for a in task.assignments:
            name = a.person.name
            if a.is_lead:
                name += ' (lead)'
            assignee_names.append(name)
        milestones = [{'name': ms.name, 'date': ms.date.isoformat(),
                       'status': ms.computed_status} for ms in task.milestones]
        tasks.append({
            'id': f'task-{task.id}',
            'name': task.title,
            'start': task.start_date.isoformat(),
            'end': task.end_date.isoformat(),
            'progress': task.progress,
            'dependencies': dep_ids,
            'custom_class': f'status-{task.status} priority-{task.priority}',
            'assignees': ', '.join(assignee_names) if assignee_names else 'Unassigned',
            'milestones': milestones,
        })
    return jsonify(tasks)
