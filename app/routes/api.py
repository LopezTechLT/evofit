from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

import json as json_lib

from app import db
from app.models import (
    FitnessProfile,
    WorkoutSession,
    BodyProgress,
    Achievement,
    UserAchievement,
    Client,
    Routine,
    League,
    LeagueMember,
    SocialConnection,
    Challenge,
    ChallengeParticipant,
    FeedPost,
    User,
)
from app.utils.fitness import (
    compute_level_from_xp,
    compute_xp_to_next,
    get_level_title,
    get_league_for_level,
    is_same_day,
    is_yesterday,
)
from app.utils.tenant import get_current_gym_id

api = Blueprint('api', __name__, url_prefix='/api')


def _current_client() -> Client | None:
    return Client.query.filter_by(email=current_user.email, gym_id=get_current_gym_id()).first()


def _client_routine_to_card(r: Routine) -> dict:
    return _routine_to_dict(r)


def _ensure_default_routines(client: Client):
    if not client or Routine.query.filter_by(client_id=client.id).first():
        return
    routines_data = [
        {
            'name': 'Full Body Quemador',
            'category': 'fullbody',
            'exercises': [
                {'name': 'Sentadilla', 'sets': 3, 'reps': 12, 'rest_seconds': 60, 'muscles': 'Pierna,Glúteos'},
                {'name': 'Press banca', 'sets': 3, 'reps': 10, 'rest_seconds': 60, 'muscles': 'Pecho,Tríceps'},
                {'name': 'Remo con barra', 'sets': 3, 'reps': 12, 'rest_seconds': 45, 'muscles': 'Espalda,Bíceps'},
                {'name': 'Plancha', 'sets': 3, 'reps': 30, 'rest_seconds': 30, 'muscles': 'Core'},
            ],
        },
        {
            'name': 'Cardio Quemagrasa',
            'category': 'cardio',
            'exercises': [
                {'name': 'Saltos de tijera', 'sets': 3, 'reps': 30, 'rest_seconds': 30, 'muscles': 'Pierna,Cardio'},
                {'name': 'Burpees', 'sets': 3, 'reps': 10, 'rest_seconds': 45, 'muscles': 'Full Body,Cardio'},
                {'name': 'Mountain climbers', 'sets': 3, 'reps': 20, 'rest_seconds': 30, 'muscles': 'Core,Cardio'},
                {'name': 'Plancha', 'sets': 3, 'reps': 30, 'rest_seconds': 30, 'muscles': 'Core'},
            ],
        },
    ]
    for rd in routines_data:
        r = Routine(
            gym_id=client.gym_id,
            client_id=client.id,
            name=rd['name'],
            category=rd['category'],
            exercises=json_lib.dumps(rd['exercises']),
        )
        db.session.add(r)
    db.session.commit()


def _ensure_profile(user_id: int) -> FitnessProfile:
    profile = FitnessProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile
    profile = FitnessProfile(user_id=user_id, xp=0, level=1, streak_days=0)
    db.session.add(profile)
    db.session.commit()
    return profile


def _parse_routine_exercises(r: Routine) -> list[dict]:
    if not r.exercises:
        return []
    try:
        parsed = json_lib.loads(r.exercises)
        if not isinstance(parsed, list):
            return []
        return parsed
    except (json_lib.JSONDecodeError, TypeError):
        return []


def _routine_to_dict(r: Routine) -> dict:
    exercises = _parse_routine_exercises(r)
    count = len(exercises)
    duration = max(10, count * 5)
    estimated = max(80, duration * 6)
    difficulty = 'Principiante' if count <= 5 else 'Intermedio' if count <= 9 else 'Avanzado'
    focus = (r.category or '').capitalize() if r.category else 'Rutina'
    return {
        'id': r.id,
        'name': r.name,
        'coverImage': None,
        'difficulty': difficulty,
        'durationMinutes': duration,
        'exercisesCount': count,
        'estimatedKcal': estimated,
        'focus': focus,
    }


