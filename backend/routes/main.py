from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response, current_app, send_file
from flask_login import login_required, current_user
from backend import db
from backend.models import Client, Membership, Payment, Routine, Progress, CheckIn, GroupClass, ClassReservation
from backend.forms import ClientForm, MembershipForm, PaymentForm, RoutineForm, ProgressForm
from backend.utils.membership import effective_membership_price
from backend.utils.tenant import get_current_gym_id
from backend.face_recognizer import register_face, recognize, has_faces, is_available
import qrcode
import os
import io
from PIL import Image
from werkzeug.utils import secure_filename
import json

main = Blueprint('main', __name__)

def _get_current_client():
    return Client.query.filter_by(email=current_user.email, gym_id=get_current_gym_id()).first()

@main.route('/landing')
@main.route('/')
def index():
    return render_template('index.html')

@main.route('/fitness')
@login_required
def fitness_app():
    # Vista integrada (no-React) para visualizar la API fitness dentro de Flask.
    from backend.routes.api import _ensure_profile, _ensure_default_routines, _routine_to_dict
    from backend.models import LeagueMember, WorkoutSession, BodyProgress
    from backend.utils.fitness import get_league_for_level, get_level_title, compute_level_from_xp, compute_xp_to_next
    from datetime import timedelta

    # 1. User & Profile
    profile = _ensure_profile(current_user.id)
    profile.level = compute_level_from_xp(profile.xp)
    db.session.commit()

    member = LeagueMember.query.filter_by(user_id=current_user.id, season=1).first()
    league_name = member.league.name if member else get_league_for_level(profile.level)
    league_icon = member.league.icon if member else '[B]'

    me_data = {
        'username': current_user.username,
        'title': get_level_title(profile.level),
        'league': league_name,
        'leagueIcon': league_icon,
    }

    # 2. Dashboard & Routine of Day
    client = _get_current_client()
    _ensure_default_routines(client)
    today = datetime.utcnow().weekday()
    routine_today = Routine.query.filter_by(client_id=client.id, day_of_week=today).first() if client else None

    since = datetime.utcnow() - timedelta(days=7)
    sessions = WorkoutSession.query.filter(WorkoutSession.user_id == current_user.id, WorkoutSession.started_at >= since).all()
    weekly_minutes = sum(int((s.total_seconds or 0) / 60) for s in sessions)
    weekly_kcal = sum(int(s.kcal_burned or 0) for s in sessions)

    profile.weekly_minutes = weekly_minutes
    profile.weekly_calories = weekly_kcal
    db.session.commit()

    def _greeting_for_hour() -> str:
        hour = datetime.now().hour
        if hour < 12:
            return 'Buenos días'
        if hour < 18:
            return 'Buenas tardes'
        return 'Buenas noches'

    dash_data = {
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

    # 3. All Client Routines
    routines = Routine.query.filter_by(client_id=client.id).order_by(Routine.id.desc()).all() if client else []
    routines_data = {
        'items': [_routine_to_dict(r) for r in routines]
    }

    # 4. Weekly progress points
    items = (
        BodyProgress.query.filter(BodyProgress.user_id == current_user.id, BodyProgress.date >= since)
        .order_by(BodyProgress.date.asc())
        .all()
    )
    weekly_data = {
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

    initial_data = {
        'me': me_data,
        'dash': dash_data,
        'routines': routines_data,
        'weekly': weekly_data
    }

    return render_template('fitness.html', initial_data=initial_data)

@main.route('/clients')
@login_required
def clients():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    clients = Client.query.filter_by(gym_id=get_current_gym_id()).all()
    return render_template('clients.html', clients=clients)

@main.route('/client/<int:id>')
@login_required
def client_detail(id):
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    client = Client.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()

    membership = (
        Membership.query.filter_by(client_id=client.id)
        .order_by(Membership.end_date.desc())
        .first()
    )
    paid_amount = 0.0
    membership_price = 0.0
    due_amount = 0.0
    membership_payments = []
    if membership:
        membership_price = effective_membership_price(membership)
        paid_amount = float(sum(p.amount for p in membership.payments))
        due_amount = float(max(membership_price - paid_amount, 0))
        membership_payments = (
            Payment.query.filter_by(client_id=client.id, membership_id=membership.id)
            .order_by(Payment.date.desc())
            .all()
        )

    return render_template(
        'client_detail.html',
        client=client,
        membership=membership,
        membership_price=membership_price,
        paid_amount=paid_amount,
        due_amount=due_amount,
        membership_payments=membership_payments,
    )

@main.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    form = ClientForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        else:
            try:
                client = Client(
                    gym_id=get_current_gym_id(),
                    name=form.name.data,
                    email=form.email.data,
                    phone=form.phone.data,
                    age=form.age.data,
                    weight=form.weight.data,
                    height=form.height.data,
                    goal=form.goal.data
                )
                print(f"Photo data: {form.photo.data}")
                if form.photo.data and hasattr(form.photo.data, 'filename') and form.photo.data.filename:
                    print("Saving photo...")
                    filename = secure_filename(form.photo.data.filename)
                    filepath = os.path.join(os.getcwd(), 'backend', 'static', 'images', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    form.photo.data.save(filepath)
                    client.photo = filename
                db.session.add(client)
                db.session.commit()
                print(f"Client saved with ID: {client.id}")
                # Generate QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(str(client.id))
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                qr_filename = f'qr_{client.id}.png'
                qr_filepath = os.path.join(os.getcwd(), 'backend', 'static', 'images', qr_filename)
                img.save(qr_filepath)
                client.qr_code = qr_filename
                db.session.commit()
                print("QR generated and saved")
                flash('Cliente agregado correctamente')
                return redirect(url_for('main.clients'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al agregar cliente: {str(e)}')
                print(f'Error: {str(e)}')
    return render_template('add_client.html', form=form)

@main.route('/mi_perfil')
@main.route('/cliente')
@login_required
def client_dashboard():
    if current_user.role != 'user':
        return redirect(url_for('admin.dashboard'))
    client = _get_current_client()
    if not client:
        flash('Perfil de cliente no encontrado. Contacta al administrador.')
        return render_template('cliente_dashboard.html', client=None)

    membership = Membership.query.filter_by(client_id=client.id).order_by(Membership.end_date.desc()).first()
    routines = Routine.query.filter_by(client_id=client.id).order_by(Routine.day_of_week).all()
    progress = Progress.query.filter_by(client_id=client.id).order_by(Progress.date.desc()).limit(5).all()
    payments = Payment.query.filter_by(client_id=client.id).order_by(Payment.date.desc()).all()

    routine_by_day = {}
    for r in routines:
        routine_by_day[r.day_of_week] = r

    return render_template(
        'cliente_dashboard.html',
        client=client,
        membership=membership,
        routines=routines,
        routine_by_day=routine_by_day,
        progress=progress,
        payments=payments
    )

@main.route('/add_membership/<int:client_id>', methods=['GET', 'POST'])
@login_required
def add_membership(client_id):
    gym_id = get_current_gym_id()
    client = Client.query.filter_by(id=client_id, gym_id=gym_id).first_or_404()
    form = MembershipForm()
    prices = {
        'mensual': 119900.0,
        'quincenal': 69900.0,
        'semanal': 44950.0,
        'anual': 299900.0
    }
    if form.validate_on_submit():
        price = prices.get(form.plan.data, 0.0)
        membership = Membership(
            gym_id=gym_id,
            client_id=client_id,
            plan=form.plan.data,
            end_date=form.end_date.data,
            price=price,
            status='active'
        )
        db.session.add(membership)
        client.membership_status = 'active'
        db.session.commit()
        flash('Membresía añadida')
        return redirect(url_for('main.client_detail', id=client_id))
    existing = Membership.query.filter_by(client_id=client_id, gym_id=gym_id).order_by(Membership.end_date.desc()).all()
    memberships_data = []
    for m in existing:
        total_paid = sum(p.amount for p in m.payments)
        price = effective_membership_price(m)
        status = 'Pagada' if total_paid >= price else 'Pendiente'
        memberships_data.append({'m': m, 'paid': total_paid, 'status': status, 'price': price})
    return render_template('add_membership.html', form=form, prices=prices, client_id=client_id, memberships=memberships_data)

@main.route('/add_payment/<int:client_id>', methods=['GET', 'POST'])
@login_required
def add_payment(client_id):
    gym_id = get_current_gym_id()
    client = Client.query.filter_by(id=client_id, gym_id=gym_id).first_or_404()
    form = PaymentForm()
    memberships = Membership.query.filter_by(client_id=client_id, gym_id=gym_id).order_by(Membership.end_date.desc()).all()
    form.membership_id.choices = [(0, 'Sin membresía')] + [(m.id, f'{m.plan} - {m.end_date.strftime("%Y-%m-%d")}') for m in memberships]

    if request.method == 'POST':
        if not form.validate_on_submit():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        else:
            membership_id = form.membership_id.data if form.membership_id.data != 0 else None
            if membership_id is None and memberships:
                membership_id = memberships[0].id

            try:
                payment = Payment(
                    gym_id=gym_id,
                    client_id=client_id,
                    membership_id=membership_id,
                    amount=form.amount.data,
                    method=form.method.data,
                    description=form.description.data
                )
                db.session.add(payment)
                db.session.commit()
                flash('Pago añadido')
                return redirect(url_for('main.client_detail', id=client_id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al guardar pago: {str(e)}', 'danger')
    existing_payments = Payment.query.filter_by(client_id=client_id, gym_id=gym_id).order_by(Payment.date.desc()).all()
    return render_template('add_payment.html', form=form, client_id=client_id, payments=existing_payments)

@main.route('/add_routine/<int:client_id>', methods=['GET', 'POST'])
@login_required
def add_routine(client_id):
    gym_id = get_current_gym_id()
    Client.query.filter_by(id=client_id, gym_id=gym_id).first_or_404()
    form = RoutineForm()
    if form.validate_on_submit():
        try:
            exercises = json.loads(form.exercises.data or '[]')
            if not isinstance(exercises, list) or len(exercises) == 0:
                raise ValueError('Debe agregar al menos 1 ejercicio.')
            day = int(form.day_of_week.data) if form.day_of_week.data else None
            routine = Routine(
                gym_id=gym_id,
                client_id=client_id,
                name=form.name.data,
                category=form.category.data,
                day_of_week=day,
                exercises=form.exercises.data
            )
            db.session.add(routine)
            db.session.commit()
            flash('Rutina añadida')
            return redirect(url_for('main.client_detail', id=client_id))
        except Exception:
            flash('Ejercicios inválidos. Agrega al menos 1 ejercicio con el formulario.', 'danger')
    routines = Routine.query.filter_by(client_id=client_id, gym_id=gym_id).order_by(Routine.day_of_week).all()
    routines_by_day = {}
    for r in routines:
        d = r.day_of_week if r.day_of_week is not None else -1
        routines_by_day.setdefault(d, []).append(r)
    return render_template('add_routine.html', form=form, client_id=client_id, routines=routines, routines_by_day=routines_by_day)

@main.route('/add_progress/<int:client_id>', methods=['GET', 'POST'])
@login_required
def add_progress(client_id):
    gym_id = get_current_gym_id()
    client = Client.query.filter_by(id=client_id, gym_id=gym_id).first_or_404()
    form = ProgressForm()
    if form.validate_on_submit():
        progress = Progress(
            gym_id=gym_id,
            client_id=client_id,
            weight=form.weight.data,
            measurements=form.measurements.data
        )
        if progress.weight and client.height:
            height_m = client.height / 100
            progress.imc = progress.weight / (height_m ** 2)
        db.session.add(progress)
        db.session.commit()
        flash('Progreso añadido')
        return redirect(url_for('main.client_detail', id=client_id))
    progress_list = Progress.query.filter_by(client_id=client_id, gym_id=gym_id).order_by(Progress.date.desc()).all()
    return render_template('add_progress.html', form=form, client_id=client_id, progress_list=progress_list)

@main.route('/escaner')
@login_required
def escaner():
    return render_template('scanner.html')


@main.route('/checkins')
@login_required
def checkins():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    gym_id = get_current_gym_id()
    checks = CheckIn.query.filter_by(gym_id=gym_id).order_by(CheckIn.timestamp.desc()).limit(50).all()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_count = CheckIn.query.filter(CheckIn.gym_id == gym_id, CheckIn.timestamp >= today_start).count()
    return render_template('checkins.html', checkins=checks, now=datetime.utcnow(), todays_count=todays_count)


@main.route('/clases')
@login_required
def clases():
    gym_id = get_current_gym_id()
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    classes_list = GroupClass.query.filter_by(gym_id=gym_id, active=True).order_by(GroupClass.day_of_week, GroupClass.start_time).all()
    today = datetime.utcnow().date()
    client = _get_current_client()
    class_data = []
    for gc in classes_list:
        reserved = ClassReservation.query.filter_by(group_class_id=gc.id, date=today).count()
        user_reserved = ClassReservation.query.filter_by(group_class_id=gc.id, client_id=client.id, date=today).first() if client else None
        class_data.append({
            'class': gc,
            'reserved': reserved,
            'available': gc.capacity - reserved,
            'user_reserved': user_reserved is not None,
        })
    return render_template('clases.html', classes=class_data, days=days, now=datetime.utcnow())


@main.route('/clase/reserve/<int:class_id>', methods=['POST'])
@login_required
def reserve_class(class_id):
    client = _get_current_client()
    if not client:
        flash('No tienes perfil de cliente.', 'danger')
        return redirect(url_for('main.clases'))
    gc = GroupClass.query.filter_by(id=class_id, gym_id=get_current_gym_id()).first_or_404()
    today = datetime.utcnow().date()
    existing = ClassReservation.query.filter_by(group_class_id=gc.id, client_id=client.id, date=today).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('Reserva cancelada.', 'info')
    else:
        count = ClassReservation.query.filter_by(group_class_id=gc.id, date=today).count()
        if count >= gc.capacity:
            flash('Clase llena.', 'danger')
        else:
            r = ClassReservation(group_class_id=gc.id, client_id=client.id, date=today)
            db.session.add(r)
            db.session.commit()
            flash('Reserva confirmada.', 'success')
    return redirect(url_for('main.clases'))


@main.route('/print/clientes')
@login_required
def print_clients():
    gym_id = get_current_gym_id()
    from backend.models import Gym as GymModel
    gym = GymModel.query.get(gym_id)
    clients = Client.query.filter_by(gym_id=gym_id).order_by(Client.name).all()
    return render_template('print_clients.html', clients=clients, gym_name=gym.name if gym else '')


@main.route('/service-worker.js')
def service_worker():
    resp = make_response(current_app.send_static_file('service-worker.js'))
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@main.route('/qr_scan', methods=['POST'])
@login_required
def qr_scan():
    data = request.json
    client_id = data.get('client_id')
    client = Client.query.filter_by(id=client_id, gym_id=get_current_gym_id()).first()
    if client:
        checkin = CheckIn(gym_id=get_current_gym_id(), client_id=client.id)
        db.session.add(checkin)
        db.session.commit()
        return jsonify({'message': 'Entrada registrada', 'client': client.name, 'time': checkin.timestamp.isoformat() + 'Z'})
    return jsonify({'error': 'Cliente no encontrado'}), 404


@main.route('/face/register', methods=['GET'])
@login_required
def face_register_page():
    if not is_available():
        flash('OpenCV no esta disponible en este servidor. El registro facial requiere OpenCV.')
        return redirect(url_for('main.clients'))
    clients = Client.query.filter_by(gym_id=get_current_gym_id()).all()
    return render_template('face_register.html', clients=clients)


@main.route('/face/register/<int:client_id>', methods=['POST'])
@login_required
def face_register_capture(client_id):
    client = Client.query.filter_by(id=client_id, gym_id=get_current_gym_id()).first_or_404()
    data = request.get_json(silent=True)
    if not data or 'embedding' not in data:
        return jsonify({'error': 'No embedding data'}), 400
    ok = register_face(client.id, data['embedding'])
    if not ok:
        return jsonify({'error': 'Embedding invalido. Asegurate de estar bien iluminado y frente a la camara.'}), 400
    return jsonify({'message': f'Rostro registrado para {client.name}'})


@main.route('/face/checkin', methods=['GET'])
@login_required
def face_checkin_page():
    if not is_available():
        flash('OpenCV no esta disponible en este servidor. El check-in facial requiere OpenCV.')
        return redirect(url_for('main.checkins'))
    return render_template('face_checkin.html')


@main.route('/face/checkin/scan', methods=['POST'])
@login_required
def face_checkin_scan():
    data = request.get_json(silent=True)
    if not data or 'embedding' not in data:
        return jsonify({'error': 'No embedding data'}), 400
    cid = recognize(data['embedding'])
    if cid is None:
        return jsonify({'error': 'Rostro no reconocido'}), 404
    client = Client.query.filter_by(id=cid, gym_id=get_current_gym_id()).first()
    if not client:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    checkin = CheckIn(gym_id=get_current_gym_id(), client_id=client.id)
    db.session.add(checkin)
    db.session.commit()
    return jsonify({'message': 'Entrada registrada', 'client': client.name, 'time': checkin.timestamp.isoformat() + 'Z'})


@main.route('/face/has/<int:client_id>')
@login_required
def face_has(client_id):
    return jsonify({'has': has_faces(client_id)})
