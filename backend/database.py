"""SQLite application-support storage; never financial authority."""
import sqlite3
from pathlib import Path
import click
from flask import current_app, g

SCHEMA = Path(__file__).with_name('schema.sql')


def initialize(db):
    db.executescript(SCHEMA.read_text())
    db.commit()


def get_db():
    if 'db' not in g:
        if current_app.config.get('TURSO_DATABASE_URL'):
            from .turso import Connection
            db = Connection(current_app.config['TURSO_DATABASE_URL'], current_app.config.get('TURSO_AUTH_TOKEN', ''))
        else:
            db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
            db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys = ON')
            initialize(db)
        except sqlite3.Error:
            db.close()
            raise
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command('init-db')
    def init_db_command():
        """Idempotently add tables without clearing existing data."""
        get_db()
        click.echo('SQLite application schema initialized; existing records retained.')