def _routine_detail_to_dict(r: Routine) -> dict:
    exercises = _parse_routine_exercises(r)
    normalized = []
    for i, ex in enumerate(exercises):
        if not isinstance(ex, dict):
            continue
        name = str(ex.get('name') or '').strip()
        if not name:
            continue
        normalized.append({
            'id': i + 1,
            'name': name,
            'mediaUrl': None,
            'instructions': ex.get('instructions') or '',
            'muscles': [m.strip() for m in (ex.get('muscles') or '').split(',') if m.strip()],
            'sets': int(ex.get('sets') or 3),
            'reps': int(ex.get('reps') or 12),
            'restSeconds': int(ex.get('rest_seconds') or ex.get('restSeconds') or 60),
            'notes': ex.get('notes'),
            'order': i,
        })
    return {
        **_routine_to_dict(r),
        'exercises': normalized,
    }


def _ensure_achievements_catalog():
    if Achievement.query.count() > 0:
        return
    db.session.add_all(
        [
            Achievement(code='first_workout', name='Primer entrenamiento', description='Completaste tu primer entrenamiento.', icon='🏆'),
            Achievement(code='streak_7', name='Racha 7 días', description='Entrenaste 7 días seguidos.', icon='🔥'),
        ]
    )
    db.session.commit()


@api.get('/health')
def health():
    return jsonify({'ok': True, 'service': 'evofit-api', 'ts': datetime.utcnow().isoformat()})


@api.get('/me')
@login_required
def me():
    _ensure_achievements_catalog()
    profile = _ensure_profile(current_user.id)
    profile.level = compute_level_from_xp(profile.xp)
    db.session.commit()

    member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
    league_name = member.league.name if member else get_league_for_level(profile.level)
    league_icon = member.league.icon if member else '🥉'

    return jsonify(
        {
            'id': current_user.id,
            'username': current_user.username,
            'role': current_user.role,
            'title': get_level_title(profile.level),
            'league': league_name,
            'leagueIcon': league_icon,
            'fitness': {
                'xp': profile.xp,
                'level': profile.level,
                'xpToNext': compute_xp_to_next(profile.level, profile.xp),
                'streakDays': profile.streak_days,
                'weeklyMinutes': profile.weekly_minutes,
                'weeklyCalories': profile.weekly_calories,
            },
        }
    )


@api.get('/fitness/dashboard')
@login_required
def fitness_dashboard():
    _ensure_achievements_catalog()
    profile = _ensure_profile(current_user.id)

    # routine of the day: naive pick based on weekday
    client = _current_client()
    _ensure_default_routines(client)
    routines = Routine.query.filter_by(client_id=client.id).order_by(Routine.id.asc()).all() if client else []
    routine_today = routines[datetime.utcnow().weekday() % max(1, len(routines))] if routines else None

    # weekly stats: last 7 days
    since = datetime.utcnow() - timedelta(days=7)
    sessions = WorkoutSession.query.filter(WorkoutSession.user_id == current_user.id, WorkoutSession.started_at >= since).all()
    weekly_minutes = sum(int((s.total_seconds or 0) / 60) for s in sessions)
    weekly_kcal = sum(int(s.kcal_burned or 0) for s in sessions)

    # persist weekly snapshot for UI
    profile.weekly_minutes = weekly_minutes
    profile.weekly_calories = weekly_kcal
    profile.level = compute_level_from_xp(profile.xp)
    db.session.commit()

    return jsonify(
        {
            'greeting': _greeting_for_hour(),
            'routineOfDay': _routine_to_dict(routine_today) if routine_today else None,
            'weekly': {
                'minutes': weekly_minutes,
                'kcal': weekly_kcal,
                'sessions': len(sessions),
            },
            'streakDays': profile.streak_days,
            'level': profile.level,
            'xp': profile.xp,
            'xpToNext': compute_xp_to_next(profile.level, profile.xp),
        }
    )


def _greeting_for_hour() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return 'Buenos días'
    if hour < 18:
        return 'Buenas tardes'
    return 'Buenas noches'


@api.get('/fitness/routines')
@login_required
def fitness_routines():
    client = _current_client()
    if not client:
        return jsonify({'items': []})
    _ensure_default_routines(client)
    routines = Routine.query.filter_by(client_id=client.id).order_by(Routine.id.desc()).all()
    return jsonify({'items': [_routine_to_dict(r) for r in routines]})


@api.get('/client/routines')
@login_required
def client_routines():
    client = _current_client()
    if not client:
        return jsonify({'items': []})
    _ensure_default_routines(client)

    routines = Routine.query.filter_by(client_id=client.id).order_by(Routine.id.desc()).all()
    return jsonify({'items': [_client_routine_to_card(r) for r in routines]})


