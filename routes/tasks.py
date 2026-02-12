from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Task, Project, Person, Tag, StatusUpdate, TaskDependency
from datetime import date

bp = Blueprint('tasks', __name__)


@bp.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    if request.method == 'POST':
        task = Task(
            title=request.form['title'],
            description=request.form.get('description', ''),
            project_id=int(request.form['project_id']),
            assignee_id=int(request.form['assignee_id']) if request.form.get('assignee_id') else None,
            start_date=date.fromisoformat(request.form['start_date']),
            end_date=date.fromisoformat(request.form['end_date']),
            status=request.form.get('status', 'todo'),
            priority=request.form.get('priority', 'medium'),
        )
        db.session.add(task)
        db.session.flush()  # get task.id

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
        task.assignee_id = int(request.form['assignee_id']) if request.form.get('assignee_id') else None
        task.start_date = date.fromisoformat(request.form['start_date'])
        task.end_date = date.fromisoformat(request.form['end_date'])
        task.status = request.form.get('status', 'todo')
        task.priority = request.form.get('priority', 'medium')

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


@bp.route('/tasks/<int:id>/delete', methods=['POST'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('projects.detail', id=project_id))
