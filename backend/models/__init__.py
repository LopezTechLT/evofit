from backend import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import UniqueConstraint

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Gym(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    plan = db.Column(db.String(50), default='starter')
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), default='user')  # admin, trainer, user
    is_super_admin = db.Column(db.Boolean, default=False)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    gym = db.relationship('Gym', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    goal = db.Column(db.String(100))  # bajar peso, ganar masa, mantener
    photo = db.Column(db.String(200))
    membership_status = db.Column(db.String(50), default='active')
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code = db.Column(db.String(200), unique=True)
    gym = db.relationship('Gym', backref='clients')

    # Relationships
    memberships = db.relationship('Membership', backref='client', lazy=True)
    payments = db.relationship('Payment', backref='client', lazy=True)
    routines = db.relationship('Routine', backref='client', lazy=True)
    progress = db.relationship('Progress', backref='client', lazy=True)

class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    plan = db.Column(db.String(100))  # mensual, quincenal, semanal, anual
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='active')
    price = db.Column(db.Float, default=0.0)
    payments = db.relationship('Payment', backref='membership', lazy=True)
    gym = db.relationship('Gym', backref='memberships')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    membership_id = db.Column(db.Integer, db.ForeignKey('membership.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(100))  # efectivo, tarjeta, etc.
    description = db.Column(db.String(200))
    gym = db.relationship('Gym', backref='payments')

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100))  # pecho, espalda, pierna, cardio
    day_of_week = db.Column(db.Integer, nullable=True)  # 0=Lunes ... 6=Domingo
    exercises = db.Column(db.Text)  # JSON string of exercises
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    gym = db.relationship('Gym', backref='routines')

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gym_id = db.Column(db.Integer, db.ForeignKey('gym.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    weight = db.Column(db.Float)
    imc = db.Column(db.Float)
    measurements = db.Column(db.Text)  # JSON string of measurements
    gym = db.relationship('Gym', backref='progress_items')

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clients = db.relationship('Client', secondary='trainer_clients', backref='trainers')

trainer_clients = db.Table('trainer_clients',
    db.Column('trainer_id', db.Integer, db.ForeignKey('trainer.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('client.id'), primary_key=True)
)

# -----------------------------
# Fitness "app-like" subsystem
# -----------------------------

class FitnessProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak_days = db.Column(db.Integer, default=0)
    last_workout_date = db.Column(db.DateTime, nullable=True)

    weekly_minutes = db.Column(db.Integer, default=0)
    weekly_calories = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref=db.backref('fitness_profile', uselist=False))


class WorkoutSession(db.Model):
    __tablename__ = 'fitness_workout_session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=True)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    total_seconds = db.Column(db.Integer, default=0)
    kcal_burned = db.Column(db.Integer, default=0)
    xp_gained = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='workout_sessions')
    routine = db.relationship('Routine', lazy=True)


class BodyProgress(db.Model):
    __tablename__ = 'fitness_body_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    imc = db.Column(db.Float, nullable=True)

    minutes_trained = db.Column(db.Integer, default=0)
    kcal_burned = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='body_progress')


class Achievement(db.Model):
    __tablename__ = 'fitness_achievement'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)  # e.g. first_workout
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(64), nullable=True)  # emoji/name


class UserAchievement(db.Model):
    __tablename__ = 'fitness_user_achievement'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('fitness_achievement.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='achievements')
    achievement = db.relationship('Achievement', lazy=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_id', name='uq_fitness_user_achievement'),
    )


# -----------------------------
# Social, Leagues & Challenges
# -----------------------------

class League(db.Model):
    __tablename__ = 'fitness_league'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)  # Bronce, Plata, Oro, Titan
    min_level = db.Column(db.Integer, default=1)
    max_level = db.Column(db.Integer, default=999)
    icon = db.Column(db.String(16), default='🥉')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('LeagueMember', backref='league', lazy=True)


class LeagueMember(db.Model):
    __tablename__ = 'fitness_league_member'

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('fitness_league.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    season = db.Column(db.Integer, default=1)
    xp_earned = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='league_memberships')

    __table_args__ = (
        UniqueConstraint('user_id', 'season', name='uq_league_member_season'),
    )


class SocialConnection(db.Model):
    __tablename__ = 'fitness_social_connection'

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    followed = db.relationship('User', foreign_keys=[followed_id], backref='followers')

    __table_args__ = (
        UniqueConstraint('follower_id', 'followed_id', name='uq_social_connection'),
    )


class Challenge(db.Model):
    __tablename__ = 'fitness_challenge'

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    goal_type = db.Column(db.String(32), nullable=False)  # workouts, days_streak, kcal, xp
    goal_value = db.Column(db.Integer, nullable=False)
    xp_reward = db.Column(db.Integer, default=200)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='created_challenges')
    participants = db.relationship('ChallengeParticipant', backref='challenge', lazy=True)


class ChallengeParticipant(db.Model):
    __tablename__ = 'fitness_challenge_participant'

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('fitness_challenge.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='challenge_participations')

    __table_args__ = (
        UniqueConstraint('challenge_id', 'user_id', name='uq_challenge_participant'),
    )


class FeedPost(db.Model):
    __tablename__ = 'fitness_feed_post'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # workout, achievement, level_up, streak, challenge
    message = db.Column(db.String(280), nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)  # JSON with extra data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='feed_posts')