@api.get('/client/routines/<int:routine_id>')
@login_required
def client_routine_detail(routine_id: int):
    client = _current_client()
    if not client:
        return jsonify({'error': 'not_found'}), 404

    routine = Routine.query.get_or_404(routine_id)
    if routine.client_id != client.id:
        return jsonify({'error': 'forbidden'}), 403

    return jsonify(_routine_detail_to_dict(routine))

@api.get('/fitness/routines/<int:routine_id>')
@login_required
def fitness_routine_detail(routine_id: int):
    client = _current_client()
    routine = Routine.query.get_or_404(routine_id)
    if client and routine.client_id != client.id:
        return jsonify({'error': 'forbidden'}), 403
    return jsonify(_routine_detail_to_dict(routine))


@api.post('/fitness/workouts/start')
@login_required
def fitness_workout_start():
    payload = request.get_json(silent=True) or {}
    routine_id = payload.get('routineId')

    session = WorkoutSession(user_id=current_user.id, routine_id=routine_id, started_at=datetime.utcnow())
    db.session.add(session)
    db.session.commit()
    return jsonify({'sessionId': session.id})


@api.post('/fitness/workouts/<int:session_id>/finish')
@login_required
def fitness_workout_finish(session_id: int):
    payload = request.get_json(silent=True) or {}
    total_seconds = int(payload.get('totalSeconds') or 0)
    kcal_burned = int(payload.get('kcalBurned') or 0)

    session = WorkoutSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    session.finished_at = datetime.utcnow()
    session.total_seconds = max(0, total_seconds)
    session.kcal_burned = max(0, kcal_burned)

    xp_gained = max(10, min(250, int((session.total_seconds / 60) * 5)))
    session.xp_gained = xp_gained

    profile = _ensure_profile(current_user.id)
    now = datetime.utcnow()

    # streak logic
    if profile.last_workout_date is None:
        profile.streak_days = 1
    else:
        if is_same_day(profile.last_workout_date, now):
            pass
        elif is_yesterday(now, profile.last_workout_date):
            profile.streak_days = int(profile.streak_days or 0) + 1
        else:
            profile.streak_days = 1

    profile.last_workout_date = now
    profile.xp = int(profile.xp or 0) + xp_gained
    profile.level = compute_level_from_xp(profile.xp)

    # Sync LeagueMember xp_earned
    member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
    if member:
        member.xp_earned = profile.xp

    # unlock achievements
    _unlock_achievement_if_needed(current_user.id, 'first_workout', condition=True)
    _unlock_achievement_if_needed(current_user.id, 'streak_7', condition=profile.streak_days >= 7)

    old_level = compute_level_from_xp(int(profile.xp or 0) - xp_gained)
    level_ups = profile.level - old_level

    # progress snapshot
    db.session.add(
        BodyProgress(
            user_id=current_user.id,
            date=now,
            weight_kg=None,
            height_cm=None,
            imc=None,
            minutes_trained=int(session.total_seconds / 60),
            kcal_burned=session.kcal_burned,
        )
    )

    # Feed post
    _create_feed_post(
        current_user.id, 'workout',
        f'{current_user.username} completó un entrenamiento 🔥',
        {'xp': xp_gained, 'kcal': kcal_burned, 'seconds': total_seconds},
    )

    # Level-up feed post
    if level_ups > 0:
        _create_feed_post(
            current_user.id, 'level_up',
            f'{current_user.username} subió a nivel {profile.level} ({get_level_title(profile.level)}) 🏆',
            {'level': profile.level, 'title': get_level_title(profile.level)},
        )
        # Auto promote league
        member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
        target_league = get_league_for_level(profile.level)
        league = League.query.filter_by(name=target_league).first()
        if member and league and member.league_id != league.id:
            member.league_id = league.id
            _create_feed_post(
                current_user.id, 'league_up',
                f'{current_user.username} ascendió a liga {league.name} {league.icon}',
            )

    db.session.commit()
    return jsonify(
        {
            'ok': True,
            'xpGained': xp_gained,
            'level': profile.level,
            'streakDays': profile.streak_days,
            'leveledUp': level_ups > 0,
            'title': get_level_title(profile.level),
        }
    )


def _unlock_achievement_if_needed(user_id: int, code: str, condition: bool):
    if not condition:
        return
    achievement = Achievement.query.filter_by(code=code).first()
    if not achievement:
        return
    exists = UserAchievement.query.filter_by(user_id=user_id, achievement_id=achievement.id).first()
    if exists:
        return
    db.session.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))


