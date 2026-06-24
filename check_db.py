from app import create_app
from app.models.db import db

app = create_app()

with app.app_context():
    inspector = db.inspect(db.engine)

    print("\nTables Found:")
    for table in inspector.get_table_names():
        print("-", table)