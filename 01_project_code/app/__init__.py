from flask import Flask

from .config import Config
from .extensions import db
from .auth_middleware import register_auth_middleware
from .routes.responses import fail
from .services.admin_service import initialize_admin_features


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    db.init_app(app)

    from .routes.main import main_bp
    from .routes.hr import hr_bp
    from .routes.interview import interview_bp
    from .routes.candidate import candidate_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(main_bp)
    app.register_blueprint(hr_bp, url_prefix="/hr")
    app.register_blueprint(interview_bp, url_prefix="/interviews")
    app.register_blueprint(candidate_bp, url_prefix="/candidate")

    initialize_admin_features(app)
    register_auth_middleware(app)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled error: %s", error)
        return fail(str(error), status=500)

    return app
