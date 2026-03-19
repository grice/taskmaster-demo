from pathlib import Path

from models import Person, Project, Task, Team, Workspace
from workspace_import import load_people_csv, load_plan_csv


class TestWorkspaceImportValidation:
    def test_duplicate_team_name_fails(self, app, db, tmp_path):
        csv_path = tmp_path / 'people.csv'
        csv_path.write_text(
            'type,name,email,teams\n'
            'team,Design,,\n'
            'team,Design,,\n',
            encoding='utf-8',
        )

        with app.app_context():
            ws = Workspace(name='Import Test', slug='import-test')
            db.session.add(ws)
            db.session.flush()

            try:
                load_people_csv(csv_path, ws.id)
                assert False, 'expected SystemExit'
            except SystemExit as exc:
                assert 'duplicate team name' in str(exc)
                db.session.rollback()

            assert Team.query.filter_by(workspace_id=ws.id).count() == 0

    def test_duplicate_task_name_fails(self, app, db, tmp_path):
        csv_path = tmp_path / 'plan.csv'
        csv_path.write_text(
            'type,name,description,start_date,end_date,status,priority,assignees,tags,depends_on\n'
            'project,Project One,,2025-01-01,2025-02-01,active,,,,\n'
            'task,Shared Task,,2025-01-01,2025-01-10,todo,medium,,,\n'
            'project,Project Two,,2025-02-01,2025-03-01,active,,,,\n'
            'task,Shared Task,,2025-02-01,2025-02-10,todo,medium,,,\n',
            encoding='utf-8',
        )

        with app.app_context():
            ws = Workspace(name='Import Test', slug='import-test')
            db.session.add(ws)
            db.session.flush()

            try:
                load_plan_csv(csv_path, ws.id, {})
                assert False, 'expected SystemExit'
            except SystemExit as exc:
                assert 'duplicate task name' in str(exc)
                db.session.rollback()

            assert Project.query.filter_by(workspace_id=ws.id).count() == 0
            assert Task.query.filter_by(workspace_id=ws.id).count() == 0

    def test_duplicate_person_name_fails(self, app, db, tmp_path):
        csv_path = tmp_path / 'people.csv'
        csv_path.write_text(
            'type,name,email,teams\n'
            'person,Alice Smith,alice@example.com,\n'
            'person,Alice Smith,alice2@example.com,\n',
            encoding='utf-8',
        )

        with app.app_context():
            ws = Workspace(name='Import Test', slug='import-test')
            db.session.add(ws)
            db.session.flush()

            try:
                load_people_csv(csv_path, ws.id)
                assert False, 'expected SystemExit'
            except SystemExit as exc:
                assert 'duplicate person name' in str(exc)
                db.session.rollback()

            assert Person.query.filter_by(workspace_id=ws.id).count() == 0
