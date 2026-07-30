import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."

    from app.models import init_db, UserModel
    init_db(app)

    @login_manager.user_loader
    def load_user(user_id):
        return UserModel.get(user_id)

    from app.auth import auth_bp
    from app.routes import routes_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(routes_bp)

    return app