@api.get('/fitness/progress/weekly')
@login_required
def fitness_progress_weekly():
    since = datetime.utcnow() - timedelta(days=7)
    items = (
        BodyProgress.query.filter(BodyProgress.user_id == current_user.id, BodyProgress.date >= since)
        .order_by(BodyProgress.date.asc())
        .all()
    )
    return jsonify(
        {
            'items': [
                {
                    'date': p.date.date().isoformat(),
                    'minutes': int(p.minutes_trained or 0),
                    'kcal': int(p.kcal_burned or 0),
                    'weightKg': p.weight_kg,
                    'imc': p.imc,
                }
                for p in items
            ]
        }
    )


@api.get('/fitness/achievements')
@login_required
def fitness_achievements():
    catalog = Achievement.query.order_by(Achievement.id.asc()).all()
    unlocked = UserAchievement.query.filter_by(user_id=current_user.id).all()
    unlocked_ids = {u.achievement_id for u in unlocked}
    return jsonify(
        {
            'items': [
                {
                    'code': a.code,
                    'name': a.name,
                    'description': a.description,
                    'icon': a.icon,
                    'unlocked': a.id in unlocked_ids,
                }
                for a in catalog
            ]
        }
    )


@api.post('/fitness/routines/generate')
@login_required
def fitness_generate_routine():
    payload = request.get_json(silent=True) or {}
    goal = (payload.get('goal') or 'mantener').strip().lower()
    experience = (payload.get('experience') or 'intermedio').strip().lower()
    days = int(payload.get('daysAvailable') or 3)

    focus = 'Full Body'
    if goal in ('ganar masa muscular', 'masa', 'musculo', 'músculo'):
        focus = 'Hipertrofia'
    elif goal in ('perder grasa', 'grasa', 'definicion', 'definición'):
        focus = 'Quema grasa'
    elif goal in ('resistencia',):
        focus = 'Resistencia'

    duration = 25 if experience == 'principiante' else 40 if experience == 'avanzado' else 35
    estimated = 180 if duration <= 25 else 320 if duration >= 40 else 260
    difficulty = 'Principiante' if experience == 'principiante' else 'Avanzado' if experience == 'avanzado' else 'Intermedio'

    return jsonify(
        {
            'name': f'Rutina {focus} ({days} días)',
            'focus': focus,
            'difficulty': difficulty,
            'durationMinutes': duration,
            'estimatedKcal': estimated,
            'recommendation': {
                'daysSplit': _days_split(days, focus),
            },
        }
    )


def _days_split(days: int, focus: str) -> list[str]:
    if days <= 2:
        return ['Full Body A', 'Full Body B']
    if days == 3:
        return ['Empuje', 'Tirón', 'Pierna']
    if days == 4:
        return ['Superior', 'Inferior', 'Superior', 'Inferior']
    return ['Empuje', 'Tirón', 'Pierna', 'Core + Cardio', 'Full Body']


# ---------------------------------------------------------------------------
# LEADERBOARD & LEAGUES
# ---------------------------------------------------------------------------

@api.get('/leaderboard')
@login_required
def leaderboard():
    period = request.args.get('period', 'weekly')  # weekly, monthly, all
    since = datetime.utcnow()
    if period == 'weekly':
        since -= timedelta(days=7)
    elif period == 'monthly':
        since -= timedelta(days=30)

    query = db.session.query(
        User.id,
        User.username,
        db.func.coalesce(db.func.sum(WorkoutSession.xp_gained), 0).label('xp'),
        db.func.coalesce(db.func.sum(WorkoutSession.kcal_burned), 0).label('kcal'),
        db.func.count(WorkoutSession.id).label('sessions'),
    ).join(WorkoutSession, WorkoutSession.user_id == User.id)

    if period != 'all':
        query = query.filter(WorkoutSession.started_at >= since)

    rows = query.group_by(User.id).order_by(db.desc('xp')).limit(50).all()

    return jsonify({
        'period': period,
        'items': [
            {
                'rank': i + 1,
                'userId': r.id,
                'username': r.username,
                'xp': int(r.xp),
                'kcal': int(r.kcal),
                'sessions': int(r.sessions),
            }
            for i, r in enumerate(rows)
        ],
    })


