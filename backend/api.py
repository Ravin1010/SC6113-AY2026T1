"""Minimal wallet authentication and read/index API; no blockchain writes."""
import datetime
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from functools import wraps
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys.exceptions import BadSignature
from eth_utils import is_address, is_checksum_address, to_checksum_address
from flask import Blueprint, current_app, g, jsonify, request, session
from werkzeug.exceptions import HTTPException
from .blockchain import unavailable_state, get_reader, BlockchainError, configuration_status
from .indexer import index_events
from .preparation import prepare
from .database import get_db
from web3.exceptions import Web3Exception
from requests.exceptions import RequestException

api = Blueprint('api', __name__, url_prefix='/api')


class APIError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details


@api.errorhandler(APIError)
def api_error(error):
    payload = {'code': error.code, 'message': error.message}
    if error.details is not None:
        payload['details'] = error.details
    return jsonify(error=payload), error.status


@api.app_errorhandler(HTTPException)
def http_error(error):
    if not request.path.startswith('/api/'):
        return error
    codes = {400: 'INVALID_JSON', 404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED',
             413: 'REQUEST_TOO_LARGE', 415: 'JSON_REQUIRED'}
    return jsonify(error={'code': codes.get(error.code, 'HTTP_ERROR'),
                          'message': error.description}), error.code


@api.errorhandler(sqlite3.Error)
def storage_error(error):
    current_app.logger.exception('Application storage operation failed')
    return jsonify(error={'code': 'STORAGE_UNAVAILABLE', 'message': 'Application storage is unavailable.'}), 503


@api.errorhandler(Web3Exception)
@api.errorhandler(RequestException)
def rpc_error(error):
    return api_error(APIError(503, 'BLOCKCHAIN_READER_UNAVAILABLE', 'RPC read failed. Actions remain disabled.'))


@api.after_request
def prevent_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@api.before_request
def check_origin():
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('Origin')
        if origin and origin != current_app.config['AUTH_ORIGIN']:
            raise APIError(403, 'ORIGIN_REJECTED', 'Request origin does not match this application.')


def body(required, optional=()):
    if not request.is_json:
        raise APIError(415, 'JSON_REQUIRED', 'A JSON object is required.')
    value = request.get_json()
    if not isinstance(value, dict) or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise APIError(400, 'INVALID_INPUT', 'Missing, unexpected or invalid JSON fields.')
    return value


def wallet(value):
    if not isinstance(value, str) or not is_address(value) or int(value, 16) == 0:
        raise APIError(400, 'INVALID_WALLET', 'A nonzero Ethereum wallet address is required.')
    address_body = value[2:]
    if address_body != address_body.lower() and address_body != address_body.upper() and not is_checksum_address(value):
        raise APIError(400, 'INVALID_WALLET', 'Mixed-case addresses must have a valid checksum.')
    return value.lower()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def now():
    return int(time.time())


