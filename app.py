from app import create_app
from app.models.db import db
from sqlalchemy import text

flask_app = create_app()


def ensure_schema():
    inspector = db.inspect(db.engine)
    if "attractions" in inspector.get_table_names():
        attraction_columns = {
            column["name"]
            for column in inspector.get_columns("attractions")
        }
        if "photo_reference" not in attraction_columns:
            db.session.execute(
                text("ALTER TABLE attractions ADD COLUMN photo_reference VARCHAR(500) NULL")
            )
            db.session.commit()
            print("Added missing attractions.photo_reference column.")


if __name__ == "__main__":
    with flask_app.app_context():
        db.create_all()
        ensure_schema()
        print("Database tables created.")
    flask_app.run(debug=True, port=5000)
