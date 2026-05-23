"""Add 30 test clients to the main gym for testing"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app, db
from backend.models import Gym, User, Client, Membership, Payment, FitnessProfile, Routine
from datetime import datetime, timedelta
import random

app = create_app()

GOALS = ['bajar peso', 'ganar masa', 'mantener', 'tonificar', 'resistencia']
PLANS = ['semanal', 'quincenal', 'mensual']
METHODS = ['efectivo', 'tarjeta', 'transferencia']
FIRST_NAMES = ['Carlos','Maria','Juan','Ana','Luis','Sofia','Pedro','Laura','Diego','Valentina',
               'Andres','Camila','Jorge','Isabella','Miguel','Gabriela','David','Sara','Felipe','Daniela',
               'Alex','Paula','Oscar','Mariana','Hugo','Luz','Pablo','Rosa','Santiago','Elena']
LAST_NAMES = ['Garcia','Rodriguez','Martinez','Lopez','Gonzalez','Perez','Sanchez','Ramirez','Torres','Flores',
              'Rivera','Gomez','Diaz','Cruz','Morales','Ortiz','Reyes','Castillo','Vargas','Mendoza']

def seed():
    gym = Gym.query.order_by(Gym.id.asc()).first()
    if not gym:
        print('No gym found! Run the main seed first.')
        return

    gym_id = gym.id
    existing = Client.query.filter_by(gym_id=gym_id).count()
    need = max(0, 30 - existing)
    if need == 0:
        print(f'Already have {existing} clients in {gym.name}, no more needed.')
        return

    print(f'Adding {need} test clients to {gym.name}...')
    used = {c.email for c in Client.query.filter_by(gym_id=gym_id).all()}

    for i in range(need):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f'{first.lower()}.{last.lower()}{i}@test.com'
        if email in used:
            email = f'{first.lower()}{i}{last.lower()}@test.com'
        used.add(email)

        client = Client(
            gym_id=gym_id, name=first, email=email,
            phone=f'+57{random.randint(300000000, 399999999)}',
            age=random.randint(16, 60),
            weight=round(random.uniform(50, 100), 1),
            height=round(random.uniform(1.50, 1.90), 2),
            goal=random.choice(GOALS),
            membership_status='active' if random.random() < 0.8 else 'inactive',
            registration_date=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
        )
        db.session.add(client)
        db.session.flush()

        # Create a matching User for each client (logins: test1..test30 / pass123)
        username = f'test{i+1}'
        user = User(username=username, email=email, role='user', gym_id=gym_id)
        user.set_password('pass123')
        db.session.add(user)
        db.session.flush()

        # Fitness profile
        fp = FitnessProfile(user_id=user.id, xp=random.randint(0, 2000), level=1,
                           streak_days=random.randint(0, 14),
                           weekly_minutes=random.randint(0, 300),
                           weekly_calories=random.randint(0, 2000))
        db.session.add(fp)

        # Add a plan membership if active
        if client.membership_status == 'active':
            plan = random.choice(PLANS)
            price = {'semanal': 44950, 'quincenal': 69900, 'mensual': 119900}[plan]
            start = client.registration_date
            duration = {'semanal': 7, 'quincenal': 14, 'mensual': 30}[plan]
            membership = Membership(
                gym_id=gym_id, client_id=client.id,
                plan=plan, price=price,
                start_date=start, end_date=start + timedelta(days=duration),
            )
            db.session.add(membership)
            db.session.flush()

            # Payment
            pay = Payment(
                gym_id=gym_id, client_id=client.id, membership_id=membership.id,
                amount=price, method=random.choice(METHODS),
                date=start, description=f'Pago {plan}'
            )
            db.session.add(pay)

        # Default routines for fitness app
        defaults = [
            (0, 'Full Body', json.dumps([
                {'name': 'Sentadilla', 'sets': 3, 'reps': 12, 'rest_seconds': 60},
                {'name': 'Press banca', 'sets': 3, 'reps': 10, 'rest_seconds': 60},
                {'name': 'Remo', 'sets': 3, 'reps': 12, 'rest_seconds': 45},
            ])),
            (1, 'Cardio', json.dumps([
                {'name': 'Saltos', 'sets': 3, 'reps': 30, 'rest_seconds': 30},
                {'name': 'Burpees', 'sets': 3, 'reps': 10, 'rest_seconds': 45},
                {'name': 'Plancha', 'sets': 3, 'reps': 30, 'rest_seconds': 30},
            ])),
        ]
        for dw, rname, rex in defaults:
            r = Routine(client_id=client.id, gym_id=gym_id, name=rname,
                       category='fullbody' if dw == 0 else 'cardio',
                       exercises=rex, day_of_week=dw)
            db.session.add(r)

        print(f'  [{i+1}/{need}] {client.name} {last} ({username} / pass123)')

    db.session.commit()
    print(f'Done! Total clients in {gym.name}: {Client.query.filter_by(gym_id=gym_id).count()}')
    print('Logins: test1..test30 / pass123')

if __name__ == '__main__':
    with app.app_context():
        seed()
    print('Seed completed.')
