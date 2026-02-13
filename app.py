import os
import re
from markupsafe import Markup, escape
from flask import Flask, render_template
from flask_migrate import Migrate
from models import db, Project, Task, Person, Team
from routes import register_blueprints
from datetime import date

migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmaster.db'
    app.config['SECRET_KEY'] = 'dev-secret-key'

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    register_blueprints(app)

    @app.template_filter('render_mentions')
    def render_mentions(content):
        """Replace @"Name" with styled spans, and URLs with clickable links."""
        safe = str(escape(content))
        # Linkify URLs first (before mentions, since URLs won't contain @"...")
        def replace_url(m):
            url = m.group(0)
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
        result = re.sub(r'https?://[^\s<>&]+', replace_url, safe)
        # Then render @mentions
        def replace_mention(m):
            name = m.group(1) or m.group(2)
            return f'<span class="mention-tag">@{escape(name)}</span>'
        result = re.sub(r'@&quot;([^&]+)&quot;|@(\w+(?:\s\w+)?)', replace_mention, result)
        return Markup(result)

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