def iso(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat()


def authenticated(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        token = session.get('auth_token')
        row = None
        if isinstance(token, str):
            row = get_db().execute('SELECT wallet_address,created_at FROM auth_sessions WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?',
                                   (digest(token), now())).fetchone()
        if row is None:
            session.clear()
            raise APIError(401, 'AUTH_REQUIRED', 'A valid wallet session is required.')
        g.wallet = row['wallet_address']
        g.session_started_at = row['created_at']
        return function(*args, **kwargs)
    return wrapped


@api.errorhandler(BlockchainError)
def blockchain_error(error):
    return api_error(APIError(error.status, error.code, error.message, configuration_status()))


def csrf_check():
    supplied = request.headers.get('X-CSRF-Token', '')
    if not supplied or not hmac.compare_digest(supplied.encode(), session.get('csrf_token', '').encode()):
        raise APIError(403, 'CSRF_REQUIRED', 'A valid session CSRF token is required.')


@api.post('/auth/nonce')
def request_nonce():
    address = wallet(body(('wallet',))['wallet'])
    db, issued = get_db(), now()
    outstanding = db.execute('SELECT COUNT(*) FROM auth_nonces WHERE wallet_address=? AND consumed_at IS NULL AND expires_at>?',
                             (address, issued)).fetchone()[0]
    if outstanding >= 10:
        raise APIError(429, 'NONCE_LIMIT', 'Too many outstanding login attempts for this wallet.')
    nonce, attempt = secrets.token_hex(32), secrets.token_hex(32)
    expires = issued + current_app.config['AUTH_NONCE_TTL']
    message = (f"SC6113 Cross-Border Remittance DApp wallet login\nApplication origin: {current_app.config['AUTH_ORIGIN']}\n"
               f"Wallet: {to_checksum_address(address)}\nNonce: {nonce}\nIssued at: {iso(issued)}\nExpires at: {iso(expires)}\n"
               'This signature authenticates a session only; it authorizes no blockchain transaction.')
    with db:
        db.execute('INSERT INTO auth_nonces VALUES (?,?,?,?,?,?,NULL)',
                   (nonce, address, digest(attempt), message, issued, expires))
    session['auth_attempt'] = attempt
    return jsonify(wallet=to_checksum_address(address), nonce=nonce, message=message,
                   issued_at=issued, expires_at=expires), 201


@api.post('/auth/verify')
def verify():
    value = body(('wallet', 'nonce', 'signature'), ('message',))
    address = wallet(value['wallet'])
    if not isinstance(value['nonce'], str) or not re.fullmatch('[0-9a-f]{64}', value['nonce']):
        raise APIError(400, 'INVALID_NONCE', 'Invalid nonce format.')
    if not isinstance(value['signature'], str) or not re.fullmatch('(0x)?[0-9a-fA-F]{130}', value['signature']):
        raise APIError(400, 'INVALID_SIGNATURE', 'A 65-byte Ethereum signature is required.')
    db = get_db()
    row = db.execute('SELECT * FROM auth_nonces WHERE nonce=?', (value['nonce'],)).fetchone()
    if row is None:
        raise APIError(400, 'NONCE_NOT_FOUND', 'Login nonce was not found.')
    if row['consumed_at'] is not None:
        raise APIError(409, 'NONCE_USED', 'Login nonce has already been consumed.')
    if row['expires_at'] <= now():
        raise APIError(410, 'NONCE_EXPIRED', 'Login nonce has expired.')
    attempt = session.get('auth_attempt', '')
    if row['wallet_address'] != address or not hmac.compare_digest(row['attempt_hash'], digest(attempt)):
        raise APIError(401, 'LOGIN_ATTEMPT_MISMATCH', 'Nonce does not belong to this wallet and browser login attempt.')
    if 'message' in value and value['message'] != row['message']:
        raise APIError(400, 'MESSAGE_MISMATCH', 'Sign the exact server-issued message.')
    try:
        signer = Account.recover_message(encode_defunct(text=row['message']), signature=value['signature'])
    except (ValueError, TypeError, BadSignature):
        raise APIError(400, 'INVALID_SIGNATURE', 'Signature recovery failed.')
    if signer.lower() != address:
        raise APIError(401, 'SIGNER_MISMATCH', 'Recovered signer does not match the claimed wallet.')
    token, timestamp = secrets.token_hex(32), now()
    with db:
        updated = db.execute('UPDATE auth_nonces SET consumed_at=? WHERE nonce=? AND consumed_at IS NULL AND expires_at>?',
                             (timestamp, value['nonce'], timestamp))
        if updated.rowcount != 1:
            raise APIError(409, 'NONCE_UNAVAILABLE', 'Nonce was consumed or expired during verification.')
        db.execute('INSERT INTO app_wallets VALUES (?,?,?) ON CONFLICT(wallet_address) DO UPDATE SET last_login_at=excluded.last_login_at',
                   (address, timestamp, timestamp))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,NULL)',
                   (digest(token), address, timestamp, timestamp + current_app.config['AUTH_SESSION_TTL']))
        previous = session.get('auth_token')
        if previous:
            db.execute('UPDATE auth_sessions SET revoked_at=? WHERE token_hash=?', (timestamp, digest(previous)))
    session.clear()
    session.permanent = True
    session['auth_token'], session['csrf_token'] = token, secrets.token_hex(32)
    # Public presentation epoch only; this value cannot authenticate a request.
    session['view_epoch'] = str(time.time_ns())
    return jsonify(authenticated=True, wallet=to_checksum_address(address), csrf_token=session['csrf_token'], session_started_at=timestamp, session_view_epoch=session['view_epoch'])