@api.get('/leagues/my')
@login_required
def my_league():
    member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
    if not member:
        profile = _ensure_profile(current_user.id)
        league_name = get_league_for_level(profile.level)
        league = League.query.filter_by(name=league_name).first()
        if not league:
            return jsonify({'error': 'no_league'}), 404
        member = LeagueMember(user_id=current_user.id, league_id=league.id, season=1, xp_earned=profile.xp)
        db.session.add(member)
        db.session.commit()
    else:
        league = member.league

    # members sorted by xp
    members = (
        db.session.query(LeagueMember, User.username)
        .join(User, User.id == LeagueMember.user_id)
        .filter(LeagueMember.league_id == league.id, LeagueMember.season == 1)
        .order_by(LeagueMember.xp_earned.desc())
        .all()
    )

    profile = _ensure_profile(current_user.id)

    return jsonify({
        'league': {
            'id': league.id,
            'name': league.name,
            'icon': league.icon,
        },
        'myRank': next((i + 1 for i, (m, _) in enumerate(members) if m.user_id == current_user.id), None),
        'myXp': member.xp_earned,
        'memberCount': len(members),
        'items': [
            {
                'rank': i + 1,
                'userId': m.user_id,
                'username': u,
                'xp': m.xp_earned,
            }
            for i, (m, u) in enumerate(members[:50])
        ],
    })


@api.post('/leagues/promote')
@login_required
def promote_league():
    """Called when user levels up — auto promote to next league."""
    profile = _ensure_profile(current_user.id)
    target = get_league_for_level(profile.level)
    league = League.query.filter_by(name=target).first()
    if not league:
        return jsonify({'ok': False}), 400

    member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
    if member and member.league_id == league.id:
        return jsonify({'ok': True, 'promoted': False})

    if member:
        member.league_id = league.id
    else:
        db.session.add(LeagueMember(user_id=current_user.id, league_id=league.id, season=1))
    db.session.commit()
    return jsonify({'ok': True, 'promoted': True, 'league': league.name, 'icon': league.icon})


# ---------------------------------------------------------------------------
# SOCIAL — FOLLOW
# ---------------------------------------------------------------------------

