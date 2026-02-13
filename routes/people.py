from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Person, Team

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
    return render_template('people/detail.html', person=person,
                           person_tasks=person_tasks,
                           tasks_by_project=tasks_by_project)


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


@bp.route('/people/<int:id>/delete', methods=['POST'])
def delete_person(id):
    person = Person.query.get_or_404(id)
    db.session.delete(person)
    db.session.commit()
    return redirect(url_for('people.list_people'))
