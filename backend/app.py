import sys
import json
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app, db
from backend.models import User, Membership, Routine, FitnessProfile, Gym
from sqlalchemy import inspect, text, or_
from backend.utils.tenant import slugify_gym_name
from backend.utils.fitness import get_league_for_level

app = create_app()

def ensure_payment_membership_column():
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('payment')]
    if 'membership_id' not in columns:
        db.session.execute(text('ALTER TABLE payment ADD COLUMN membership_id INTEGER'))
        db.session.commit()

def ensure_membership_price_column():
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('membership')]
    if 'price' not in columns:
        db.session.execute(text('ALTER TABLE membership ADD COLUMN price FLOAT DEFAULT 0.0'))
        db.session.commit()

    prices = {
        'mensual': 119900.0,
        'quincenal': 69900.0,
        'semanal': 44950.0,
        'anual': 299900.0
    }
    memberships = Membership.query.filter(or_(Membership.price == None, Membership.price == 0)).all()
    for membership in memberships:
        membership.price = prices.get(membership.plan, 0.0)
    db.session.commit()

def ensure_multi_tenant_columns():
    inspector = inspect(db.engine)
    tenant_tables = ['user', 'client', 'membership', 'payment', 'routine', 'progress']
    for table_name in tenant_tables:
        columns = [column['name'] for column in inspector.get_columns(table_name)]
        if 'gym_id' not in columns:
            db.session.execute(text(f'ALTER TABLE {table_name} ADD COLUMN gym_id INTEGER'))
    db.session.commit()

    gym_columns = [column['name'] for column in inspector.get_columns('gym')]
    if 'slug' not in gym_columns:
        db.session.execute(text('ALTER TABLE gym ADD COLUMN slug VARCHAR(120)'))
        db.session.commit()

    default_gym = Gym.query.order_by(Gym.id.asc()).first()
    if not default_gym:
        default_gym = Gym(name='Gym Principal', slug='principal', plan='starter')
        db.session.add(default_gym)
        db.session.commit()

    for gym in Gym.query.all():
        if not gym.slug:
            gym.slug = slugify_gym_name(gym.name)
    db.session.commit()

    db.session.execute(text('UPDATE user SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.execute(text('UPDATE client SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.execute(text('UPDATE membership SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.execute(text('UPDATE payment SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.execute(text('UPDATE routine SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.execute(text('UPDATE progress SET gym_id = :gym_id WHERE gym_id IS NULL'), {'gym_id': default_gym.id})
    db.session.commit()

def ensure_super_admin_and_approval_columns():
    inspector = inspect(db.engine)
    user_columns = [column['name'] for column in inspector.get_columns('user')]
    if 'is_super_admin' not in user_columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN is_super_admin BOOLEAN DEFAULT 0'))
    gym_columns = [column['name'] for column in inspector.get_columns('gym')]
    if 'approved' not in gym_columns:
        db.session.execute(text('ALTER TABLE gym ADD COLUMN approved BOOLEAN DEFAULT 0'))
    db.session.commit()

    admin_user = User.query.filter_by(username='admin').first()
    if admin_user and not admin_user.is_super_admin:
        admin_user.is_super_admin = True
        db.session.commit()
        print('Usuario admin actualizado a super_admin')


def ensure_fitness_social_tables():
    from sqlalchemy import inspect as _inspect
    inspector = _inspect(db.engine)
    existing = inspector.get_table_names()

    if 'fitness_league' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_league (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(64) NOT NULL UNIQUE,
                min_level INTEGER DEFAULT 1,
                max_level INTEGER DEFAULT 999,
                icon VARCHAR(16) DEFAULT '🥉',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        db.session.execute(text("INSERT INTO fitness_league (name, min_level, max_level, icon) VALUES ('Bronce', 1, 4, '🥉')"))
        db.session.execute(text("INSERT INTO fitness_league (name, min_level, max_level, icon) VALUES ('Plata', 5, 9, '🥈')"))
        db.session.execute(text("INSERT INTO fitness_league (name, min_level, max_level, icon) VALUES ('Oro', 10, 14, '🥇')"))
        db.session.execute(text("INSERT INTO fitness_league (name, min_level, max_level, icon) VALUES ('Titan', 15, 999, '💎')"))

    if 'fitness_league_member' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_league_member (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL REFERENCES fitness_league(id),
                user_id INTEGER NOT NULL REFERENCES user(id),
                season INTEGER DEFAULT 1,
                xp_earned INTEGER DEFAULT 0,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, season)
            )
        '''))

    if 'fitness_social_connection' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_social_connection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL REFERENCES user(id),
                followed_id INTEGER NOT NULL REFERENCES user(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, followed_id)
            )
        '''))

    if 'fitness_challenge' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_challenge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL REFERENCES user(id),
                name VARCHAR(160) NOT NULL,
                description TEXT,
                goal_type VARCHAR(32) NOT NULL,
                goal_value INTEGER NOT NULL,
                xp_reward INTEGER DEFAULT 200,
                start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_date DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))

    if 'fitness_challenge_participant' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_challenge_participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id INTEGER NOT NULL REFERENCES fitness_challenge(id),
                user_id INTEGER NOT NULL REFERENCES user(id),
                progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT 0,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(challenge_id, user_id)
            )
        '''))

    if 'fitness_feed_post' not in existing:
        db.session.execute(text('''
            CREATE TABLE fitness_feed_post (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES user(id),
                type VARCHAR(32) NOT NULL,
                message VARCHAR(280) NOT NULL,
                metadata_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))

    for t in ('fitness_routine_exercise', 'fitness_exercise', 'fitness_routine'):
        if t in inspector.get_table_names():
            db.session.execute(text(f'DROP TABLE IF EXISTS {t}'))

    if 'fitness_workout_session' in inspector.get_table_names():
        db.session.execute(text('DROP TABLE IF EXISTS fitness_workout_session'))

    from backend.models import League as _League, LeagueMember as _LM, FitnessProfile as _FP, WorkoutSession as _WS, BodyProgress as _BP
    db.create_all()
    for user in User.query.all():
        existing_member = _LM.query.filter_by(user_id=user.id, season=1).first()
        if not existing_member:
            profile = _FP.query.filter_by(user_id=user.id).first()
            level = profile.level if profile else 1
            league_name = get_league_for_level(level)
            league = _League.query.filter_by(name=league_name).first()
            if league:
                db.session.add(_LM(user_id=user.id, league_id=league.id, season=1, xp_earned=profile.xp if profile else 0))
    db.session.commit()