@api.get('/social/users')
@login_required
def social_users():
    """Search users by username."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'items': []})
    users = User.query.filter(User.username.ilike(f'%{q}%'), User.id != current_user.id).limit(20).all()
    following_ids = {c.followed_id for c in SocialConnection.query.filter_by(follower_id=current_user.id).all()}
    return jsonify({
        'items': [
            {
                'id': u.id,
                'username': u.username,
                'isFollowing': u.id in following_ids,
            }
            for u in users
        ]
    })


@api.post('/social/follow')
@login_required
def social_follow():
    data = request.get_json(silent=True) or {}
    target_id = int(data.get('userId') or 0)
    if target_id == current_user.id:
        return jsonify({'error': 'self'}), 400
    existing = SocialConnection.query.filter_by(follower_id=current_user.id, followed_id=target_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'following': False})
    db.session.add(SocialConnection(follower_id=current_user.id, followed_id=target_id))
    db.session.commit()
    return jsonify({'following': True})


@api.get('/social/friends')
@login_required
def social_friends():
    following = (
        db.session.query(SocialConnection, User)
        .join(User, User.id == SocialConnection.followed_id)
        .filter(SocialConnection.follower_id == current_user.id)
        .all()
    )
    followers = (
        db.session.query(SocialConnection, User)
        .join(User, User.id == SocialConnection.follower_id)
        .filter(SocialConnection.followed_id == current_user.id)
        .all()
    )
    return jsonify({
        'following': [
            {'id': u.id, 'username': u.username}
            for _, u in following
        ],
        'followers': [
            {'id': u.id, 'username': u.username}
            for _, u in followers
        ],
    })


# ---------------------------------------------------------------------------
# SOCIAL — FEED
# ---------------------------------------------------------------------------

@api.get('/feed')
@login_required
def feed():
    page = int(request.args.get('page', 1))
    per_page = 20
    posts = FeedPost.query.order_by(FeedPost.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'items': [
            {
                'id': p.id,
                'userId': p.user_id,
                'username': p.user.username,
                'type': p.type,
                'message': p.message,
                'metadata': json_lib.loads(p.metadata_json) if p.metadata_json else None,
                'createdAt': p.created_at.isoformat(),
            }
            for p in posts
        ]
    })


def _create_feed_post(user_id: int, post_type: str, message: str, metadata: dict | None = None):
    post = FeedPost(
        user_id=user_id,
        type=post_type,
        message=message,
        metadata_json=json_lib.dumps(metadata) if metadata else None,
    )
    db.session.add(post)
    db.session.commit()


# ---------------------------------------------------------------------------
# CHALLENGES
# ---------------------------------------------------------------------------

@api.get('/challenges')
@login_required
def challenges():
    active = Challenge.query.filter_by(is_active=True).order_by(Challenge.created_at.desc()).all()
    return jsonify({
        'items': [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'goalType': c.goal_type,
                'goalValue': c.goal_value,
                'xpReward': c.xp_reward,
                'endDate': c.end_date.isoformat(),
                'creator': c.creator.username,
                'participantCount': len(c.participants),
            }
            for c in active
        ]
    })


@api.post('/challenges/create')
@login_required
def create_challenge():
    data = request.get_json(silent=True) or {}
    try:
        end = datetime.fromisoformat(data.get('endDate', ''))
    except (ValueError, TypeError):
        return jsonify({'error': 'invalid endDate'}), 400

    challenge = Challenge(
        creator_id=current_user.id,
        name=data.get('name', 'Reto'),
        description=data.get('description', ''),
        goal_type=data.get('goalType', 'workouts'),
        goal_value=int(data.get('goalValue', 5)),
        xp_reward=int(data.get('xpReward', 200)),
        end_date=end,
    )
    db.session.add(challenge)
    db.session.commit()
    return jsonify({'ok': True, 'id': challenge.id})


@api.post('/challenges/<int:challenge_id>/join')
@login_required
def join_challenge(challenge_id: int):
    challenge = Challenge.query.get_or_404(challenge_id)
    existing = ChallengeParticipant.query.filter_by(challenge_id=challenge_id, user_id=current_user.id).first()
    if existing:
        return jsonify({'error': 'already_joined'}), 400
    db.session.add(ChallengeParticipant(challenge_id=challenge_id, user_id=current_user.id))
    db.session.commit()
    return jsonify({'ok': True})


@api.get('/challenges/mine')
@login_required
def my_challenges():
    participations = ChallengeParticipant.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'items': [
            {
                'id': p.challenge_id,
                'name': p.challenge.name,
                'progress': p.progress,
                'goalValue': p.challenge.goal_value,
                'goalType': p.challenge.goal_type,
                'completed': p.completed,
                'endDate': p.challenge.end_date.isoformat(),
            }
            for p in participations
        ]
    })


# ---------------------------------------------------------------------------
# ENHANCED ME / PROFILE
# ---------------------------------------------------------------------------

@api.get('/profile/<int:user_id>')
@login_required
def profile_detail(user_id: int):
    target = User.query.get_or_404(user_id)
    profile = FitnessProfile.query.filter_by(user_id=target.id).first()
    level = compute_level_from_xp(profile.xp if profile else 0)

    # League
    member = LeagueMember.query.filter_by(user_id=target.id, season=1).first()
    league_name = member.league.name if member else get_league_for_level(level)
    league_icon = member.league.icon if member else '🥉'

    # Stats
    total_sessions = WorkoutSession.query.filter_by(user_id=target.id).count()
    total_kcal = db.session.query(db.func.coalesce(db.func.sum(WorkoutSession.kcal_burned), 0)).filter(
        WorkoutSession.user_id == target.id
    ).scalar()

    # Achievements
    unlocked_ids = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=target.id).all()}
    all_ach = Achievement.query.all()

    # Following check
    is_following = SocialConnection.query.filter_by(
        follower_id=current_user.id, followed_id=target.id
    ).first() is not None

    return jsonify({
        'id': target.id,
        'username': target.username,
        'level': level,
        'title': get_level_title(level),
        'xp': profile.xp if profile else 0,
        'streakDays': profile.streak_days if profile else 0,
        'league': league_name,
        'leagueIcon': league_icon,
        'stats': {
            'sessions': total_sessions,
            'kcal': int(total_kcal),
        },
        'achievements': [
            {
                'code': a.code,
                'name': a.name,
                'icon': a.icon,
                'unlocked': a.id in unlocked_ids,
            }
            for a in all_ach
        ],
        'isFollowing': is_following,
    })
