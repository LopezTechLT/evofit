from flask import render_template
from flask_mail import Mail, Message
from backend import db
from backend.models import EmailSettings
from threading import Thread


def get_mail(app):
    settings = EmailSettings.query.first()
    if not settings or not settings.smtp_host or not settings.smtp_user:
        return None

    app.config['MAIL_SERVER'] = settings.smtp_host
    app.config['MAIL_PORT'] = settings.smtp_port
    app.config['MAIL_USE_TLS'] = settings.smtp_port == 587
    app.config['MAIL_USERNAME'] = settings.smtp_user
    app.config['MAIL_PASSWORD'] = settings.smtp_password
    app.config['MAIL_DEFAULT_SENDER'] = (settings.from_name or 'EVOFIT', settings.from_email)
    return Mail(app)


def send_async(app, msg):
    with app.app_context():
        mail = get_mail(app)
        if mail:
            mail.send(msg)


def send_email(app, subject, to, template, **kwargs):
    settings = EmailSettings.query.first()
    if not settings or not settings.smtp_host:
        return False
    try:
        html = render_template(template, **kwargs)
        msg = Message(subject, recipients=[to], html=html)
        thr = Thread(target=send_async, args=(app, msg))
        thr.start()
        return True
    except Exception:
        return False
