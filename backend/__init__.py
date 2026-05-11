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

    from backend.routes import auth, main, admin, api
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)

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
        db.create_all()

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
