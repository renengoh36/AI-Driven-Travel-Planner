from flask import Flask
from .config import Config
from .models.db import db
from .models import *

# Creates and configures the Flask application with its database and blueprints.
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from .routes.auth import auth_bp
    from .routes.recommendations import rec_bp
    from .routes.itinerary import itinerary_bp
    from .routes.pages import pages_bp
    from .routes.behaviour import beh_bp
    from .routes.chatbot import chatbot_bp
    from .routes.wishlist import wishlist_bp

    app.register_blueprint(auth_bp, url_prefix="/api/users")
    app.register_blueprint(rec_bp, url_prefix="/api")
    app.register_blueprint(itinerary_bp, url_prefix="/api/itinerary")
    app.register_blueprint(beh_bp, url_prefix="/api")
    app.register_blueprint(chatbot_bp, url_prefix="/api")
    app.register_blueprint(wishlist_bp, url_prefix="/api")
    app.register_blueprint(pages_bp)

    with app.app_context():
        db.create_all()

    return app