@api.get('/auth/session')
@authenticated
def current_session():
    return jsonify(authenticated=True, wallet=to_checksum_address(g.wallet), csrf_token=session['csrf_token'], session_started_at=g.session_started_at, session_view_epoch=session.get('view_epoch', str(g.session_started_at)))


@api.post('/auth/logout')
@authenticated
def logout():
    body(())
    supplied = request.headers.get('X-CSRF-Token', '')
    if not hmac.compare_digest(supplied.encode(), session.get('csrf_token', '').encode()) or not supplied:
        raise APIError(403, 'CSRF_REQUIRED', 'A valid session CSRF token is required.')
    db = get_db()
    with db:
        db.execute('UPDATE auth_sessions SET revoked_at=? WHERE token_hash=?', (now(), digest(session['auth_token'])))
    session.clear()
    return jsonify(authenticated=False)


@api.get('/users/me')
@authenticated
def me():
    row = get_db().execute('SELECT created_at,last_login_at FROM app_wallets WHERE wallet_address=?', (g.wallet,)).fetchone()
    try:
        reader = get_reader()
        roles, deployment = reader.user(g.wallet), reader.state()
    except BlockchainError as error:
        roles = {'available': False, 'source': 'RoleRegistry', 'error': {'code': error.code, 'message': error.message}}
        deployment = configuration_status()
    return jsonify(wallet=to_checksum_address(g.wallet), application_metadata=dict(row), roles=roles, deployment=deployment)


@api.get('/users/me/balances')
@authenticated
def balances():
    return jsonify(get_reader().balances(g.wallet))


@api.get('/users/roles/<address>')
@authenticated
def user_roles(address):
    return jsonify(get_reader().user(wallet(address)))


def pagination():
    if set(request.args) - {'limit', 'offset'}:
        raise APIError(400, 'INVALID_QUERY', 'Only limit and offset query parameters are supported.')
    values = []
    for key, default, maximum, minimum in [('limit', '50', 100, 1), ('offset', '0', 1000000, 0)]:
        raw = request.args.get(key, default)
        if len(request.args.getlist(key)) > 1 or not re.fullmatch('[0-9]{1,7}', raw) or not minimum <= int(raw) <= maximum:
            raise APIError(400, 'INVALID_QUERY', f'Invalid {key}.')
        values.append(int(raw))
    return values


@api.get('/remittances')
@authenticated
def remittances():
    limit, offset = pagination()
    reader = get_reader()
    # Discover from the verified snapshot, independently of history/index catch-up.
    admin = reader.admin.lower() == g.wallet
    items = []
    matched = 0
    for identifier in range(reader.count, 0, -1):
        item = reader.remittance(identifier)
        if not admin and g.wallet not in (item['sender'].lower(), item['recipient'].lower()):
            continue
        if matched >= offset:
            items.append(item)
        matched += 1
        if len(items) == limit:
            break
    return jsonify(items=items, source='verified_contract', authoritative=True,
                   discovery='direct_contract_scan', limit=limit, offset=offset)


@api.get('/remittances/<int:remittance_id>')
@authenticated
def remittance(remittance_id):
    if not 0 < remittance_id < 2**256:
        raise APIError(400, 'INVALID_REMITTANCE_ID', 'A positive uint256 remittance ID is required.')
    reader = get_reader()
    item = reader.remittance(remittance_id)
    if g.wallet not in (item['sender'].lower(), item['recipient'].lower()) and not reader.user(g.wallet)['admin']:
        raise APIError(403, 'REMITTANCE_ACCESS_DENIED', 'Only participants or Admin may inspect this remittance through the application.')
    return jsonify(item)


