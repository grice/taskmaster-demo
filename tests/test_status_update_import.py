import io
from datetime import datetime

from models import StatusUpdate
from status_update_import import import_status_updates_from_text
from tests.conftest import W, make_person, make_project, make_task


class TestStatusUpdateImportService:
    def test_dry_run_does_not_write_updates(self, app, db):
        make_person('Jane Smith')
        project = make_project('Website Redesign')
        make_task(project, 'Homepage QA')

        summary = import_status_updates_from_text(
            'project_name,task_title,created_at,content,mentions,external_id\n'
            'Website Redesign,Homepage QA,2026-03-14 09:00:00,"Blocked on legal copy",Jane Smith,weekly-1\n',
            workspace_slug='test',
            dry_run=True,
        )

        assert summary.imported == 1
        assert summary.errors == 0
        assert StatusUpdate.query.count() == 0

    def test_import_writes_update_and_mentions(self, app, db):
        person = make_person('Jane Smith')
        project = make_project('Website Redesign')
        task = make_task(project, 'Homepage QA')

        summary = import_status_updates_from_text(
            'project_name,task_title,created_at,content,mentions,external_id\n'
            'Website Redesign,Homepage QA,2026-03-14 09:00:00,"Blocked on legal copy",Jane Smith,weekly-1\n',
            workspace_slug='test',
            dry_run=False,
        )

        assert summary.imported == 1
        update = StatusUpdate.query.filter_by(task_id=task.id).one()
        assert update.content == 'Blocked on legal copy'
        assert update.external_id == 'weekly-1'
        assert update.created_at == datetime(2026, 3, 14, 9, 0, 0)
        assert person in update.mentions

    def test_duplicate_external_id_is_skipped(self, app, db):
        project = make_project('Website Redesign')
        task = make_task(project, 'Homepage QA')
        db.session.add(StatusUpdate(task_id=task.id, content='Old update', external_id='weekly-1'))
        db.session.commit()

        summary = import_status_updates_from_text(
            'project_name,task_title,content,external_id\n'
            'Website Redesign,Homepage QA,"Blocked on legal copy",weekly-1\n',
            workspace_slug='test',
            dry_run=False,
        )

        assert summary.skipped == 1
        assert StatusUpdate.query.count() == 1

    def test_unmatched_task_reports_error(self, app, db):
        make_project('Website Redesign')

        summary = import_status_updates_from_text(
            'project_name,task_title,content\n'
            'Website Redesign,Missing Task,"Blocked on legal copy"\n',
            workspace_slug='test',
            dry_run=False,
        )

        assert summary.errors == 1
        assert 'No task match' in summary.results[0].message


class TestStatusUpdateImportRoute:
    def test_import_page_renders(self, client):
        r = client.get(W + '/imports/status-updates')
        assert r.status_code == 200
        assert b'Import Status Updates' in r.data

    def test_parser_guide_download(self, client, db):
        make_person('Jane Smith')
        project = make_project('Website Redesign')
        make_task(project, 'Homepage QA')

        r = client.get(W + '/imports/status-updates/parser-guide')

        assert r.status_code == 200
        assert b'Status Update CSV Instructions' in r.data
        assert b'Current Workspace Reference' in r.data
        assert b'Website Redesign' in r.data
        assert b'Homepage QA' in r.data
        assert b'Jane Smith' in r.data

    def test_upload_preview(self, client, db):
        make_person('Jane Smith')
        project = make_project('Website Redesign')
        make_task(project, 'Homepage QA')

        csv_bytes = io.BytesIO(
            b'project_name,task_title,created_at,content,mentions,external_id\n'
            b'Website Redesign,Homepage QA,2026-03-14 09:00:00,"Blocked on legal copy",Jane Smith,weekly-1\n'
        )

        r = client.post(
            W + '/imports/status-updates',
            data={'dry_run': '1', 'csv_file': (csv_bytes, 'updates.csv')},
            content_type='multipart/form-data',
        )

        assert r.status_code == 200
        assert b'Preview' in r.data
        assert b'Blocked on legal copy' not in r.data
        assert StatusUpdate.query.count() == 0

    def test_upload_import_writes_updates(self, client, db):
        project = make_project('Website Redesign')
        make_task(project, 'Homepage QA')

        csv_bytes = io.BytesIO(
            b'project_name,task_title,content,external_id\n'
            b'Website Redesign,Homepage QA,"Blocked on legal copy",weekly-1\n'
        )

        r = client.post(
            W + '/imports/status-updates',
            data={'csv_file': (csv_bytes, 'updates.csv')},
            content_type='multipart/form-data',
        )

        assert r.status_code == 200
        assert StatusUpdate.query.count() == 1

    def test_preview_can_be_committed_without_reupload(self, client, db):
        project = make_project('Website Redesign')
        make_task(project, 'Homepage QA')

        csv_text = (
            'project_name,task_title,content,external_id\n'
            'Website Redesign,Homepage QA,"Blocked on legal copy",weekly-1\n'
        )

        preview = client.post(
            W + '/imports/status-updates',
            data={'dry_run': '1', 'csv_file': (io.BytesIO(csv_text.encode('utf-8')), 'updates.csv')},
            content_type='multipart/form-data',
        )

        assert preview.status_code == 200
        assert b'Import Previewed File' in preview.data
        assert StatusUpdate.query.count() == 0

        commit = client.post(
            W + '/imports/status-updates',
            data={'commit_preview': '1', 'preview_csv_text': csv_text},
        )

        assert commit.status_code == 200
        assert StatusUpdate.query.count() == 1
