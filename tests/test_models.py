"""Unit tests for model properties and computed fields."""
from datetime import date, timedelta
import pytest
from models import Task, TaskAssignment, Milestone, Project, Person
from tests.conftest import make_project, make_task, make_milestone, make_person, make_team


class TestTaskProgress:
    def test_todo_is_zero(self, db):
        p = make_project()
        t = make_task(p, status='todo')
        assert t.progress == 0

    def test_in_progress_is_fifty(self, db):
        p = make_project()
        t = make_task(p, status='in_progress')
        assert t.progress == 50

    def test_done_is_hundred(self, db):
        p = make_project()
        t = make_task(p, status='done')
        assert t.progress == 100


class TestTaskAssignees:
    def test_no_assignees(self, db):
        p = make_project()
        t = make_task(p)
        assert t.lead is None
        assert t.assignees == []

    def test_lead_is_returned(self, db):
        p = make_project()
        t = make_task(p)
        person = make_person()
        db.session.add(TaskAssignment(task_id=t.id, person_id=person.id, is_lead=True))
        db.session.commit()
        assert t.lead == person

    def test_assignees_includes_all(self, db):
        p = make_project()
        t = make_task(p)
        alice = make_person('Alice')
        bob = make_person('Bob')
        db.session.add(TaskAssignment(task_id=t.id, person_id=alice.id, is_lead=True))
        db.session.add(TaskAssignment(task_id=t.id, person_id=bob.id, is_lead=False))
        db.session.commit()
        assert set(t.assignees) == {alice, bob}

    def test_non_lead_has_no_lead(self, db):
        p = make_project()
        t = make_task(p)
        person = make_person()
        db.session.add(TaskAssignment(task_id=t.id, person_id=person.id, is_lead=False))
        db.session.commit()
        assert t.lead is None


class TestMilestoneComputedStatus:
    def test_manual_override_takes_precedence(self, db):
        p = make_project()
        t = make_task(p)
        ms = make_milestone(t, status_override='on_hold')
        assert ms.computed_status == 'on_hold'

    def test_on_track_for_future_date(self, db):
        p = make_project()
        t = make_task(p, status='in_progress')
        future = date.today() + timedelta(days=30)
        ms = make_milestone(t, ms_date=future)
        assert ms.computed_status == 'on_track'

    def test_delayed_for_past_date_incomplete_task(self, db):
        p = make_project()
        t = make_task(p, status='in_progress')
        past = date.today() - timedelta(days=5)
        ms = make_milestone(t, ms_date=past)
        assert ms.computed_status == 'delayed'

    def test_on_track_when_task_done_despite_past_date(self, db):
        p = make_project()
        t = make_task(p, status='done')
        past = date.today() - timedelta(days=5)
        ms = make_milestone(t, ms_date=past)
        assert ms.computed_status == 'on_track'

    def test_on_hold_when_project_on_hold(self, db):
        p = make_project(status='on_hold')
        t = make_task(p)
        future = date.today() + timedelta(days=10)
        ms = make_milestone(t, ms_date=future)
        assert ms.computed_status == 'on_hold'
