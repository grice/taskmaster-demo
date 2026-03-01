import os
import re
from markupsafe import Markup, escape
from flask import Flask, render_template
from flask_migrate import Migrate
from models import db, Project, Task, Person, Team, Milestone
from flask import url_for as flask_url_for
from routes import register_blueprints
from datetime import date

migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmaster.db'
    app.config['SECRET_KEY'] = 'dev-secret-key'

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    register_blueprints(app)

    @app.after_request
    def add_no_cache_headers(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.template_filter('render_mentions')
    def render_mentions(content):
        """Replace @"Name" with clickable links, and URLs with hyperlinks."""
        # File extensions to detect for condensed display
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
            # Check if URL path ends with a file extension
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
        # Then render @mentions on raw text (before escaping the rest)
        def replace_mention(m):
            name = m.group(1) or m.group(2)
            safe_name = escape(name.strip())
            person = Person.query.filter(Person.name.ilike(name.strip())).first()
            if person:
                url = flask_url_for('people.detail', id=person.id)
                return f'<a href="{url}" class="mention-tag text-decoration-none">@{safe_name}</a>'
            return f'<span class="mention-tag">@{safe_name}</span>'
        result = re.sub(r'@"([^"]+)"|@(\w+(?:\s\w+)?)', replace_mention, result)
        # Escape any remaining raw text that isn't already wrapped in tags
        # Split on HTML tags, escape non-tag parts
        parts = re.split(r'(<[^>]+>)', result)
        for i, part in enumerate(parts):
            if not part.startswith('<'):
                parts[i] = str(escape(part))
        return Markup(''.join(parts))

    @app.route('/')
    def index():
        total_projects = Project.query.count()
        active_projects = Project.query.filter_by(status='active').count()
        total_tasks = Task.query.count()
        todo_tasks = Task.query.filter_by(status='todo').count()
        in_progress_tasks = Task.query.filter_by(status='in_progress').count()
        done_tasks = Task.query.filter_by(status='done').count()
        overdue_tasks = Task.query.filter(
            Task.end_date < date.today(),
            Task.status != 'done'
        ).count()
        total_people = Person.query.count()
        teams = Team.query.all()
        recent_projects = Project.query.order_by(Project.id.desc()).limit(5).all()

        return render_template('index.html',
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


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
