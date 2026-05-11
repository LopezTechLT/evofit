from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from backend import db
from backend.models import Client, Payment, Membership, Routine, Progress, User, Gym, CheckIn, EmailSettings, GroupClass, ClassReservation
from backend.forms import GymForm
from backend.utils.membership import effective_membership_price
from backend.utils.tenant import get_current_gym_id, slugify_gym_name
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import os

def super_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin:
            flash('Acceso denegado. Solo el super admin puede realizar esta acción.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

admin = Blueprint('admin', __name__)


@admin.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    gym_id = get_current_gym_id()
    now = datetime.utcnow()
    # Active clients
    active_clients = Client.query.filter(Client.gym_id == gym_id, Client.membership_status.in_(['active', 'activo'])).count()
    expired = Membership.query.filter(Membership.gym_id == gym_id, Membership.end_date < now).count()
    month_start = now.replace(day=1)
    monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(Payment.gym_id == gym_id, Payment.date >= month_start).scalar() or 0
    total_clients = Client.query.filter_by(gym_id=gym_id).count()

    memberships = Membership.query.filter_by(gym_id=gym_id).all()
    paid_memberships = 0
    pending_memberships = 0
    for m in memberships:
        total_paid = sum(p.amount for p in m.payments)
        price = effective_membership_price(m)
        if total_paid >= price:
            paid_memberships += 1
        else:
            pending_memberships += 1

    # --- Chart data ---
    one_year_ago = now - timedelta(days=365)
    thirty_days_ago = now - timedelta(days=30)

    # Monthly revenue last 12 months
    rev_rows = db.session.query(
        func.strftime('%Y-%m', Payment.date).label('month'),
        func.sum(Payment.amount).label('total')
    ).filter(Payment.gym_id == gym_id, Payment.date >= one_year_ago).group_by('month').order_by('month').all()
    rev_months = [r.month for r in rev_rows]
    rev_totals = [float(r.total) for r in rev_rows]

    # Check-ins last 30 days
    ci_rows = db.session.query(
        func.date(CheckIn.timestamp).label('day'),
        func.count(CheckIn.id).label('count')
    ).filter(CheckIn.gym_id == gym_id, CheckIn.timestamp >= thirty_days_ago).group_by('day').order_by('day').all()
    ci_days = [r.day for r in ci_rows]
    ci_counts = [r.count for r in ci_rows]

    # New clients per month
    nc_rows = db.session.query(
        func.strftime('%Y-%m', Client.registration_date).label('month'),
        func.count(Client.id).label('count')
    ).filter(Client.gym_id == gym_id).group_by('month').order_by('month').all()
    nc_months = [r.month for r in nc_rows]
    nc_counts = [r.count for r in nc_rows]

    # Goal distribution
    goal_rows = db.session.query(Client.goal, func.count(Client.id)).filter(
        Client.gym_id == gym_id, Client.goal.isnot(None), Client.goal != ''
    ).group_by(Client.goal).all()
    goal_labels = [r[0] for r in goal_rows]
    goal_data = [r[1] for r in goal_rows]

    return render_template('dashboard.html',
                         active_clients=active_clients, expired=expired,
                         monthly_revenue=monthly_revenue, total_clients=total_clients,
                         paid_memberships=paid_memberships, pending_memberships=pending_memberships,
                         rev_months=rev_months, rev_totals=rev_totals,
                         ci_days=ci_days, ci_counts=ci_counts,
                         nc_months=nc_months, nc_counts=nc_counts,
                         goal_labels=goal_labels, goal_data=goal_data)


@admin.route('/reports')
@login_required
def reports():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    return render_template('reports.html')


@admin.route('/export/<string:type>')
@login_required
def export(type):
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    from flask import Response
    from backend.utils.reports import export_clients_excel, export_payments_excel, export_checkins_excel
    gym_id = get_current_gym_id()
    filename_map = {'clientes': ('clientes.xlsx', export_clients_excel),
                    'pagos': ('pagos.xlsx', export_payments_excel),
                    'entradas': ('entradas.xlsx', export_checkins_excel)}
    if type not in filename_map:
        flash('Tipo de reporte inválido.', 'danger')
        return redirect(url_for('admin.reports'))
    fn, exporter = filename_map[type]
    if type == 'clientes':
        data = Client.query.filter_by(gym_id=gym_id).order_by(Client.name).all()
    elif type == 'pagos':
        data = Payment.query.filter_by(gym_id=gym_id).order_by(Payment.date.desc()).all()
    else:
        data = CheckIn.query.filter_by(gym_id=gym_id).order_by(CheckIn.timestamp.desc()).all()
    buf = exporter(data)
    return Response(buf.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename={fn}'})

@admin.route('/memberships')
@login_required
def memberships():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    memberships = Membership.query.filter_by(gym_id=get_current_gym_id()).order_by(Membership.end_date.desc()).all()
    membership_list = []
    for membership in memberships:
        total_paid = sum(p.amount for p in membership.payments)
        price = effective_membership_price(membership)
        status = 'Pagada' if total_paid >= price else 'Pendiente'
        due = max(price - total_paid, 0)
        membership_list.append({
            'membership': membership,
            'paid_amount': total_paid,
            'status': status,
            'due_amount': due
        })
    return render_template('admin_memberships.html', memberships=membership_list, now=datetime.utcnow())

@admin.route('/membership/delete/<int:id>', methods=['POST'])
@login_required
def delete_membership(id):
    if current_user.role != 'admin':
        flash('No tienes permiso para eliminar membresías.', 'danger')
        return redirect(url_for('main.index'))

    membership = Membership.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()
    client = membership.client
    db.session.delete(membership)
    db.session.commit()

    if client:
        active_memberships = Membership.query.filter(
            Membership.gym_id == get_current_gym_id(),
            Membership.client_id == client.id,
            Membership.end_date >= datetime.utcnow()
        ).count()
        client.membership_status = 'active' if active_memberships else 'inactive'
        db.session.commit()

    flash('Membresía eliminada correctamente.', 'success')
    return redirect(url_for('admin.memberships'))

@admin.route('/payment/delete/<int:id>', methods=['POST'])
@login_required
def delete_payment(id):
    if current_user.role != 'admin':
        flash('No tienes permiso para eliminar pagos.', 'danger')
        return redirect(url_for('main.index'))

    payment = Payment.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()
    client_id = payment.client_id
    db.session.delete(payment)
    db.session.commit()

    flash('Pago eliminado correctamente.', 'success')
    return redirect(url_for('main.client_detail', id=client_id))

@admin.route('/routine/delete/<int:id>', methods=['POST'])
@login_required
def delete_routine(id):
    if current_user.role != 'admin':
        flash('No tienes permiso para eliminar rutinas.', 'danger')
        return redirect(url_for('main.index'))

    routine = Routine.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()
    client_id = routine.client_id
    db.session.delete(routine)
    db.session.commit()
    flash('Rutina eliminada correctamente.', 'success')
    return redirect(url_for('main.client_detail', id=client_id))


@admin.route('/progress/delete/<int:id>', methods=['POST'])
@login_required
def delete_progress(id):
    if current_user.role != 'admin':
        flash('No tienes permiso para eliminar progresos.', 'danger')
        return redirect(url_for('main.index'))

    progress = Progress.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()
    client_id = progress.client_id
    db.session.delete(progress)
    db.session.commit()
    flash('Progreso eliminado correctamente.', 'success')
    return redirect(url_for('main.client_detail', id=client_id))


@admin.route('/client/delete/<int:id>', methods=['POST'])
@login_required
def delete_client(id):
    if current_user.role != 'admin':
        flash('No tienes permiso para eliminar clientes.', 'danger')
        return redirect(url_for('main.clients'))

    client = Client.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()

    for membership in list(client.memberships):
        db.session.delete(membership)
    for payment in list(client.payments):
        db.session.delete(payment)
    for routine in list(client.routines):
        db.session.delete(routine)
    for progress_item in list(client.progress):
        db.session.delete(progress_item)

    # Remove QR file if exists
    if client.qr_code:
        qr_path = os.path.join(current_app.static_folder, 'images', client.qr_code)
        if os.path.exists(qr_path):
            os.remove(qr_path)

    # Remove linked user account if exists
    linked_users = User.query.filter(
        User.gym_id == get_current_gym_id(),
        or_(
            func.lower(User.email) == client.email.lower(),
            func.lower(User.username) == client.name.lower(),
            func.lower(User.username) == client.email.lower(),
            func.lower(User.email) == client.name.lower()
        )
    ).all()
    for linked_user in linked_users:
        db.session.delete(linked_user)

    db.session.delete(client)
    db.session.commit()
    flash('Cliente eliminado correctamente.', 'success')
    return redirect(url_for('main.clients'))


@admin.route('/gyms', methods=['GET', 'POST'])
@login_required
@super_admin_required
def gyms():
    form = GymForm()
    if form.validate_on_submit():
        slug = slugify_gym_name(form.slug.data) if form.slug.data else slugify_gym_name(form.name.data)
        exists = Gym.query.filter(or_(Gym.name == form.name.data.strip(), Gym.slug == slug)).first()
        if exists:
            flash('Ya existe un gimnasio con ese nombre o slug.', 'danger')
        else:
            gym = Gym(name=form.name.data.strip(), slug=slug, plan=form.plan.data)
            db.session.add(gym)
            db.session.commit()
            flash(f'Gimnasio creado: {gym.name}', 'success')
            return redirect(url_for('admin.gyms'))

    gyms_list = Gym.query.order_by(Gym.created_at.desc()).all()
    # Attach admin username per gym
    gym_data = []
    for g in gyms_list:
        admin_user = User.query.filter_by(gym_id=g.id, role='admin').first()
        gym_data.append({'gym': g, 'admin': admin_user})
    return render_template('admin_gyms.html', form=form, gyms=gym_data)


@admin.route('/gym/<int:gym_id>/edit_admin', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_gym_admin(gym_id):
    gym = Gym.query.get_or_404(gym_id)
    current_admin = User.query.filter_by(gym_id=gym.id, role='admin').first()
    gym_users = User.query.filter_by(gym_id=gym.id).all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user and user.gym_id == gym.id:
                if current_admin and current_admin.id != user.id:
                    current_admin.role = 'user'
                user.role = 'admin'
                db.session.commit()
                flash(f'Admin cambiado a {user.username}', 'success')
            else:
                flash('Usuario no válido para este gimnasio.', 'danger')
        else:
            username = request.form.get('new_username')
            email = request.form.get('new_email')
            password = request.form.get('new_password')
            if username and email and password:
                exists = User.query.filter_by(username=username).first()
                if exists:
                    flash('Ya existe un usuario con ese nombre.', 'danger')
                else:
                    new_admin = User(username=username, email=email, role='admin', gym_id=gym.id)
                    new_admin.set_password(password)
                    if current_admin:
                        current_admin.role = 'user'
                    db.session.add(new_admin)
                    db.session.commit()
                    flash(f'Nuevo admin creado: {username}', 'success')
            else:
                flash('Completa todos los campos para crear un nuevo admin.', 'danger')
        return redirect(url_for('admin.gyms'))

    return render_template('edit_gym_admin.html', gym=gym, current_admin=current_admin, users=gym_users)


@admin.route('/gym/<int:gym_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_gym(gym_id):
    gym = Gym.query.get_or_404(gym_id)
    gym_name = gym.name

    for user in User.query.filter_by(gym_id=gym.id).all():
        db.session.delete(user)
    for c in CheckIn.query.filter_by(gym_id=gym.id).all():
        db.session.delete(c)
    for client in Client.query.filter_by(gym_id=gym.id).all():
        for m in list(client.memberships):
            db.session.delete(m)
        for p in list(client.payments):
            db.session.delete(p)
        for r in list(client.routines):
            db.session.delete(r)
        for pr in list(client.progress):
            db.session.delete(pr)
        if client.qr_code:
            qr_path = os.path.join(current_app.static_folder, 'images', client.qr_code)
            if os.path.exists(qr_path):
                os.remove(qr_path)
        db.session.delete(client)

    db.session.delete(gym)
    db.session.commit()
    flash(f'Gimnasio "{gym_name}" eliminado correctamente.', 'success')
    return redirect(url_for('admin.gyms'))


@admin.route('/classes', methods=['GET', 'POST'])
@login_required
def classes():
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    gym_id = get_current_gym_id()
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    if request.method == 'POST' and current_user.role == 'admin':
        name = request.form.get('name')
        day = int(request.form.get('day_of_week', 0))
        start = request.form.get('start_time', '08:00')
        duration = int(request.form.get('duration', 60))
        capacity = int(request.form.get('capacity', 20))
        desc = request.form.get('description', '')
        if name:
            gc = GroupClass(gym_id=gym_id, name=name, description=desc, day_of_week=day, start_time=start, duration_minutes=duration, capacity=capacity)
            db.session.add(gc)
            db.session.commit()
            flash(f'Clase "{name}" creada.', 'success')
        return redirect(url_for('admin.classes'))

    classes_list = GroupClass.query.filter_by(gym_id=gym_id).order_by(GroupClass.day_of_week, GroupClass.start_time).all()
    today = datetime.utcnow().date()
    # Count reservations for each class today
    class_data = []
    for gc in classes_list:
        reserved = ClassReservation.query.filter_by(group_class_id=gc.id, date=today).count()
        class_data.append({'class': gc, 'reserved': reserved, 'available': gc.capacity - reserved})
    return render_template('admin_classes.html', classes=class_data, days=days, now=datetime.utcnow())


@admin.route('/class/delete/<int:id>', methods=['POST'])
@login_required
def delete_class(id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    gc = GroupClass.query.filter_by(id=id, gym_id=get_current_gym_id()).first_or_404()
    ClassReservation.query.filter_by(group_class_id=gc.id).delete()
    db.session.delete(gc)
    db.session.commit()
    flash('Clase eliminada.', 'success')
    return redirect(url_for('admin.classes'))


@admin.route('/class_reservations/<int:class_id>')
@login_required
def class_reservations(class_id):
    if current_user.role == 'user':
        return redirect(url_for('main.client_dashboard'))
    gc = GroupClass.query.filter_by(id=class_id, gym_id=get_current_gym_id()).first_or_404()
    reservations = ClassReservation.query.filter_by(group_class_id=gc.id).order_by(ClassReservation.date.desc()).all()
    return render_template('class_reservations.html', gc=gc, reservations=reservations)


@admin.route('/pending_gyms')
@login_required
def pending_gyms():
    if not current_user.is_super_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    pending = Gym.query.filter_by(approved=False).order_by(Gym.created_at.desc()).all()
    approved_list = Gym.query.filter_by(approved=True).order_by(Gym.created_at.desc()).all()
    return render_template('pending_gyms.html', pending=pending, approved=approved_list)


@admin.route('/approve_gym/<int:gym_id>', methods=['POST'])
@login_required
def approve_gym(gym_id):
    if not current_user.is_super_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    gym = Gym.query.get_or_404(gym_id)
    gym.approved = True
    db.session.commit()
    flash(f'Gimnasio "{gym.name}" aprobado correctamente.', 'success')
    return redirect(url_for('admin.pending_gyms'))


@admin.route('/email_config', methods=['GET', 'POST'])
@login_required
def email_config():
    if not current_user.is_super_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.smtp_host = request.form.get('smtp_host', 'smtp.gmail.com')
        settings.smtp_port = int(request.form.get('smtp_port', 587))
        settings.smtp_user = request.form.get('smtp_user', '')
        settings.smtp_password = request.form.get('smtp_password', '')
        settings.from_email = request.form.get('from_email', '')
        settings.from_name = request.form.get('from_name', 'EVOFIT')
        db.session.commit()
        flash('Configuración de email guardada.', 'success')
        return redirect(url_for('admin.email_config'))

    return render_template('email_config.html', settings=settings)


@admin.route('/send_reminders', methods=['POST'])
@login_required
def send_reminders():
    from backend.utils.reminder import send_reminders as _send
    result = _send()
    flash(f'Recordatorios enviados: {result["sent"]}', 'success')
    if result['errors']:
        for e in result['errors']:
            flash(e, 'danger')
    return redirect(url_for('admin.dashboard'))
