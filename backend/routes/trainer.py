from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from backend import db
from backend.models import Client, Trainer
from backend.utils.tenant import get_current_gym_id

trainer = Blueprint('trainer', __name__)


@trainer.route('/trainer/dashboard')
@login_required
def dashboard():
    if current_user.role != 'trainer':
        return redirect(url_for('main.index'))
    trainer_obj = Trainer.query.filter_by(user_id=current_user.id).first()
    clients = []
    if trainer_obj:
        clients = trainer_obj.clients
    return render_template('trainer_dashboard.html', clients=clients)
