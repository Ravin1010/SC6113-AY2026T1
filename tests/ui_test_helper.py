"""Test-only local server/signing helper. Never imported by the application."""
import json
import os
import sys
from eth_account import Account
from eth_account.messages import encode_defunct

if len(sys.argv) > 1 and sys.argv[1] == 'server':
    from app import create_app
    port = int(os.environ['UI_TEST_PORT'])
    app = create_app({'TESTING': True, 'DATABASE': os.environ['UI_TEST_DB'],
                      'SECRET_KEY': 'isolated-ui-test-only', 'AUTH_ORIGIN': f'http://127.0.0.1:{port}'})
    app.run(host='127.0.0.1', port=port, threaded=True, use_reloader=False)
else:
    value = json.load(sys.stdin)
    operation = value['operation']
    if operation == 'account':
        account = Account.create()
        print(json.dumps({'address': account.address, 'key': account.key.hex()}))
    elif operation == 'sign':
        message = bytes.fromhex(value['messageHex'][2:]).decode('utf-8')
        print(json.dumps(Account.from_key(value['key']).sign_message(encode_defunct(text=message)).signature.hex()))
    elif operation == 'expire_session':
        import sqlite3
        with sqlite3.connect(value['database']) as db:
            db.execute('UPDATE auth_sessions SET created_at=1, expires_at=2')
        print('true')
    elif operation == 'seed_cache':
        import sqlite3
        with sqlite3.connect(value['database']) as db:
            db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?)',
                       (11155111, 'isolated-ui-fixture', '0x'+'a'*64, value['address'].lower(),
                        '0x'+'b'*40, 12, '0x'+'c'*64, 1, 1))
        print('true')
