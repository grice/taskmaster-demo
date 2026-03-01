"""Tests for task CRUD routes, filtering, milestones, and status updates."""
import json
from datetime import date, timedelta
from models import Task, Milestone, StatusUpdate
from tests.conftest import make_project, make_task, make_milestone, make_person


class TestTaskList:
    def test_empty_list(self, client):
        r = client.get('/tasks')
        assert r.status_code == 200
        assert b'Tasks' in r.data

    def test_shows_all_tasks(self, client, db):
        p = make_project()
        make_task(p, 'Alpha Task', status='todo')
        make_task(p, 'Beta Task', status='done')
        r = client.get('/tasks')
        assert b'Alpha Task' in r.data
        assert b'Beta Task' in r.data

    def test_status_filter(self, client, db):
        p = make_project()
        make_task(p, 'Todo Task', status='todo')
        make_task(p, 'Progress Task', status='in_progress')
        r = client.get('/tasks?status=in_progress')
        assert b'Progress Task' in r.data
        assert b'Todo Task' not in r.data

    def test_overdue_filter(self, client, db):
        p = make_project()
        past = date.today() - timedelta(days=10)
        future = date.today() + timedelta(days=10)
        make_task(p, 'Overdue Task', status='in_progress',
                  start=past - timedelta(days=5), end=past)
        make_task(p, 'Future Task', status='todo',
                  start=date.today(), end=future)
        r = client.get('/tasks?overdue=1')
        assert b'Overdue Task' in r.data
        assert b'Future Task' not in r.data

    def test_overdue_excludes_done(self, client, db):
        p = make_project()
        past = date.today() - timedelta(days=10)
        make_task(p, 'Done Past', status='done',
                  start=past - timedelta(days=5), end=past)
        r = client.get('/tasks?overdue=1')
        assert b'Done Past' not in r.data

    def test_in_progress_heading(self, client, db):
        p = make_project()
        make_task(p, status='in_progress')
        r = client.get('/tasks?status=in_progress')
        assert b'In Progress Tasks' in r.data

    def test_overdue_heading(self, client):
        r = client.get('/tasks?overdue=1')
        assert b'Overdue Tasks' in r.data


