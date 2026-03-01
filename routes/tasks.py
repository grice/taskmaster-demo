import re
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Task, TaskAssignment, Project, Person, Tag, StatusUpdate, TaskDependency, Milestone
from datetime import date

bp = Blueprint('tasks', __name__)


@bp.route('/tasks')
def list_tasks():
    status_filter = request.args.get('status', '')
    overdue = request.args.get('overdue', '')
    q = Task.query
    if overdue:
        q = q.filter(Task.end_date < date.today(), Task.status != 'done')
    elif status_filter:
        q = q.filter_by(status=status_filter)
    tasks = q.order_by(Task.end_date).all()
    return render_template('tasks/list.html', tasks=tasks,
                           status_filter=status_filter, overdue=overdue,
                           today=date.today())


@bp.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    if request.method == 'POST':
        task = Task(
            title=request.form['title'],
            description=request.form.get('description', ''),
            project_id=int(request.form['project_id']),
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
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
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
    projects = Project.query.order_by(Project.name).all()
    people = Person.query.order_by(Person.name).all()
    # Available tasks for dependencies (from the same project)
    available_deps = []
    if project_id:
        available_deps = Task.query.filter_by(project_id=project_id).all()
    return render_template('tasks/form.html', task=None, projects=projects,
                           people=people, project_id=project_id,
                           available_deps=available_deps)


@bp.route('/tasks/<int:id>')
def detail(id):
    task = Task.query.get_or_404(id)
    return render_template('tasks/detail.html', task=task)


@bp.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    task = Task.query.get_or_404(id)
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
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
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

    projects = Project.query.order_by(Project.name).all()
    people = Person.query.order_by(Person.name).all()
    available_deps = Task.query.filter(
        Task.project_id == task.project_id, Task.id != task.id
    ).all()
    return render_template('tasks/form.html', task=task, projects=projects,
                           people=people, project_id=task.project_id,
                           available_deps=available_deps)


@bp.route('/tasks/<int:id>/status', methods=['POST'])
def add_status_update(id):
    task = Task.query.get_or_404(id)
    content = request.form.get('content', '').strip()
    if content:
        update = StatusUpdate(task_id=task.id, content=content)
        db.session.add(update)
        db.session.flush()

        # Parse @mentions — match @"First Last" or @FirstLast
        mention_names = re.findall(r'@"([^"]+)"|@(\w+(?:\s\w+)?)', content)
        for groups in mention_names:
            name = groups[0] or groups[1]
            person = Person.query.filter(Person.name.ilike(name.strip())).first()
            if person and person not in update.mentions:
                update.mentions.append(person)

        db.session.commit()
    return redirect(url_for('tasks.detail', id=task.id))


@bp.route('/tasks/<int:id>/quick-update', methods=['POST'])
def quick_update(id):
    """AJAX endpoint for inline Gantt edits (start, end, status)."""
    task = Task.query.get_or_404(id)
    data = request.get_json()
    if 'start_date' in data:
        task.start_date = date.fromisoformat(data['start_date'])
    if 'end_date' in data:
        task.end_date = date.fromisoformat(data['end_date'])
    if 'status' in data and data['status'] in ('todo', 'in_progress', 'done'):
        task.status = data['status']
    db.session.commit()
    return jsonify({'ok': True, 'progress': task.progress})


@bp.route('/tasks/<int:id>/milestones', methods=['POST'])
def add_milestone(id):
    task = Task.query.get_or_404(id)
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
    task = Task.query.get_or_404(id)
    project_id = task.project_id
    if request.method == 'POST':
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for('projects.detail', id=project_id))
    return render_template('confirm_delete.html',
                           title='Delete Task',
                           message=f'Are you sure you want to delete task "{task.title}"? This cannot be undone.',
                           cancel_url=url_for('tasks.detail', id=task.id))
