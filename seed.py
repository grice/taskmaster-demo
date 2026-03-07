"""Populate the database with sample data for testing."""
from app import create_app
from models import db, Workspace, Team, Person, Project, Task, TaskAssignment, TaskDependency, Tag, StatusUpdate
from datetime import date, datetime, timedelta

app = create_app()

with app.app_context():
    # Clear existing data (WARNING: drops all tables and recreates from scratch)
    db.drop_all()
    db.create_all()
    # Note: After seeding, run 'flask db stamp head' to mark migrations as current

    today = date.today()

    # ── Workspace 1: Engineering ───────────────────────────────────────────────
    ws1 = Workspace(name='Engineering', slug='engineering')
    db.session.add(ws1)
    db.session.flush()

    engineering = Team(name='Engineering', workspace_id=ws1.id)
    design = Team(name='Design', workspace_id=ws1.id)
    db.session.add_all([engineering, design])
    db.session.flush()

    alice = Person(name='Alice Chen', email='alice@example.com', workspace_id=ws1.id)
    bob = Person(name='Bob Martinez', email='bob@example.com', workspace_id=ws1.id)
    carol = Person(name='Carol Johnson', email='carol@example.com', workspace_id=ws1.id)
    dave = Person(name='Dave Kim', email='dave@example.com', workspace_id=ws1.id)
    frank = Person(name='Frank Lee', email='frank@example.com', workspace_id=ws1.id)
    db.session.add_all([alice, bob, carol, dave, frank])
    db.session.flush()
    engineering.members.extend([alice, bob, frank])
    design.members.extend([carol, dave])
    # Frank is on both teams (cross-functional)
    design.members.append(frank)

    tag_frontend = Tag(name='frontend', workspace_id=ws1.id)
    tag_backend = Tag(name='backend', workspace_id=ws1.id)
    tag_design = Tag(name='design', workspace_id=ws1.id)
    tag_urgent = Tag(name='urgent', workspace_id=ws1.id)
    tag_v2 = Tag(name='v2', workspace_id=ws1.id)
    tag_infra = Tag(name='infrastructure', workspace_id=ws1.id)
    db.session.add_all([tag_frontend, tag_backend, tag_design, tag_urgent, tag_v2, tag_infra])
    db.session.flush()

    # --- Project 1: Website Redesign ---
    p1 = Project(
        name='Website Redesign',
        description='Complete overhaul of the company website with new branding and improved UX.',
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=60),
        status='active',
        workspace_id=ws1.id,
    )
    db.session.add(p1)
    db.session.flush()

    t1 = Task(title='Design mockups', description='Create wireframes and high-fidelity mockups for all pages.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today - timedelta(days=30), end_date=today - timedelta(days=15),
              status='done', priority='high')
    t2 = Task(title='Frontend implementation', description='Build React components based on approved designs.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today - timedelta(days=14), end_date=today + timedelta(days=20),
              status='in_progress', priority='high')
    t3 = Task(title='Backend API', description='Build REST API endpoints for the new site.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today - timedelta(days=14), end_date=today + timedelta(days=10),
              status='in_progress', priority='high')
    t4 = Task(title='Content migration', description='Migrate existing content to the new CMS structure.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today + timedelta(days=10), end_date=today + timedelta(days=30),
              status='todo', priority='medium')
    t5 = Task(title='QA testing', description='Full regression testing of the new website.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today + timedelta(days=25), end_date=today + timedelta(days=45),
              status='todo', priority='high')
    t6 = Task(title='Launch', description='Deploy to production and monitor.',
              project_id=p1.id, workspace_id=ws1.id,
              start_date=today + timedelta(days=50), end_date=today + timedelta(days=60),
              status='todo', priority='critical')
    db.session.add_all([t1, t2, t3, t4, t5, t6])
    db.session.flush()

    db.session.add_all([
        TaskAssignment(task_id=t1.id, person_id=carol.id, is_lead=True),
        TaskAssignment(task_id=t1.id, person_id=dave.id, is_lead=False),
        TaskAssignment(task_id=t2.id, person_id=alice.id, is_lead=True),
        TaskAssignment(task_id=t2.id, person_id=frank.id, is_lead=False),
        TaskAssignment(task_id=t3.id, person_id=bob.id, is_lead=True),
        TaskAssignment(task_id=t3.id, person_id=alice.id, is_lead=False),
        TaskAssignment(task_id=t4.id, person_id=carol.id, is_lead=True),
        TaskAssignment(task_id=t5.id, person_id=frank.id, is_lead=True),
        TaskAssignment(task_id=t5.id, person_id=bob.id, is_lead=False),
        TaskAssignment(task_id=t6.id, person_id=alice.id, is_lead=True),
        TaskAssignment(task_id=t6.id, person_id=bob.id, is_lead=False),
        TaskAssignment(task_id=t6.id, person_id=frank.id, is_lead=False),
    ])

    t1.tags.extend([tag_design])
    t2.tags.extend([tag_frontend, tag_v2])
    t3.tags.extend([tag_backend, tag_v2])
    t4.tags.extend([tag_frontend])
    t5.tags.extend([tag_frontend, tag_backend])
    t6.tags.extend([tag_infra, tag_urgent])

    db.session.add_all([
        TaskDependency(task_id=t2.id, depends_on_id=t1.id),
        TaskDependency(task_id=t4.id, depends_on_id=t3.id),
        TaskDependency(task_id=t5.id, depends_on_id=t2.id),
        TaskDependency(task_id=t5.id, depends_on_id=t3.id),
        TaskDependency(task_id=t6.id, depends_on_id=t5.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t1.id, content='Initial wireframes completed and shared for review.',
                     created_at=datetime.now() - timedelta(days=25)),
        StatusUpdate(task_id=t1.id, content='Mockups approved by stakeholders. Moving to implementation.',
                     created_at=datetime.now() - timedelta(days=15)),
        StatusUpdate(task_id=t2.id, content='Set up React project scaffolding and component library.',
                     created_at=datetime.now() - timedelta(days=12)),
        StatusUpdate(task_id=t3.id, content='Database schema finalized. Building auth endpoints.',
                     created_at=datetime.now() - timedelta(days=10)),
    ])

    # --- Project 2: Infrastructure Upgrade ---
    p2 = Project(
        name='Infrastructure Upgrade',
        description='Migrate from legacy infrastructure to Kubernetes with improved CI/CD.',
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=45),
        status='active',
        workspace_id=ws1.id,
    )
    db.session.add(p2)
    db.session.flush()

    t7 = Task(title='K8s cluster setup', description='Provision and configure Kubernetes cluster.',
              project_id=p2.id, workspace_id=ws1.id,
              start_date=today - timedelta(days=5), end_date=today + timedelta(days=10),
              status='in_progress', priority='critical')
    t8 = Task(title='CI/CD pipeline', description='Set up GitHub Actions with automated deployments.',
              project_id=p2.id, workspace_id=ws1.id,
              start_date=today + timedelta(days=5), end_date=today + timedelta(days=25),
              status='todo', priority='high')
    t9 = Task(title='Service migration', description='Migrate services one-by-one to new infrastructure.',
              project_id=p2.id, workspace_id=ws1.id,
              start_date=today + timedelta(days=20), end_date=today + timedelta(days=40),
              status='todo', priority='high')
    db.session.add_all([t7, t8, t9])
    db.session.flush()

    db.session.add_all([
        TaskAssignment(task_id=t7.id, person_id=frank.id, is_lead=True),
        TaskAssignment(task_id=t7.id, person_id=bob.id, is_lead=False),
        TaskAssignment(task_id=t8.id, person_id=bob.id, is_lead=True),
        TaskAssignment(task_id=t9.id, person_id=alice.id, is_lead=True),
        TaskAssignment(task_id=t9.id, person_id=frank.id, is_lead=False),
    ])

    t7.tags.extend([tag_infra, tag_urgent])
    t8.tags.extend([tag_infra])
    t9.tags.extend([tag_infra, tag_backend])

    db.session.add_all([
        TaskDependency(task_id=t8.id, depends_on_id=t7.id),
        TaskDependency(task_id=t9.id, depends_on_id=t8.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t7.id, content='Node pool provisioned. Configuring networking and RBAC.',
                     created_at=datetime.now() - timedelta(days=2)),
    ])

    # ── Workspace 2: Marketing ─────────────────────────────────────────────────
    ws2 = Workspace(name='Marketing', slug='marketing')
    db.session.add(ws2)
    db.session.flush()

    mkt_team = Team(name='Marketing', workspace_id=ws2.id)
    creative_team = Team(name='Creative', workspace_id=ws2.id)
    db.session.add_all([mkt_team, creative_team])
    db.session.flush()

    eve = Person(name='Eve Williams', email='eve@example.com', workspace_id=ws2.id)
    grace = Person(name='Grace Park', email='grace@example.com', workspace_id=ws2.id)
    henry = Person(name='Henry Osei', email='henry@example.com', workspace_id=ws2.id)
    db.session.add_all([eve, grace, henry])
    db.session.flush()
    mkt_team.members.extend([eve, henry])
    creative_team.members.extend([grace, eve])

    tag_campaign = Tag(name='campaign', workspace_id=ws2.id)
    tag_social = Tag(name='social', workspace_id=ws2.id)
    tag_content = Tag(name='content', workspace_id=ws2.id)
    db.session.add_all([tag_campaign, tag_social, tag_content])
    db.session.flush()

    # --- Project 3: Q2 Campaign ---
    p3 = Project(
        name='Q2 Product Launch Campaign',
        description='Multi-channel marketing campaign for the Q2 product launch.',
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=50),
        status='active',
        workspace_id=ws2.id,
    )
    db.session.add(p3)
    db.session.flush()

    t10 = Task(title='Campaign strategy', description='Define target audience, channels, and messaging.',
               project_id=p3.id, workspace_id=ws2.id,
               start_date=today - timedelta(days=10), end_date=today + timedelta(days=5),
               status='in_progress', priority='high')
    t11 = Task(title='Creative assets', description='Design banners, social media graphics, and email templates.',
               project_id=p3.id, workspace_id=ws2.id,
               start_date=today + timedelta(days=5), end_date=today + timedelta(days=20),
               status='todo', priority='medium')
    t12 = Task(title='Campaign execution', description='Launch ads, send emails, post on social media.',
               project_id=p3.id, workspace_id=ws2.id,
               start_date=today + timedelta(days=20), end_date=today + timedelta(days=50),
               status='todo', priority='high')
    db.session.add_all([t10, t11, t12])
    db.session.flush()

    db.session.add_all([
        TaskAssignment(task_id=t10.id, person_id=eve.id, is_lead=True),
        TaskAssignment(task_id=t10.id, person_id=henry.id, is_lead=False),
        TaskAssignment(task_id=t11.id, person_id=grace.id, is_lead=True),
        TaskAssignment(task_id=t12.id, person_id=eve.id, is_lead=True),
        TaskAssignment(task_id=t12.id, person_id=henry.id, is_lead=False),
    ])

    t10.tags.extend([tag_campaign])
    t11.tags.extend([tag_content, tag_social])
    t12.tags.extend([tag_campaign, tag_social])

    db.session.add_all([
        TaskDependency(task_id=t11.id, depends_on_id=t10.id),
        TaskDependency(task_id=t12.id, depends_on_id=t11.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t10.id, content='Kicked off strategy session. Focusing on LinkedIn and email.',
                     created_at=datetime.now() - timedelta(days=5)),
    ])

    # --- Project 4: Brand Refresh ---
    p4 = Project(
        name='Brand Refresh',
        description='Update brand guidelines, logo variants, and visual identity.',
        start_date=today - timedelta(days=20),
        end_date=today + timedelta(days=30),
        status='active',
        workspace_id=ws2.id,
    )
    db.session.add(p4)
    db.session.flush()

    t13 = Task(title='Brand audit', description='Review current brand assets and identify gaps.',
               project_id=p4.id, workspace_id=ws2.id,
               start_date=today - timedelta(days=20), end_date=today - timedelta(days=5),
               status='done', priority='medium')
    t14 = Task(title='New logo variants', description='Create updated logo in multiple formats.',
               project_id=p4.id, workspace_id=ws2.id,
               start_date=today - timedelta(days=5), end_date=today + timedelta(days=15),
               status='in_progress', priority='high')
    t15 = Task(title='Style guide update', description='Document updated colors, typography, and usage rules.',
               project_id=p4.id, workspace_id=ws2.id,
               start_date=today + timedelta(days=15), end_date=today + timedelta(days=30),
               status='todo', priority='medium')
    db.session.add_all([t13, t14, t15])
    db.session.flush()

    db.session.add_all([
        TaskAssignment(task_id=t13.id, person_id=grace.id, is_lead=True),
        TaskAssignment(task_id=t14.id, person_id=grace.id, is_lead=True),
        TaskAssignment(task_id=t15.id, person_id=grace.id, is_lead=True),
        TaskAssignment(task_id=t15.id, person_id=eve.id, is_lead=False),
    ])

    t13.tags.extend([tag_content])
    t14.tags.extend([tag_content])
    t15.tags.extend([tag_content])

    db.session.add_all([
        TaskDependency(task_id=t14.id, depends_on_id=t13.id),
        TaskDependency(task_id=t15.id, depends_on_id=t14.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t13.id, content='Audit complete. Found inconsistent logo usage across 12 properties.',
                     created_at=datetime.now() - timedelta(days=5)),
        StatusUpdate(task_id=t14.id, content='First drafts shared with leadership for feedback.',
                     created_at=datetime.now() - timedelta(days=1)),
    ])

    db.session.commit()
    print('Seed data created successfully!')
    print(f'  Workspaces: 2 (engineering, marketing)')
    print(f'  Engineering workspace: 2 teams, 5 people, 2 projects, 9 tasks, 6 tags')
    print(f'  Marketing workspace: 2 teams, 3 people, 2 projects, 6 tasks, 3 tags')
