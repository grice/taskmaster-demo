"""Tests for people and team routes."""
from models import Person, Team
from tests.conftest import make_team, make_person, make_project, make_task


class TestPeopleList:
    def test_empty_list(self, client):
        r = client.get('/people')
        assert r.status_code == 200
        assert b'People' in r.data

    def test_shows_people(self, client, db):
        make_person('Alice')
        make_person('Bob')
        r = client.get('/people')
        assert b'Alice' in r.data
        assert b'Bob' in r.data


class TestNewPerson:
    def test_get_form(self, client):
        r = client.get('/people/new')
        assert r.status_code == 200
        assert b'Name' in r.data

    def test_create_person(self, client, db):
        r = client.post('/people/new', data={
            'name': 'Carol',
            'email': 'carol@example.com',
        }, follow_redirects=True)
        assert r.status_code == 200
        person = Person.query.filter_by(name='Carol').first()
        assert person is not None
        assert person.email == 'carol@example.com'

    def test_create_with_team(self, client, db):
        team = make_team('Engineering')
        r = client.post('/people/new', data={
            'name': 'Dave',
            'email': 'dave@example.com',
            'team_id': str(team.id),
        }, follow_redirects=True)
        assert r.status_code == 200
        person = Person.query.filter_by(name='Dave').first()
        assert person.team_id == team.id


class TestPersonDetail:
    def test_shows_person(self, client, db):
        p = make_person('Eve')
        r = client.get(f'/people/{p.id}')
        assert r.status_code == 200
        assert b'Eve' in r.data

    def test_404_for_missing(self, client):
        r = client.get('/people/99999')
        assert r.status_code == 404

    def test_shows_assigned_tasks(self, client, db):
        from models import TaskAssignment
        person = make_person('Frank')
        proj = make_project()
        task = make_task(proj, 'Frank\'s Task')
        db.session.add(TaskAssignment(task_id=task.id, person_id=person.id, is_lead=True))
        db.session.commit()
        r = client.get(f'/people/{person.id}')
        assert b"Frank&#39;s Task" in r.data or b"Frank's Task" in r.data


class TestEditPerson:
    def test_get_edit_form(self, client, db):
        p = make_person('Grace')
        r = client.get(f'/people/{p.id}/edit')
        assert r.status_code == 200
        assert b'Grace' in r.data

    def test_update_person(self, client, db):
        p = make_person('Hank')
        r = client.post(f'/people/{p.id}/edit', data={
            'name': 'Henry',
            'email': 'henry@example.com',
        }, follow_redirects=True)
        assert r.status_code == 200
        db.session.refresh(p)
        assert p.name == 'Henry'


class TestDeletePerson:
    def test_get_shows_confirmation(self, client, db):
        p = make_person('Ivan')
        r = client.get(f'/people/{p.id}/delete')
        assert r.status_code == 200
        assert b'Delete Person' in r.data
        assert b'Ivan' in r.data

    def test_post_deletes_person(self, client, db):
        p = make_person('Jack')
        pid = p.id
        r = client.post(f'/people/{pid}/delete', follow_redirects=True)
        assert r.status_code == 200
        assert Person.query.get(pid) is None


class TestTeamList:
    def test_empty_list(self, client):
        r = client.get('/teams')
        assert r.status_code == 200
        assert b'Teams' in r.data

    def test_shows_teams(self, client, db):
        make_team('Backend')
        make_team('Frontend')
        r = client.get('/teams')
        assert b'Backend' in r.data
        assert b'Frontend' in r.data


class TestNewTeam:
    def test_get_form(self, client):
        r = client.get('/teams/new')
        assert r.status_code == 200

    def test_create_team(self, client, db):
        r = client.post('/teams/new', data={'name': 'QA'}, follow_redirects=True)
        assert r.status_code == 200
        team = Team.query.filter_by(name='QA').first()
        assert team is not None

    def test_create_redirects_to_list(self, client, db):
        r = client.post('/teams/new', data={'name': 'Ops'})
        assert r.status_code == 302
        assert '/teams' in r.headers['Location']


class TestEditTeam:
    def test_get_edit_form(self, client, db):
        t = make_team('Old Team')
        r = client.get(f'/teams/{t.id}/edit')
        assert r.status_code == 200
        assert b'Old Team' in r.data

    def test_update_team(self, client, db):
        t = make_team('Rename Me')
        r = client.post(f'/teams/{t.id}/edit', data={'name': 'Renamed'},
                        follow_redirects=True)
        assert r.status_code == 200
        db.session.refresh(t)
        assert t.name == 'Renamed'


class TestDeleteTeam:
    def test_get_shows_confirmation(self, client, db):
        t = make_team('Doomed Team')
        r = client.get(f'/teams/{t.id}/delete')
        assert r.status_code == 200
        assert b'Delete Team' in r.data
        assert b'Doomed Team' in r.data

    def test_post_deletes_team(self, client, db):
        t = make_team('Gone Team')
        tid = t.id
        r = client.post(f'/teams/{tid}/delete', follow_redirects=True)
        assert r.status_code == 200
        assert Team.query.get(tid) is None
