from flask import Blueprint, render_template, request, redirect, url_for, g
from models import db, Team, Workspace

bp = Blueprint('teams', __name__)


@bp.url_value_preprocessor
def pull_workspace(endpoint, values):
    g.workspace_slug = values.pop('workspace_slug', None)
    g.workspace = Workspace.query.filter_by(slug=g.workspace_slug).first_or_404()


@bp.url_defaults
def inject_workspace(endpoint, values):
    if 'workspace_slug' not in values and hasattr(g, 'workspace_slug'):
        values['workspace_slug'] = g.workspace_slug


@bp.route('/teams')
def list_teams():
    teams = Team.query.filter_by(workspace_id=g.workspace.id).order_by(Team.name).all()
    return render_template('teams/list.html', teams=teams)


@bp.route('/teams/new', methods=['GET', 'POST'])
def new_team():
    if request.method == 'POST':
        team = Team(name=request.form['name'], workspace_id=g.workspace.id)
        db.session.add(team)
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('teams/form.html', team=None)


@bp.route('/teams/<int:id>/edit', methods=['GET', 'POST'])
def edit_team(id):
    team = Team.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    if request.method == 'POST':
        team.name = request.form['name']
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('teams/form.html', team=team)


@bp.route('/teams/<int:id>/delete', methods=['GET', 'POST'])
def delete_team(id):
    team = Team.query.filter_by(id=id, workspace_id=g.workspace.id).first_or_404()
    if request.method == 'POST':
        db.session.delete(team)
        db.session.commit()
        return redirect(url_for('teams.list_teams'))
    return render_template('confirm_delete.html',
                           title='Delete Team',
                           message=f'Are you sure you want to delete team "{team.name}"?',
                           cancel_url=url_for('teams.list_teams'))
