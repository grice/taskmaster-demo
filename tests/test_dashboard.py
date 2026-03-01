"""Tests for the dashboard/index route."""
from datetime import date, timedelta
from tests.conftest import make_project, make_task, make_team, make_person


class TestDashboard:
    def test_loads(self, client):
        r = client.get('/')
        assert r.status_code == 200
        assert b'Dashboard' in r.data

    def test_active_projects_count(self, client, db):
        make_project('Active 1', status='active')
        make_project('Active 2', status='active')
        make_project('Done', status='completed')
        r = client.get('/')
        # The number 2 should appear in the active projects stat card
        assert b'Active Projects' in r.data

    def test_total_tasks_count(self, client, db):
        p = make_project()
        make_task(p, 'T1')
        make_task(p, 'T2')
        make_task(p, 'T3')
        r = client.get('/')
        assert b'Total Tasks' in r.data

    def test_overdue_tasks_count(self, client, db):
        p = make_project()
        past = date.today() - timedelta(days=5)
        make_task(p, 'Overdue', status='in_progress',
                  start=past - timedelta(days=2), end=past)
        r = client.get('/')
        assert b'Overdue' in r.data

    def test_stat_cards_are_links(self, client):
        r = client.get('/')
        assert b'href' in r.data
        assert b'/projects?status=active' in r.data
        assert b'/tasks' in r.data

    def test_shows_recent_projects(self, client, db):
        make_project('Recent Project Alpha')
        r = client.get('/')
        assert b'Recent Project Alpha' in r.data

    def test_shows_teams(self, client, db):
        make_team('The A-Team')
        r = client.get('/')
        assert b'The A-Team' in r.data
