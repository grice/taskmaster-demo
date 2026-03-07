from .projects import bp as projects_bp
from .people import bp as people_bp
from .tasks import bp as tasks_bp
from .teams import bp as teams_bp
from .workspaces import bp as workspaces_bp


def register_blueprints(app):
    app.register_blueprint(workspaces_bp)
    app.register_blueprint(projects_bp, url_prefix='/w/<workspace_slug>')
    app.register_blueprint(people_bp, url_prefix='/w/<workspace_slug>')
    app.register_blueprint(tasks_bp, url_prefix='/w/<workspace_slug>')
    app.register_blueprint(teams_bp, url_prefix='/w/<workspace_slug>')
