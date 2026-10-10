"""Classroom pages plus the additive Iteration 4 backend API."""
import datetime
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, render_template, request, redirect, url_for
from backend.api import api
from backend.database import get_db, init_app


def create_app(test_config=None):
    app = Flask(__name__)
    production = os.getenv('APP_ENV', 'development') == 'production'
    app.config.from_mapping(
        APP_ENV='production' if production else 'development',
        TURSO_DATABASE_URL=os.getenv('TURSO_DATABASE_URL', ''),
        TURSO_AUTH_TOKEN=os.getenv('TURSO_AUTH_TOKEN', ''),
        DATABASE=os.getenv('DATABASE_PATH', str(Path(__file__).with_name('user.db'))),
        SECRET_KEY=os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32),
        AUTH_ORIGIN=os.getenv('AUTH_ORIGIN', 'http://localhost:5000'),
        AUTH_NONCE_TTL=300, AUTH_SESSION_TTL=3600,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=1),
        MAX_CONTENT_LENGTH=16384,
        BLOCKCHAIN_RPC_URL=os.getenv('BLOCKCHAIN_RPC_URL', ''),
        BLOCKCHAIN_CHAIN_ID=os.getenv('BLOCKCHAIN_CHAIN_ID', '11155111'),
        ROLE_REGISTRY_ADDRESS=os.getenv('ROLE_REGISTRY_ADDRESS', ''),
        FUNDING_CONTRACT_ADDRESS=os.getenv('FUNDING_CONTRACT_ADDRESS', ''),
        REMITTANCE_CONTRACT_ADDRESS=os.getenv('REMITTANCE_CONTRACT_ADDRESS', ''),
        BLOCKCHAIN_DEPLOYMENT_ID=os.getenv('BLOCKCHAIN_DEPLOYMENT_ID', ''),
        BLOCKCHAIN_MANIFEST_PATH=os.getenv('BLOCKCHAIN_MANIFEST_PATH', ''),
        BLOCKCHAIN_CONFIRMATIONS=6, BLOCKCHAIN_LOG_CHUNK=500, BLOCKCHAIN_INDEX_MAX_BLOCKS=5000,
    )
    if test_config:
        app.config.update(test_config)
    if app.config['APP_ENV'] == 'production':
        if not os.getenv('FLASK_SECRET_KEY') and not (test_config or {}).get('SECRET_KEY'):
            raise RuntimeError('Production requires FLASK_SECRET_KEY')
        if not os.getenv('AUTH_ORIGIN') and not (test_config or {}).get('AUTH_ORIGIN'):
            raise RuntimeError('Production requires explicit AUTH_ORIGIN')
        app.config['SESSION_COOKIE_SECURE'] = True
    origin = urlsplit(app.config['AUTH_ORIGIN'])
    if (origin.scheme not in ('http', 'https') or not origin.netloc or origin.username
            or origin.password or origin.path or origin.query or origin.fragment):
        raise RuntimeError('AUTH_ORIGIN must be a canonical HTTP(S) origin without a path')
    if app.config['APP_ENV'] == 'production' and origin.scheme != 'https':
        raise RuntimeError('Production AUTH_ORIGIN requires HTTPS')
    if app.config['APP_ENV'] == 'production':
        database_url = urlsplit(app.config['TURSO_DATABASE_URL'])
        if (database_url.scheme not in ('libsql', 'https') or not database_url.hostname
                or not database_url.hostname.endswith('.turso.io') or database_url.username
                or database_url.password or database_url.query or database_url.fragment
                or not app.config['TURSO_AUTH_TOKEN']):
            raise RuntimeError('Production requires a remote Turso libSQL URL and authentication token')
    init_app(app)
    app.register_blueprint(api)

    def save_name():
        name = request.form.get('q', '').strip()
        if not name or len(name) > 120:
            return render_template('index.html', name_error='Enter a name of 1–120 characters.'), 400
        db = get_db()
        db.execute('INSERT INTO user (name,timestamp) VALUES(?,?)',
                   (name, datetime.datetime.now(datetime.timezone.utc).isoformat()))
        db.commit()
        return redirect(url_for('main'), code=303)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            return save_name()
        return render_template('index.html')

    @app.route('/main', methods=['GET', 'POST'])
    def main():
        if request.method == 'POST':
            return save_name()
        return render_template('main.html')

    @app.route('/transferMoney', endpoint='transferMoney', methods=['GET', 'POST'])
    def transfer_money_page():
        return render_template('transferMoney.html')

    @app.route('/depositMoney', endpoint='depositMoney', methods=['GET', 'POST'])
    def deposit_money_page():
        return render_template('depositMoney.html')

    @app.route('/viewUser', endpoint='viewUser', methods=['GET', 'POST'])
    def view_user():
        rows = get_db().execute('SELECT * FROM user').fetchall()
        return render_template('viewUser.html', rows=rows)

    @app.route('/deleteUser', endpoint='deleteUser', methods=['POST'])
    def delete_user():
        db = get_db()
        db.execute('DELETE FROM user')
        db.commit()
        return render_template('deleteUser.html')

    return app


# Import creates no database/auth records. Schema initialization is lazy or via CLI.
app = create_app()
if __name__ == '__main__':
    app.run()
