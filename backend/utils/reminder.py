from datetime import datetime, timedelta
from flask import current_app
from backend import db
from backend.models import Membership, Client, EmailSettings
from backend.utils.email import send_email


def send_reminders():
    app = current_app._get_current_object()
    settings = EmailSettings.query.first()
    if not settings or not settings.smtp_host:
        return {'sent': 0, 'errors': ['SMTP no configurado']}

    now = datetime.utcnow()
    targets = [now + timedelta(days=3), now + timedelta(days=1), now]
    sent = 0
    errors = []

    for target in targets:
        expiring = Membership.query.filter(
            Membership.end_date >= target.replace(hour=0, minute=0, second=0),
            Membership.end_date <= target.replace(hour=23, minute=59, second=59),
        ).all()

        for m in expiring:
            client = Client.query.get(m.client_id)
            if not client or not client.email:
                continue
            days_left = (m.end_date - now).days
            if days_left < 0:
                subject = f'Tu membresía en {m.gym.name} ha vencido'
            elif days_left == 0:
                subject = f'Tu membresía vence HOY — {m.gym.name}'
            else:
                subject = f'Tu membresía vence en {days_left} día(s) — {m.gym.name}'

            ok = send_email(
                app, subject, client.email,
                'email_reminder.html',
                client=client,
                membership=m,
                days_left=days_left,
                gym_name=m.gym.name if m.gym else 'EVOFIT',
            )
            if ok:
                sent += 1
            else:
                errors.append(f'Falló envío a {client.email}')

    return {'sent': sent, 'errors': errors}
