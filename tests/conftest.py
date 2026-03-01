import pytest
from datetime import date
from sqlalchemy.pool import StaticPool

from app import create_app
from models import (db as _db, Team, Person, Project, Task,
                    TaskAssignment, Milestone, StatusUpdate, Tag)


@pytest.fixture(scope='session')
def app():
    return create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
    })


@pytest.fixture()
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app, db):
    return app.test_client()


# ── Data helpers ──────────────────────────────────────────────────────────────

def make_team(name='Alpha Team'):
    t = Team(name=name)
    _db.session.add(t)
    _db.session.commit()
    return t


def make_person(name='Alice', team=None):
    p = Person(name=name, email=f'{name.lower().replace(" ", ".")}@example.com',
               team_id=team.id if team else None)
    _db.session.add(p)
    _db.session.commit()
    return p


def make_project(name='Test Project', status='active',
                 start=date(2025, 1, 1), end=date(2025, 12, 31)):
    p = Project(name=name, status=status, start_date=start, end_date=end,
                description='A test project')
    _db.session.add(p)
    _db.session.commit()
    return p


def make_task(project, title='Test Task', status='todo', priority='medium',
              start=date(2025, 1, 1), end=date(2025, 6, 30)):
    t = Task(title=title, project_id=project.id, status=status,
             priority=priority, start_date=start, end_date=end)
    _db.session.add(t)
    _db.session.commit()
    return t


def make_milestone(task, name='Beta Release', ms_date=date(2025, 6, 1),
                   status_override=None):
    m = Milestone(task_id=task.id, name=name, date=ms_date,
                  status_override=status_override)
    _db.session.add(m)
    _db.session.commit()
    return m
