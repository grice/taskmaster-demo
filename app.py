import os
import re
from markupsafe import Markup, escape
from flask import Flask, render_template, g
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from models import db, Project, Task, Person, Team, Milestone, Workspace
from flask import url_for as flask_url_for
from routes import register_blueprints
from datetime import date

migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmaster.db'
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['BRAND_NAME'] = 'Tideline'
    app.config['BRAND_TAGLINE'] = 'Chart work across teams.'

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()
        ensure_compatible_schema()

    register_blueprints(app)

    @app.context_processor
    def inject_branding():
        return {
            'brand_name': app.config['BRAND_NAME'],
            'brand_tagline': app.config['BRAND_TAGLINE'],
        }

    @app.after_request
    def add_no_cache_headers(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.template_filter('render_mentions')
    def render_mentions(content):
        """Replace @"Name" with clickable links, and URLs with hyperlinks."""
        from urllib.parse import urlparse, unquote
        FILE_EXTS = {'.doc', '.docx', '.pdf', '.txt', '.rtf', '.odt',
                     '.xls', '.xlsx', '.csv', '.ods',
                     '.ppt', '.pptx', '.odp',
                     '.png', '.jpg', '.jpeg', '.gif', '.svg',
                     '.zip', '.tar', '.gz', '.7z',
                     '.py', '.js', '.html', '.css', '.json', '.md'}

        def replace_url(m):
            raw_url = m.group(0)
            safe_url = escape(raw_url)
            try:
                parsed = urlparse(raw_url)
                path = unquote(parsed.path)
                filename = path.rsplit('/', 1)[-1] if '/' in path else path
                ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext in FILE_EXTS and filename:
                    safe_name = escape(filename)
                    return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="file-link">{safe_name}</a>'
            except Exception:
                pass
            return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>'
        result = re.sub(r'https?://[^\s<>"]+', replace_url, content)

        def replace_mention(m):
            name = m.group(1) or m.group(2)
            safe_name = escape(name.strip())
            workspace = getattr(g, 'workspace', None)
            if workspace:
                person = Person.query.filter_by(workspace_id=workspace.id).filter(
                    Person.name.ilike(name.strip())
                ).first()
            else:
                person = Person.query.filter(Person.name.ilike(name.strip())).first()
            if person:
                url = flask_url_for('people.detail', id=person.id,
                                    workspace_slug=getattr(g, 'workspace_slug', None))
                return f'<a href="{url}" class="mention-tag text-decoration-none">@{safe_name}</a>'
            return f'<span class="mention-tag">@{safe_name}</span>'
        result = re.sub(r'@"([^"]+)"|@(\w+(?:\s\w+)?)', replace_mention, result)
        parts = re.split(r'(<[^>]+>)', result)
        for i, part in enumerate(parts):
            if not part.startswith('<'):
                parts[i] = str(escape(part))
        return Markup(''.join(parts))

    @app.route('/')
    def index():
        workspaces = Workspace.query.order_by(Workspace.name).all()
        return render_template('landing.html', workspaces=workspaces)

    @app.route('/w/<workspace_slug>/')
    def workspace_dashboard(workspace_slug):
        workspace = Workspace.query.filter_by(slug=workspace_slug).first_or_404()
        g.workspace = workspace
        g.workspace_slug = workspace_slug

        total_projects = Project.query.filter_by(workspace_id=workspace.id).count()
        active_projects = Project.query.filter_by(workspace_id=workspace.id, status='active').count()
        total_tasks = Task.query.filter_by(workspace_id=workspace.id).count()
        todo_tasks = Task.query.filter_by(workspace_id=workspace.id, status='todo').count()
        in_progress_tasks = Task.query.filter_by(workspace_id=workspace.id, status='in_progress').count()
        done_tasks = Task.query.filter_by(workspace_id=workspace.id, status='done').count()
        overdue_tasks = Task.query.filter(
            Task.workspace_id == workspace.id,
            Task.end_date < date.today(),
            Task.status != 'done'
        ).count()
        total_people = Person.query.filter_by(workspace_id=workspace.id).count()
        teams = Team.query.filter_by(workspace_id=workspace.id).all()
        recent_projects = Project.query.filter_by(workspace_id=workspace.id).order_by(Project.id.desc()).limit(5).all()

        return render_template('index.html',
                               workspace=workspace,
                               total_projects=total_projects,
                               active_projects=active_projects,
                               total_tasks=total_tasks,
                               todo_tasks=todo_tasks,
                               in_progress_tasks=in_progress_tasks,
                               done_tasks=done_tasks,
                               overdue_tasks=overdue_tasks,
                               total_people=total_people,
                               teams=teams,
                               recent_projects=recent_projects)

    return app


def ensure_compatible_schema():
    """Apply tiny additive SQLite fixes for older local databases."""
    inspector = inspect(db.engine)
    if 'status_update' not in inspector.get_table_names():
        return

    columns = {col['name'] for col in inspector.get_columns('status_update')}
    if 'external_id' not in columns:
        db.session.execute(text('ALTER TABLE status_update ADD COLUMN external_id VARCHAR(255)'))
        db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