if __name__ == '__main__':
    import subprocess, sys
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(backend_dir, '..', 'frontend')
    dist_dir = os.path.join(frontend_dir, 'dist')
    if not os.path.isdir(dist_dir):
        print('Construyendo frontend React...')
        env = os.environ.copy()
        env['PATH'] = r'C:\Program Files\nodejs;' + env.get('PATH', '')
        result = subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print('Error al construir frontend:', result.stderr)
            sys.exit(1)
        print('Frontend construido correctamente')

    with app.app_context():
        db.create_all()
        ensure_payment_membership_column()
        ensure_membership_price_column()
        ensure_super_admin_and_approval_columns()
        ensure_multi_tenant_columns()
        ensure_fitness_social_tables()

        if not User.query.filter_by(username='admin').first():
            default_gym = Gym.query.order_by(Gym.id.asc()).first()
            admin = User(username='admin', email='admin@evofit.com', role='admin', is_super_admin=True, gym_id=(default_gym.id if default_gym else None))
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Super administrador creado: admin / admin123')

        default_gym = Gym.query.order_by(Gym.id.asc()).first()
        if default_gym and not default_gym.approved:
            default_gym.approved = True
            db.session.commit()

        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            from backend.models import Client as _Client
            admin_client = _Client.query.filter_by(email=admin_user.email).first()
            if not admin_client and default_gym:
                admin_client = _Client(
                    gym_id=default_gym.id,
                    name=admin_user.username,
                    email=admin_user.email,
                    membership_status='active',
                )
                db.session.add(admin_client)
                db.session.commit()

            if admin_client and not Routine.query.filter_by(client_id=admin_client.id).first():
                routines_data = [
                    {
                        'name': 'Full Body Quemador',
                        'category': 'fullbody',
                        'exercises': [
                            {'name': 'Sentadilla profunda', 'sets': 4, 'reps': 12, 'rest_seconds': 60, 'muscles': 'Pierna,Glúteos'},
                            {'name': 'Press banca con barra', 'sets': 4, 'reps': 10, 'rest_seconds': 60, 'muscles': 'Pecho,Tríceps'},
                            {'name': 'Remo con barra', 'sets': 3, 'reps': 12, 'rest_seconds': 45, 'muscles': 'Espalda,Bíceps'},
                            {'name': 'Press militar', 'sets': 3, 'reps': 10, 'rest_seconds': 60, 'muscles': 'Hombro,Tríceps'},
                            {'name': 'Plancha', 'sets': 3, 'reps': 30, 'rest_seconds': 30, 'muscles': 'Core'},
                        ],
                    },
                    {
                        'name': 'Pecho y Tríceps',
                        'category': 'pecho',
                        'exercises': [
                            {'name': 'Press banca con barra', 'sets': 4, 'reps': 10, 'rest_seconds': 90, 'muscles': 'Pecho,Tríceps'},
                            {'name': 'Fondos en paralelas', 'sets': 3, 'reps': 12, 'rest_seconds': 60, 'muscles': 'Pecho,Tríceps'},
                            {'name': 'Press militar', 'sets': 3, 'reps': 10, 'rest_seconds': 60, 'muscles': 'Hombro,Tríceps'},
                            {'name': 'Elevación lateral', 'sets': 3, 'reps': 15, 'rest_seconds': 30, 'muscles': 'Hombro'},
                        ],
                    },
                    {
                        'name': 'Pierna Extrema',
                        'category': 'pierna',
                        'exercises': [
                            {'name': 'Sentadilla profunda', 'sets': 5, 'reps': 10, 'rest_seconds': 90, 'muscles': 'Pierna,Glúteos'},
                            {'name': 'Peso muerto', 'sets': 4, 'reps': 8, 'rest_seconds': 90, 'muscles': 'Espalda,Pierna,Glúteos'},
                            {'name': 'Elevación lateral', 'sets': 3, 'reps': 15, 'rest_seconds': 45, 'muscles': 'Hombro'},
                            {'name': 'Plancha', 'sets': 3, 'reps': 45, 'rest_seconds': 30, 'muscles': 'Core'},
                        ],
                    },
                    {
                        'name': 'Espalda y Bíceps',
                        'category': 'espalda',
                        'exercises': [
                            {'name': 'Dominadas', 'sets': 3, 'reps': 8, 'rest_seconds': 60, 'muscles': 'Espalda,Bíceps'},
                            {'name': 'Remo con barra', 'sets': 3, 'reps': 12, 'rest_seconds': 60, 'muscles': 'Espalda,Bíceps'},
                            {'name': 'Curl de bíceps', 'sets': 3, 'reps': 12, 'rest_seconds': 45, 'muscles': 'Bíceps'},
                            {'name': 'Plancha', 'sets': 3, 'reps': 30, 'rest_seconds': 30, 'muscles': 'Core'},
                        ],
                    },
                ]

                for rd in routines_data:
                    routine = Routine(
                        gym_id=default_gym.id,
                        client_id=admin_client.id,
                        name=rd['name'],
                        category=rd['category'],
                        exercises=json.dumps(rd['exercises']),
                    )
                    db.session.add(routine)

                db.session.commit()
                print('Rutinas de ejemplo creadas para admin')

        from backend.models import WorkoutSession as _WS, FitnessProfile as _FP, LeagueMember as _LM
        from backend.utils.fitness import compute_level_from_xp
        if not _WS.query.first():
            users = User.query.all()
            import random
            for u in users:
                profile = _FP.query.filter_by(user_id=u.id).first()
                xp = 0
                for day_offset in range(7):
                    start = datetime.utcnow() - timedelta(days=day_offset, hours=random.randint(0, 23))
                    duration = random.randint(1200, 3600)
                    ws = _WS(
                        user_id=u.id,
                        routine_id=None,
                        started_at=start,
                        finished_at=start + timedelta(seconds=duration),
                        total_seconds=duration,
                        kcal_burned=random.randint(150, 500),
                        xp_gained=random.randint(30, 120),
                    )
                    db.session.add(ws)
                    xp += ws.xp_gained
                if profile:
                    profile.xp = xp
                    profile.level = compute_level_from_xp(xp)
                    profile.weekly_minutes = random.randint(60, 300)
                    profile.weekly_calories = random.randint(500, 2500)
                    profile.streak_days = random.randint(1, 14)
                member = _LM.query.filter_by(user_id=u.id, season=1).first()
                if member:
                    member.xp_earned = xp
            db.session.commit()
            print(f'Datos de ranking sembrados para {len(users)} usuarios')

    app.run(debug=True)