def history_items(limit, offset, deployment, audit=False):
    condition = '' if audit else ' AND (sender_wallet=? OR recipient_wallet=?)'
    parameters = [11155111,deployment] + ([] if audit else [g.wallet,g.wallet]) + [limit,offset]
    rows = get_db().execute('SELECT * FROM indexed_transactions WHERE chain_id=? AND deployment_id=?'+condition+' ORDER BY block_number DESC,tx_hash LIMIT ? OFFSET ?', parameters).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        events = get_db().execute('SELECT log_index,event_type,remittance_id,payload_json,block_hash FROM indexed_events WHERE chain_id=? AND deployment_id=? AND tx_hash=? ORDER BY log_index', (11155111,deployment,row['tx_hash'])).fetchall()
        item['events'] = [dict(event) for event in events]
        result.append(item)
    return result


@api.get('/transactions')
@authenticated
def transactions():
    limit, offset = pagination()
    config = current_app.config
    deployment = config['BLOCKCHAIN_DEPLOYMENT_ID']
    checked, progress, error = False, None, None
    try:
        reader = get_reader()
        progress = index_events(reader)
        checked = True
    except BlockchainError as failure:
        error = {'code': failure.code, 'message': failure.message}
    items = history_items(limit,offset,deployment) if deployment and str(config['BLOCKCHAIN_CHAIN_ID']) == '11155111' else []
    return jsonify(source='sqlite_index', authoritative=False, live_blockchain_checked=checked,
                   scope='authenticated_wallet', deployment_id=deployment or None,
                   indexing_available=checked, indexing=progress, live_error=error, limit=limit, offset=offset, items=items)


@api.get('/transactions/<tx_hash>/receipt')
@authenticated
def receipt(tx_hash):
    if not re.fullmatch('0x[0-9a-fA-F]{64}', tx_hash):
        raise APIError(400, 'INVALID_TRANSACTION_HASH', 'A 32-byte transaction hash is required.')
    reader = get_reader()
    result = reader.receipt(tx_hash)
    if result.get('from'):
        # Batched wallets may submit through a wrapper/relayer. Only events decoded
        # from verified deployment contracts can establish participant association.
        participant_fields = {
            'FundsDeposited': ('sender',), 'FundsWithdrawn': ('owner',),
            'FundsReserved': ('sender', 'recipient'),
            'ReservedFundsReleased': ('sender', 'recipient'),
            'ReservedFundsUnlocked': ('sender',),
            'RemittanceCreated': ('sender', 'recipient'),
            'RemittanceClaimed': ('sender', 'recipient'),
            'RemittanceCancelled': ('sender', 'recipient'),
            'RoleAuthorized': ('admin', 'wallet'), 'RoleRevoked': ('admin', 'wallet'),
            'SystemPaused': ('admin',), 'SystemUnpaused': ('admin',),
        }
        logs = result.get('deployment_logs', [])
        participant = any(
            str(log.get('args', {}).get(field, '')).lower() == g.wallet
            for log in logs for field in participant_fields.get(log.get('event'), ())
        )
        deployment_related = bool(logs) or str(result.get('to', '')).lower() in {
            c.address.lower() for c in reader.contracts.values()
        }
        wallet_related = str(result['from']).lower() == g.wallet or participant
        if not deployment_related or (not wallet_related and not reader.user(g.wallet)['admin']):
            raise APIError(403, 'TRANSACTION_ACCESS_DENIED', 'Receipt is not for this wallet/deployment.')
    return jsonify(result)


@api.get('/transactions/audit')
@authenticated
def audit():
    limit, offset = pagination()
    reader = get_reader()
    if not reader.user(g.wallet)['admin']:
        raise APIError(403, 'ADMIN_REQUIRED', 'The verified on-chain Admin is required.')
    progress = index_events(reader)
    return jsonify(items=history_items(limit,offset,reader.manifest['deploymentId'],True), source='sqlite_index', authoritative=False, live_blockchain_checked=True, indexing=progress)


@api.post('/transactions/prepare')
@authenticated
def prepare_transaction():
    csrf_check()
    value = body(('action', 'arguments'))
    return jsonify(prepare(get_reader(), g.wallet, value['action'], value['arguments'], wallet))
