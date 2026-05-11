from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
import qrcode
import os
from backend import db
from backend.models import User, Client, Gym
from backend.forms import LoginForm, RegistrationForm, GymRegistrationForm
from backend.utils.tenant import get_gyms_for_select, resolve_request_gym, slugify_gym_name

auth = Blueprint('auth', __name__)

def _create_client_for_user(user, form=None):
    client = Client.query.filter_by(email=user.email, gym_id=user.gym_id).first()
    if not client:
        client = Client(
            gym_id=user.gym_id,
            name=user.username,
            email=user.email,
            phone=(form.phone.data if form else None) if form else None,
            age=(form.age.data if form else None) if form else None,
            weight=(form.weight.data if form else None) if form else None,
            height=(form.height.data if form else None) if form else None,
            goal=(form.goal.data if form else 'mantener') if form else 'mantener',
            membership_status='active'
        )
        db.session.add(client)
        db.session.commit()

    if client and not client.qr_code:
        static_images = os.path.join(current_app.static_folder, 'images')
        os.makedirs(static_images, exist_ok=True)
        qr_filename = f'qr_{client.id}.png'
        qr_filepath = os.path.join(static_images, qr_filename)
        qr_img = qrcode.make(str(client.id))
        qr_img.save(qr_filepath)
        client.qr_code = qr_filename
        db.session.commit()

    return client

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/landing')
    form = LoginForm()
    gyms = get_gyms_for_select()
    form.gym_slug.choices = [(g.slug, g.name) for g in gyms]
    tenant_gym = resolve_request_gym(form.gym_slug.data)
    form.gym_slug.data = tenant_gym.slug
    if form.validate_on_submit():
        tenant_gym = resolve_request_gym(form.gym_slug.data)
        user = User.query.filter_by(username=form.username.data, gym_id=tenant_gym.id).first()
        if user and user.check_password(form.password.data):
            if not user.is_super_admin and not tenant_gym.approved:
                flash('Este gimnasio aún no ha sido aprobado. Contacta al administrador.')
                return render_template('login.html', form=form)
            login_user(user)
            if user.role == 'user':
                _create_client_for_user(user)
                return redirect('/landing')
            if user.role == 'trainer':
                return redirect(url_for('trainer.dashboard'))
            return redirect(url_for('admin.dashboard'))
        flash('Usuario o contraseña inválidos')
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/landing')
    form = RegistrationForm()
    gyms = get_gyms_for_select()
    form.gym_slug.choices = [(g.slug, g.name) for g in gyms]
    tenant_gym = resolve_request_gym(form.gym_slug.data)
    form.gym_slug.data = tenant_gym.slug
    if form.validate_on_submit():
        tenant_gym = resolve_request_gym(form.gym_slug.data)
        existing_user = User.query.filter(
            User.gym_id == tenant_gym.id,
            or_(User.username == form.username.data, User.email == form.email.data)
        ).first()
        if existing_user:
            if existing_user.role == 'user':
                stale_client = Client.query.filter(
                    Client.gym_id == tenant_gym.id,
                    or_(Client.email == existing_user.email, Client.name == existing_user.username)
                ).first()
                if not stale_client:
                    db.session.delete(existing_user)
                    db.session.commit()
                    existing_user = None

            if existing_user:
                if existing_user.username == form.username.data:
                    flash('El nombre de usuario ya está en uso.', 'danger')
                else:
                    flash('El correo electrónico ya está registrado.', 'danger')
                return render_template('register.html', form=form)

        user = User(username=form.username.data, email=form.email.data, gym_id=tenant_gym.id)
        user.set_password(form.password.data)
        user.role = 'user'
        db.session.add(user)
        db.session.commit()

        _create_client_for_user(user, form)

        flash('Registro exitoso. Ya estás registrado como cliente del gimnasio.')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route('/register_gym', methods=['GET', 'POST'])
def register_gym():
    if current_user.is_authenticated:
        return redirect('/landing')
    form = GymRegistrationForm()
    if form.validate_on_submit():
        slug = slugify_gym_name(form.gym_slug.data) if form.gym_slug.data else slugify_gym_name(form.gym_name.data)
        existing_gym = Gym.query.filter_by(slug=slug).first()
        if existing_gym:
            flash('Ya existe un gimnasio con ese nombre o slug.', 'danger')
            return render_template('register_gym.html', form=form)
        existing_user = User.query.filter_by(username=form.admin_username.data).first()
        if existing_user:
            flash('El nombre de usuario administrador ya está en uso.', 'danger')
            return render_template('register_gym.html', form=form)
        existing_email = User.query.filter_by(email=form.admin_email.data).first()
        if existing_email:
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('register_gym.html', form=form)

        gym = Gym(name=form.gym_name.data.strip(), slug=slug, plan=form.plan.data, approved=False)
        db.session.add(gym)
        db.session.commit()

        admin = User(
            username=form.admin_username.data,
            email=form.admin_email.data,
            role='admin',
            gym_id=gym.id
        )
        admin.set_password(form.admin_password.data)
        db.session.add(admin)
        db.session.commit()

        flash(f'Gimnasio "{gym.name}" registrado correctamente. Ahora puedes iniciar sesión como administrador.')
        return redirect(url_for('auth.login'))
    return render_template('register_gym.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))