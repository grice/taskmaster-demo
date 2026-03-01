from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Team

bp = Blueprint('teams', __name__)


@bp.route('/teams')
def list_teams():
    teams = Team.query.order_by(Team.name).all()
    return render_template('teams/list.html', teams=teams)


@bp.route('/teams/new', methods=['GET', 'POST'])
def new_team():
    if request.method == 'POST':
        team = Team(name=request.form['name'])
        db.session.add(team)
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('teams/form.html', team=None)


@bp.route('/teams/<int:id>/edit', methods=['GET', 'POST'])
def edit_team(id):
    team = Team.query.get_or_404(id)
    if request.method == 'POST':
        team.name = request.form['name']
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('teams/form.html', team=team)


@bp.route('/teams/<int:id>/delete', methods=['GET', 'POST'])
def delete_team(id):
    team = Team.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(team)
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('confirm_delete.html',
                           title='Delete Team',
                           message=f'Are you sure you want to delete team "{team.name}"?',
                           cancel_url=url_for('teams.list_teams'))
