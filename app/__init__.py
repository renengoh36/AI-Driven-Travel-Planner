from flask import Flask
from .config import Config
from .models.db import db
from .models import *

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from .routes.auth import auth_bp
    from .routes.recommendations import rec_bp
    from .routes.itinerary import itinerary_bp
    from .routes.chatbot import chatbot_bp
    from .routes.pages import pages_bp

    app.register_blueprint(auth_bp, url_prefix="/api/users")
    app.register_blueprint(rec_bp, url_prefix="/api")
    app.register_blueprint(itinerary_bp, url_prefix="/api/itinerary")
    app.register_blueprint(chatbot_bp, url_prefix="/api")
    app.register_blueprint(pages_bp)

    return app
