"""Populate the database with sample data for testing."""
from app import create_app
from models import db, Team, Person, Project, Task, TaskDependency, Tag, StatusUpdate
from datetime import date, datetime, timedelta

app = create_app()

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # --- Teams ---
    engineering = Team(name='Engineering')
    design = Team(name='Design')
    marketing = Team(name='Marketing')
    db.session.add_all([engineering, design, marketing])
    db.session.flush()

    # --- People ---
    alice = Person(name='Alice Chen', email='alice@example.com', team_id=engineering.id)
    bob = Person(name='Bob Martinez', email='bob@example.com', team_id=engineering.id)
    carol = Person(name='Carol Johnson', email='carol@example.com', team_id=design.id)
    dave = Person(name='Dave Kim', email='dave@example.com', team_id=design.id)
    eve = Person(name='Eve Williams', email='eve@example.com', team_id=marketing.id)
    frank = Person(name='Frank Lee', email='frank@example.com', team_id=engineering.id)
    db.session.add_all([alice, bob, carol, dave, eve, frank])
    db.session.flush()

    # --- Tags ---
    tag_frontend = Tag(name='frontend')
    tag_backend = Tag(name='backend')
    tag_design = Tag(name='design')
    tag_urgent = Tag(name='urgent')
    tag_v2 = Tag(name='v2')
    tag_infra = Tag(name='infrastructure')
    db.session.add_all([tag_frontend, tag_backend, tag_design, tag_urgent, tag_v2, tag_infra])
    db.session.flush()

    today = date.today()

    # --- Project 1: Website Redesign ---
    p1 = Project(
        name='Website Redesign',
        description='Complete overhaul of the company website with new branding and improved UX.',
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=60),
        status='active',
    )
    db.session.add(p1)
    db.session.flush()

    t1 = Task(title='Design mockups', description='Create wireframes and high-fidelity mockups for all pages.',
              project_id=p1.id, assignee_id=carol.id,
              start_date=today - timedelta(days=30), end_date=today - timedelta(days=15),
              status='done', priority='high')
    t2 = Task(title='Frontend implementation', description='Build React components based on approved designs.',
              project_id=p1.id, assignee_id=alice.id,
              start_date=today - timedelta(days=14), end_date=today + timedelta(days=20),
              status='in_progress', priority='high')
    t3 = Task(title='Backend API', description='Build REST API endpoints for the new site.',
              project_id=p1.id, assignee_id=bob.id,
              start_date=today - timedelta(days=14), end_date=today + timedelta(days=10),
              status='in_progress', priority='high')
    t4 = Task(title='Content migration', description='Migrate existing content to the new CMS structure.',
              project_id=p1.id, assignee_id=eve.id,
              start_date=today + timedelta(days=10), end_date=today + timedelta(days=30),
              status='todo', priority='medium')
    t5 = Task(title='QA testing', description='Full regression testing of the new website.',
              project_id=p1.id, assignee_id=frank.id,
              start_date=today + timedelta(days=25), end_date=today + timedelta(days=45),
              status='todo', priority='high')
    t6 = Task(title='Launch', description='Deploy to production and monitor.',
              project_id=p1.id, assignee_id=alice.id,
              start_date=today + timedelta(days=50), end_date=today + timedelta(days=60),
              status='todo', priority='critical')
    db.session.add_all([t1, t2, t3, t4, t5, t6])
    db.session.flush()

    # Tags
    t1.tags.extend([tag_design])
    t2.tags.extend([tag_frontend, tag_v2])
    t3.tags.extend([tag_backend, tag_v2])
    t4.tags.extend([tag_frontend])
    t5.tags.extend([tag_frontend, tag_backend])
    t6.tags.extend([tag_infra, tag_urgent])

    # Dependencies
    db.session.add_all([
        TaskDependency(task_id=t2.id, depends_on_id=t1.id),  # frontend depends on mockups
        TaskDependency(task_id=t4.id, depends_on_id=t3.id),  # content migration depends on API
        TaskDependency(task_id=t5.id, depends_on_id=t2.id),  # QA depends on frontend
        TaskDependency(task_id=t5.id, depends_on_id=t3.id),  # QA depends on API
        TaskDependency(task_id=t6.id, depends_on_id=t5.id),  # launch depends on QA
    ])

    # Status updates
    db.session.add_all([
        StatusUpdate(task_id=t1.id, content='Initial wireframes completed and shared for review.',
                     created_at=datetime.now() - timedelta(days=25)),
        StatusUpdate(task_id=t1.id, content='Mockups approved by stakeholders. Moving to implementation.',
                     created_at=datetime.now() - timedelta(days=15)),
        StatusUpdate(task_id=t2.id, content='Set up React project scaffolding and component library.',
                     created_at=datetime.now() - timedelta(days=12)),
        StatusUpdate(task_id=t2.id, content='Homepage and about page components done. Working on product pages.',
                     created_at=datetime.now() - timedelta(days=5)),
        StatusUpdate(task_id=t3.id, content='Database schema finalized. Building auth endpoints.',
                     created_at=datetime.now() - timedelta(days=10)),
        StatusUpdate(task_id=t3.id, content='Core CRUD endpoints done. Starting on search and filtering.',
                     created_at=datetime.now() - timedelta(days=2)),
    ])

    # --- Project 2: Mobile App v2 ---
    p2 = Project(
        name='Mobile App v2',
        description='Major update to the mobile app with offline support and new navigation.',
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=90),
        status='active',
    )
    db.session.add(p2)
    db.session.flush()

    t7 = Task(title='UX research', description='User interviews and competitor analysis.',
              project_id=p2.id, assignee_id=dave.id,
              start_date=today - timedelta(days=10), end_date=today + timedelta(days=5),
              status='in_progress', priority='medium')
    t8 = Task(title='App architecture planning', description='Plan the new offline-first architecture.',
              project_id=p2.id, assignee_id=bob.id,
              start_date=today - timedelta(days=5), end_date=today + timedelta(days=10),
              status='in_progress', priority='high')
    t9 = Task(title='Offline sync engine', description='Build the offline data sync layer.',
              project_id=p2.id, assignee_id=frank.id,
              start_date=today + timedelta(days=10), end_date=today + timedelta(days=50),
              status='todo', priority='critical')
    t10 = Task(title='New navigation UI', description='Implement the redesigned navigation flow.',
               project_id=p2.id, assignee_id=alice.id,
               start_date=today + timedelta(days=15), end_date=today + timedelta(days=45),
               status='todo', priority='high')
    t11 = Task(title='Beta testing', description='Distribute beta builds and collect feedback.',
               project_id=p2.id, assignee_id=eve.id,
               start_date=today + timedelta(days=55), end_date=today + timedelta(days=80),
               status='todo', priority='medium')
    db.session.add_all([t7, t8, t9, t10, t11])
    db.session.flush()

    t7.tags.extend([tag_design])
    t8.tags.extend([tag_backend, tag_infra])
    t9.tags.extend([tag_backend, tag_urgent])
    t10.tags.extend([tag_frontend, tag_v2])
    t11.tags.extend([tag_v2])

    db.session.add_all([
        TaskDependency(task_id=t10.id, depends_on_id=t7.id),  # nav depends on UX research
        TaskDependency(task_id=t9.id, depends_on_id=t8.id),   # sync depends on architecture
        TaskDependency(task_id=t11.id, depends_on_id=t9.id),  # beta depends on sync
        TaskDependency(task_id=t11.id, depends_on_id=t10.id), # beta depends on nav
    ])

    db.session.add_all([
        StatusUpdate(task_id=t7.id, content='Completed 5 user interviews. Synthesizing findings.',
                     created_at=datetime.now() - timedelta(days=3)),
        StatusUpdate(task_id=t8.id, content='Evaluated CRDTs vs operational transforms. Leaning towards CRDTs.',
                     created_at=datetime.now() - timedelta(days=1)),
    ])

    # --- Project 3: Q1 Marketing Campaign ---
    p3 = Project(
        name='Q1 Marketing Campaign',
        description='Multi-channel marketing campaign for the product launch.',
        start_date=today - timedelta(days=45),
        end_date=today - timedelta(days=5),
        status='completed',
    )
    db.session.add(p3)
    db.session.flush()

    t12 = Task(title='Campaign strategy', description='Define target audience, channels, and messaging.',
               project_id=p3.id, assignee_id=eve.id,
               start_date=today - timedelta(days=45), end_date=today - timedelta(days=35),
               status='done', priority='high')
    t13 = Task(title='Creative assets', description='Design banners, social media graphics, and email templates.',
               project_id=p3.id, assignee_id=carol.id,
               start_date=today - timedelta(days=34), end_date=today - timedelta(days=20),
               status='done', priority='medium')
    t14 = Task(title='Campaign execution', description='Launch ads, send emails, post on social media.',
               project_id=p3.id, assignee_id=eve.id,
               start_date=today - timedelta(days=19), end_date=today - timedelta(days=5),
               status='done', priority='high')
    db.session.add_all([t12, t13, t14])
    db.session.flush()

    t13.tags.extend([tag_design])
    t14.tags.extend([tag_urgent])

    db.session.add_all([
        TaskDependency(task_id=t13.id, depends_on_id=t12.id),
        TaskDependency(task_id=t14.id, depends_on_id=t13.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t12.id, content='Strategy approved by leadership.',
                     created_at=datetime.now() - timedelta(days=35)),
        StatusUpdate(task_id=t13.id, content='All assets delivered and approved.',
                     created_at=datetime.now() - timedelta(days=20)),
        StatusUpdate(task_id=t14.id, content='Campaign launched across all channels. Early metrics look good.',
                     created_at=datetime.now() - timedelta(days=15)),
        StatusUpdate(task_id=t14.id, content='Campaign complete. 23% increase in signups vs last quarter.',
                     created_at=datetime.now() - timedelta(days=5)),
    ])

    # --- Project 4: Infrastructure Upgrade ---
    p4 = Project(
        name='Infrastructure Upgrade',
        description='Migrate from legacy infrastructure to Kubernetes with improved CI/CD.',
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=45),
        status='active',
    )
    db.session.add(p4)
    db.session.flush()

    t15 = Task(title='K8s cluster setup', description='Provision and configure Kubernetes cluster.',
               project_id=p4.id, assignee_id=frank.id,
               start_date=today - timedelta(days=5), end_date=today + timedelta(days=10),
               status='in_progress', priority='critical')
    t16 = Task(title='CI/CD pipeline', description='Set up GitHub Actions with automated deployments.',
               project_id=p4.id, assignee_id=bob.id,
               start_date=today + timedelta(days=5), end_date=today + timedelta(days=25),
               status='todo', priority='high')
    t17 = Task(title='Service migration', description='Migrate services one-by-one to new infrastructure.',
               project_id=p4.id, assignee_id=alice.id,
               start_date=today + timedelta(days=20), end_date=today + timedelta(days=40),
               status='todo', priority='high')
    t18 = Task(title='Monitoring setup', description='Set up Prometheus, Grafana, and alerting.',
               project_id=p4.id, assignee_id=frank.id,
               start_date=today + timedelta(days=10), end_date=today + timedelta(days=20),
               status='todo', priority='medium')
    db.session.add_all([t15, t16, t17, t18])
    db.session.flush()

    t15.tags.extend([tag_infra, tag_urgent])
    t16.tags.extend([tag_infra])
    t17.tags.extend([tag_infra, tag_backend])
    t18.tags.extend([tag_infra])

    db.session.add_all([
        TaskDependency(task_id=t16.id, depends_on_id=t15.id),
        TaskDependency(task_id=t17.id, depends_on_id=t16.id),
        TaskDependency(task_id=t18.id, depends_on_id=t15.id),
    ])

    db.session.add_all([
        StatusUpdate(task_id=t15.id, content='Node pool provisioned. Configuring networking and RBAC.',
                     created_at=datetime.now() - timedelta(days=2)),
    ])

    db.session.commit()
    print('Seed data created successfully!')
    print(f'  Teams: 3')
    print(f'  People: 6')
    print(f'  Projects: 4')
    print(f'  Tasks: 18')
    print(f'  Tags: 6')
