from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

status_update_mentions = db.Table(
    'status_update_mentions',
    db.Column('status_update_id', db.Integer, db.ForeignKey('status_update.id'), primary_key=True),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id'), primary_key=True),
)

task_tags = db.Table(
    'task_tags',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
)

person_teams = db.Table(
    'person_teams',
    db.Column('person_id', db.Integer, db.ForeignKey('person.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
)


class Workspace(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    members = db.relationship('Person', secondary='person_teams',
                              backref=db.backref('teams', lazy=True))


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    assignments = db.relationship('TaskAssignment', backref='person', lazy=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # active, completed, on_hold
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, done
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical

    assignments = db.relationship('TaskAssignment', backref='task', lazy=True,
                                   cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=task_tags, backref=db.backref('tasks', lazy=True))
    milestones = db.relationship('Milestone', backref='task', lazy=True,
                                 order_by='Milestone.date', cascade='all, delete-orphan')
    status_updates = db.relationship('StatusUpdate', backref='task', lazy=True,
                                     order_by='StatusUpdate.created_at.desc()',
                                     cascade='all, delete-orphan')
    # Dependencies: tasks that this task depends on (blocked by)
    dependencies = db.relationship(
        'Task',
        secondary='task_dependency',
        primaryjoin='Task.id == TaskDependency.task_id',
        secondaryjoin='Task.id == TaskDependency.depends_on_id',
        backref=db.backref('dependents', lazy=True),
        lazy=True,
    )

    @property
    def lead(self):
        for a in self.assignments:
            if a.is_lead:
                return a.person
        return None

    @property
    def assignees(self):
        return [a.person for a in self.assignments]

    @property
    def progress(self):
        if self.status == 'done':
            return 100
        elif self.status == 'in_progress':
            return 50
        return 0


class TaskDependency(db.Model):
    __tablename__ = 'task_dependency'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    depends_on_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)


class TaskAssignment(db.Model):
    __tablename__ = 'task_assignment'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    is_lead = db.Column(db.Boolean, default=False)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('workspace_id', 'name', name='uq_tag_workspace_name'),)


class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status_override = db.Column(db.String(20), nullable=True)  # on_track, delayed, on_hold

    @property
    def computed_status(self):
        if self.status_override:
            return self.status_override
        today = date.today()
        if self.task.project.status == 'on_hold':
            return 'on_hold'
        if self.date < today and self.task.status != 'done':
            return 'delayed'
        return 'on_track'


class StatusUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    external_id = db.Column(db.String(255), nullable=True, index=True)
    mentions = db.relationship('Person', secondary=status_update_mentions,
                               backref=db.backref('mentioned_in', lazy=True))
