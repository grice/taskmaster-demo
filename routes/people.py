from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Person, Team, StatusUpdate, Milestone, TaskAssignment
from datetime import date

bp = Blueprint('people', __name__)


@bp.route('/people')
def list_people():
    people = Person.query.order_by(Person.name).all()
    return render_template('people/list.html', people=people)


@bp.route('/people/new', methods=['GET', 'POST'])
def new_person():
    if request.method == 'POST':
        person = Person(
            name=request.form['name'],
            email=request.form.get('email', ''),
            team_id=int(request.form['team_id']) if request.form.get('team_id') else None,
        )
        db.session.add(person)
        db.session.commit()
        return redirect(url_for('people.list_people'))
    teams = Team.query.order_by(Team.name).all()
    return render_template('people/form.html', person=None, teams=teams)


@bp.route('/people/<int:id>')
def detail(id):
    person = Person.query.get_or_404(id)
    # Get all tasks this person is assigned to
    person_tasks = [a.task for a in person.assignments]
    # Group tasks by project
    tasks_by_project = {}
    for task in person_tasks:
        proj = task.project
        if proj.id not in tasks_by_project:
            tasks_by_project[proj.id] = {'project': proj, 'tasks': []}
        tasks_by_project[proj.id]['tasks'].append(task)
    # Get all status updates that mention this person, newest first
    mentioned_updates = StatusUpdate.query.filter(
        StatusUpdate.mentions.any(id=person.id)
    ).order_by(StatusUpdate.created_at.desc()).all()

    # Get upcoming milestones for tasks this person is assigned to
    task_ids = [t.id for t in person_tasks]
    upcoming_milestones = Milestone.query.filter(
        Milestone.task_id.in_(task_ids),
        Milestone.date >= date.today()
    ).order_by(Milestone.date).all() if task_ids else []

    return render_template('people/detail.html', person=person,
                           person_tasks=person_tasks,
                           tasks_by_project=tasks_by_project,
                           mentioned_updates=mentioned_updates,
                           upcoming_milestones=upcoming_milestones)


@bp.route('/people/<int:id>/edit', methods=['GET', 'POST'])
def edit_person(id):
    person = Person.query.get_or_404(id)
    if request.method == 'POST':
        person.name = request.form['name']
        person.email = request.form.get('email', '')
        person.team_id = int(request.form['team_id']) if request.form.get('team_id') else None
        db.session.commit()
        return redirect(url_for('people.detail', id=person.id))
    teams = Team.query.order_by(Team.name).all()
    return render_template('people/form.html', person=person, teams=teams)


@bp.route('/people/search.json')
def search_json():
    q = request.args.get('q', '').strip()
    query = Person.query.order_by(Person.name)
    if q:
        query = query.filter(Person.name.ilike(f'%{q}%'))
    people = query.limit(10).all()
    return jsonify([{'id': p.id, 'name': p.name} for p in people])


@bp.route('/people/<int:id>/delete', methods=['POST'])
def delete_person(id):
    person = Person.query.get_or_404(id)
    db.session.delete(person)
    db.session.commit()
    return redirect(url_for('people.list_people'))
