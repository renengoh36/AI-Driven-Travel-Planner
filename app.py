from app import create_app
from app.models.db import db
from sqlalchemy import text

flask_app = create_app()

 # Ensures required database tables and attraction columns exist in the current schema.
def ensure_schema():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()

    # Back-compat: add photo_reference if missing from old schema
    if "attractions" in tables:
        cols = {c["name"] for c in inspector.get_columns("attractions")}
        if "photo_reference" not in cols:
            db.session.execute(
                text("ALTER TABLE attractions ADD COLUMN photo_reference VARCHAR(500) NULL")
            )
            db.session.commit()
            print("Added missing attractions.photo_reference column.")
        if "photo_url" not in cols:
            db.session.execute(
                text("ALTER TABLE attractions ADD COLUMN photo_url VARCHAR(500) NULL")
            )
            db.session.commit()
            print("Added missing attractions.photo_url column.")

    # Ensure attraction_feedback table exists
    if "attraction_feedback" not in tables:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS attraction_feedback (
                feedback_id   INT AUTO_INCREMENT PRIMARY KEY,
                user_id       INT NOT NULL,
                itinerary_id  INT NOT NULL,
                attraction_id INT NOT NULL,
                created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_af_user (user_id),
                FOREIGN KEY (user_id)      REFERENCES users(user_id)           ON DELETE CASCADE,
                FOREIGN KEY (itinerary_id) REFERENCES itineraries(itinerary_id) ON DELETE CASCADE,
                FOREIGN KEY (attraction_id) REFERENCES attractions(attraction_id) ON DELETE CASCADE
            )
        """))
        db.session.commit()
        print("Created attraction_feedback table.")

    # Ensure user_behaviour table exists (created by db.create_all, but guard here too)
    if "user_behaviour" not in tables:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_behaviour (
                behaviour_id  INT AUTO_INCREMENT PRIMARY KEY,
                user_id       INT NOT NULL,
                event_type    ENUM('search','attraction_add','itinerary_generate','rating') NOT NULL,
                category      VARCHAR(100) NULL,
                destination   VARCHAR(100) NULL,
                attraction_id INT NULL,
                event_weight  FLOAT NOT NULL DEFAULT 1.0,
                created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ub_user (user_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """))
        db.session.commit()
        print("Created user_behaviour table.")


if __name__ == "__main__":
    with flask_app.app_context():
        db.create_all()
        ensure_schema()
        print("Database tables created.")
    flask_app.run(debug=True, port=5000, threaded=True)
