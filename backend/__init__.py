import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from backend.config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=["https://evofit-a7xkyrob3-lopez-tech-lt-s-projects.vercel.app"], supports_credentials=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from backend.routes import auth, main, admin, api, trainer
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(trainer)

    frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
    if os.path.isdir(os.path.join(frontend_dist, 'assets')):
        @app.route('/assets/<path:filename>')
        def _serve_assets(filename):
            return send_from_directory(os.path.join(frontend_dist, 'assets'), filename)

        @app.route('/<path:path>')
        def _serve_react(path):
            file_path = os.path.join(frontend_dist, path)
            if path and os.path.isfile(file_path):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

    with app.app_context():
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'), exist_ok=True)
        db.create_all()

        # Migrate: add new columns/tables if missing
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        cols_routine = [c['name'] for c in inspector.get_columns('routine')]
        if 'day_of_week' not in cols_routine:
            db.session.execute(db.text('ALTER TABLE routine ADD COLUMN day_of_week INTEGER'))
            db.session.commit()
        if 'group_class' not in tables:
            db.session.execute(db.text('''
                CREATE TABLE group_class (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gym_id INTEGER REFERENCES gym(id),
                    name VARCHAR(150) NOT NULL,
                    description TEXT DEFAULT '',
                    day_of_week INTEGER NOT NULL,
                    start_time VARCHAR(5) NOT NULL,
                    duration_minutes INTEGER DEFAULT 60,
                    capacity INTEGER DEFAULT 20,
                    active BOOLEAN DEFAULT 1
                )
            '''))
            db.session.execute(db.text('''
                CREATE TABLE class_reservation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_class_id INTEGER NOT NULL REFERENCES group_class(id),
                    client_id INTEGER NOT NULL REFERENCES client(id),
                    date DATE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.session.commit()
        if 'email_settings' not in tables:
            db.session.execute(db.text('''
                CREATE TABLE email_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_host VARCHAR(200) DEFAULT 'smtp.gmail.com',
                    smtp_port INTEGER DEFAULT 587,
                    smtp_user VARCHAR(200) DEFAULT '',
                    smtp_password VARCHAR(200) DEFAULT '',
                    from_email VARCHAR(200) DEFAULT '',
                    from_name VARCHAR(200) DEFAULT 'EVOFIT'
                )
            '''))
            db.session.commit()
        if 'check_in' not in tables:
            db.session.execute(db.text('''
                CREATE TABLE check_in (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gym_id INTEGER REFERENCES gym(id),
                    client_id INTEGER NOT NULL REFERENCES client(id),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.session.commit()

        from backend.models import Gym, User
        if not Gym.query.first():
            default_gym = Gym(name='Gym Principal', slug='principal', plan='starter', approved=True)
            db.session.add(default_gym)
            db.session.commit()

            admin = User(username='admin', email='admin@evofit.com', role='admin', is_super_admin=True, gym_id=default_gym.id)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

    return app
