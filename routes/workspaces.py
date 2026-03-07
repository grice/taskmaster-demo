from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Workspace

bp = Blueprint('workspaces', __name__)


@bp.route('/workspaces/new', methods=['GET', 'POST'])
def new_workspace():
    if request.method == 'POST':
        name = request.form['name'].strip()
        slug = request.form['slug'].strip()
        workspace = Workspace(name=name, slug=slug)
        db.session.add(workspace)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('workspaces/form.html', workspace=None)


@bp.route('/workspaces/<slug>/edit', methods=['GET', 'POST'])
def edit_workspace(slug):
    workspace = Workspace.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        workspace.name = request.form['name'].strip()
        workspace.slug = request.form['slug'].strip()
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('workspaces/form.html', workspace=workspace)


@bp.route('/workspaces/<slug>/delete', methods=['GET', 'POST'])
def delete_workspace(slug):
    workspace = Workspace.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        db.session.delete(workspace)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('confirm_delete.html',
                           title='Delete Workspace',
                           message=f'Are you sure you want to delete workspace "{workspace.name}" and all its data? This cannot be undone.',
                           cancel_url=url_for('index'))
