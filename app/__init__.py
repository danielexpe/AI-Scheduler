import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)

    from app.logger_config import setup_logging, start_heartbeat, get_logger

    log_path = os.path.join(data_dir, "web.log")
    setup_logging(log_path)
    logger = get_logger("app.web")
    logger.info("Iniciando AI Mail Scheduler - container web")

    start_heartbeat("app.web")

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
    from app.tasks import tasks_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(routes_bp)
    app.register_blueprint(tasks_bp)

    logger.info("Flask app criada com sucesso")
    return app