class TestNewTask:
    def test_get_form(self, client, db):
        p = make_project()
        r = client.get(f'/tasks/new?project_id={p.id}')
        assert r.status_code == 200
        assert b'Title' in r.data

    def test_create_task(self, client, db):
        p = make_project()
        r = client.post('/tasks/new', data={
            'title': 'Brand New Task',
            'project_id': str(p.id),
            'status': 'todo',
            'priority': 'high',
            'start_date': '2025-02-01',
            'end_date': '2025-04-01',
            'description': '',
            'tags': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        task = Task.query.filter_by(title='Brand New Task').first()
        assert task is not None
        assert task.priority == 'high'
        assert task.project_id == p.id

    def test_create_redirects_to_project(self, client, db):
        p = make_project()
        r = client.post('/tasks/new', data={
            'title': 'Redirect Task',
            'project_id': str(p.id),
            'status': 'todo',
            'priority': 'medium',
            'start_date': '2025-02-01',
            'end_date': '2025-04-01',
        })
        assert r.status_code == 302
        assert f'/projects/{p.id}' in r.headers['Location']


class TestTaskDetail:
    def test_shows_task(self, client, db):
        p = make_project()
        t = make_task(p, 'My Detailed Task')
        r = client.get(f'/tasks/{t.id}')
        assert r.status_code == 200
        assert b'My Detailed Task' in r.data

    def test_404_for_missing(self, client):
        r = client.get('/tasks/99999')
        assert r.status_code == 404

    def test_shows_milestones_section(self, client, db):
        p = make_project()
        t = make_task(p)
        r = client.get(f'/tasks/{t.id}')
        assert b'Milestones' in r.data


class TestEditTask:
    def test_get_edit_form(self, client, db):
        p = make_project()
        t = make_task(p, 'Editable Task')
        r = client.get(f'/tasks/{t.id}/edit')
        assert r.status_code == 200
        assert b'Editable Task' in r.data

    def test_update_task(self, client, db):
        p = make_project()
        t = make_task(p, 'Old Title')
        r = client.post(f'/tasks/{t.id}/edit', data={
            'title': 'Updated Title',
            'project_id': str(p.id),
            'status': 'in_progress',
            'priority': 'critical',
            'start_date': '2025-01-01',
            'end_date': '2025-06-30',
            'tags': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        db.session.refresh(t)
        assert t.title == 'Updated Title'
        assert t.status == 'in_progress'
        assert t.priority == 'critical'


class TestDeleteTask:
    def test_get_shows_confirmation(self, client, db):
        p = make_project()
        t = make_task(p, 'Doomed Task')
        r = client.get(f'/tasks/{t.id}/delete')
        assert r.status_code == 200
        assert b'Delete Task' in r.data
        assert b'Doomed Task' in r.data

    def test_post_deletes_task(self, client, db):
        p = make_project()
        t = make_task(p)
        tid = t.id
        r = client.post(f'/tasks/{tid}/delete', follow_redirects=True)
        assert r.status_code == 200
        assert Task.query.get(tid) is None

    def test_post_redirects_to_project(self, client, db):
        p = make_project()
        t = make_task(p)
        r = client.post(f'/tasks/{t.id}/delete')
        assert r.status_code == 302
        assert f'/projects/{p.id}' in r.headers['Location']


class TestQuickUpdate:
    def test_update_status(self, client, db):
        p = make_project()
        t = make_task(p, status='todo')
        r = client.post(f'/tasks/{t.id}/quick-update',
                        data=json.dumps({'status': 'in_progress'}),
                        content_type='application/json')
        assert r.status_code == 200
        assert r.get_json()['ok'] is True
        db.session.refresh(t)
        assert t.status == 'in_progress'

    def test_update_dates(self, client, db):
        p = make_project()
        t = make_task(p)
        r = client.post(f'/tasks/{t.id}/quick-update',
                        data=json.dumps({'start_date': '2025-03-01', 'end_date': '2025-09-01'}),
                        content_type='application/json')
        assert r.status_code == 200
        db.session.refresh(t)
        assert t.start_date == date(2025, 3, 1)
        assert t.end_date == date(2025, 9, 1)


class TestStatusUpdates:
    def test_add_status_update(self, client, db):
        p = make_project()
        t = make_task(p)
        r = client.post(f'/tasks/{t.id}/status',
                        data={'content': 'Work is going well'},
                        follow_redirects=True)
        assert r.status_code == 200
        update = StatusUpdate.query.filter_by(task_id=t.id).first()
        assert update is not None
        assert update.content == 'Work is going well'

    def test_empty_update_ignored(self, client, db):
        p = make_project()
        t = make_task(p)
        client.post(f'/tasks/{t.id}/status', data={'content': '   '})
        assert StatusUpdate.query.filter_by(task_id=t.id).count() == 0

    def test_mention_creates_link(self, client, db):
        person = make_person('Jane Smith')
        p = make_project()
        t = make_task(p)
        r = client.post(f'/tasks/{t.id}/status',
                        data={'content': '@"Jane Smith" has reviewed this'},
                        follow_redirects=True)
        assert r.status_code == 200
        update = StatusUpdate.query.filter_by(task_id=t.id).first()
        assert person in update.mentions


class TestMilestones:
    def test_add_milestone(self, client, db):
        p = make_project()
        t = make_task(p)
        r = client.post(f'/tasks/{t.id}/milestones',
                        data={'name': 'Launch', 'date': '2025-06-15'},
                        follow_redirects=True)
        assert r.status_code == 200
        ms = Milestone.query.filter_by(task_id=t.id).first()
        assert ms is not None
        assert ms.name == 'Launch'
        assert ms.date == date(2025, 6, 15)

    def test_delete_milestone_confirmation(self, client, db):
        p = make_project()
        t = make_task(p)
        ms = make_milestone(t, 'Beta')
        r = client.get(f'/milestones/{ms.id}/delete')
        assert r.status_code == 200
        assert b'Delete Milestone' in r.data
        assert b'Beta' in r.data

    def test_delete_milestone(self, client, db):
        p = make_project()
        t = make_task(p)
        ms = make_milestone(t)
        msid = ms.id
        r = client.post(f'/milestones/{msid}/delete', follow_redirects=True)
        assert r.status_code == 200
        assert Milestone.query.get(msid) is None

    def test_update_milestone(self, client, db):
        p = make_project()
        t = make_task(p)
        ms = make_milestone(t, 'Old Name', date(2025, 5, 1))
        r = client.post(f'/milestones/{ms.id}/update', data={
            'name': 'New Name',
            'date': '2025-07-01',
            'status_override': 'on_hold',
        }, follow_redirects=True)
        assert r.status_code == 200
        db.session.refresh(ms)
        assert ms.name == 'New Name'
        assert ms.date == date(2025, 7, 1)
        assert ms.status_override == 'on_hold'
