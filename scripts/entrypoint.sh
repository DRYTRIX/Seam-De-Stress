#!/bin/sh
set -e

echo "Waiting for database..."
python -c "
import time
import sys
from app import create_app
from app.extensions import db
from sqlalchemy.exc import OperationalError

app = create_app()
with app.app_context():
    for attempt in range(30):
        try:
            db.session.execute(db.text('SELECT 1'))
            print('Database is ready.')
            sys.exit(0)
        except OperationalError:
            time.sleep(1)
    print('Database not reachable, continuing anyway.')
"

echo "Running database migrations..."
flask db upgrade

exec "$@"
