"""Iteration 4 focused tests: generated wallets, temporary SQLite, no RPC."""
import concurrent.futures
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from eth_account import Account
from eth_account.messages import encode_defunct
from app import create_app
from backend.database import get_db, initialize


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'test.db')
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE user (name text, timestamp timestamp)')
            db.execute("INSERT INTO user VALUES ('legacy','2026-01-01')")
        self.app = create_app({'TESTING': True, 'DATABASE': self.path, 'SECRET_KEY': 'test-only-secret',
                               'AUTH_ORIGIN': 'https://test.example'})
        self.client = self.app.test_client()
        self.account = Account.create()

    def nonce(self, account=None, client=None):
        response = (client or self.client).post('/api/auth/nonce', json={'wallet': (account or self.account).address})
        self.assertEqual(response.status_code, 201, response.json)
        return response.json

    def signed(self, challenge, account=None, message=None):
        signature = (account or self.account).sign_message(encode_defunct(text=message or challenge['message'])).signature.hex()
        return {'wallet': self.account.address, 'nonce': challenge['nonce'], 'signature': signature}

    def login(self):
        response = self.client.post('/api/auth/verify', json=self.signed(self.nonce()))
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        self.assertEqual(response.json['error']['code'], code)

    def test_nonce_random_message_and_browser_binding(self):
        first, second = self.nonce(), self.nonce()
        self.assertNotEqual(first['nonce'], second['nonce'])
        self.assertEqual(len(first['nonce']), 64)
        for text in ['SC6113', 'https://test.example', self.account.address, first['nonce'], 'Issued at:', 'Expires at:']:
            self.assertIn(text, first['message'])
        self.assertEqual(first['expires_at'] - first['issued_at'], 300)
        self.assert_error(self.client.post('/api/auth/verify', json=self.signed(first)), 401, 'LOGIN_ATTEMPT_MISMATCH')

    def test_invalid_wallet(self):
        for value in ['bad', '', None, 123, '0x' + '0'*40]:
            with self.subTest(value=value):
                self.assert_error(self.client.post('/api/auth/nonce', json={'wallet': value}), 400, 'INVALID_WALLET')

    def test_json_validation(self):
        self.assert_error(self.client.post('/api/auth/nonce', data='abc'), 415, 'JSON_REQUIRED')
        self.assert_error(self.client.post('/api/auth/nonce', data='{', content_type='application/json'), 400, 'INVALID_JSON')
        for value in [[], {}, {'wallet': self.account.address, 'admin': True}]:
            self.assert_error(self.client.post('/api/auth/nonce', json=value), 400, 'INVALID_INPUT')

    def test_origin_rejected(self):
        self.assert_error(self.client.post('/api/auth/nonce', json={'wallet': self.account.address},
                                          headers={'Origin': 'https://evil.example'}), 403, 'ORIGIN_REJECTED')

    def test_valid_signature_session_and_identity(self):
        result = self.login()
        self.assertTrue(result['authenticated'])
        self.assertEqual(self.client.get('/api/auth/session').json['wallet'], self.account.address)
        me = self.client.get('/api/users/me').json
        self.assertEqual(me['wallet'], self.account.address)
        self.assertFalse(me['roles']['available'])
        self.assertEqual(me['roles']['error']['code'], 'BLOCKCHAIN_NOT_CONFIGURED')
        self.assertNotIn('sender', me['roles'])
        self.assertIn('last_login_at', me['application_metadata'])
        self.assertEqual(self.client.get('/api/users/me').headers['Cache-Control'], 'no-store')

    def test_wrong_signer_not_consumed(self):
        challenge = self.nonce()
        self.assert_error(self.client.post('/api/auth/verify', json=self.signed(challenge, Account.create())), 401, 'SIGNER_MISMATCH')
        self.assertEqual(self.client.post('/api/auth/verify', json=self.signed(challenge)).status_code, 200)

    def test_altered_message(self):
        challenge = self.nonce()
        value = self.signed(challenge)
        value['message'] = challenge['message'] + ' modified'
        self.assert_error(self.client.post('/api/auth/verify', json=value), 400, 'MESSAGE_MISMATCH')
        self.assert_error(self.client.post('/api/auth/verify', json=self.signed(challenge, message=challenge['message']+'!')), 401, 'SIGNER_MISMATCH')

    def test_expired_nonce(self):
        challenge = self.nonce()
        with patch('backend.api.now', return_value=challenge['expires_at']):
            self.assert_error(self.client.post('/api/auth/verify', json=self.signed(challenge)), 410, 'NONCE_EXPIRED')

    def test_nonce_replay(self):
        value = self.signed(self.nonce())
        self.assertEqual(self.client.post('/api/auth/verify', json=value).status_code, 200)
        self.assert_error(self.client.post('/api/auth/verify', json=value), 409, 'NONCE_USED')

    def test_nonce_wallet_and_browser_mismatch(self):
        value = self.signed(self.nonce())
        self.assert_error(self.app.test_client().post('/api/auth/verify', json=value), 401, 'LOGIN_ATTEMPT_MISMATCH')
        value['wallet'] = Account.create().address
        self.assert_error(self.client.post('/api/auth/verify', json=value), 401, 'LOGIN_ATTEMPT_MISMATCH')

    def test_signature_and_nonce_format(self):
        challenge = self.nonce()
        for key, value, code in [('nonce', 'x', 'INVALID_NONCE'), ('nonce', 'a'*64, 'NONCE_NOT_FOUND'),
                                  ('signature', 'x', 'INVALID_SIGNATURE'), ('signature', '0x'+'00'*65, 'INVALID_SIGNATURE')]:
            payload = self.signed(challenge)
            payload[key] = value
            self.assert_error(self.client.post('/api/auth/verify', json=payload), 400, code)

    def test_logout_csrf_and_revoked_cookie(self):
        result = self.login()
        cookie = self.client.get_cookie('session').value
        self.assert_error(self.client.post('/api/auth/logout', json={}), 403, 'CSRF_REQUIRED')
        self.assert_error(self.client.post('/api/auth/logout', json={}, headers={'X-CSRF-Token':'é'}), 403, 'CSRF_REQUIRED')
        response = self.client.post('/api/auth/logout', json={}, headers={'X-CSRF-Token': result['csrf_token']})
        self.assertEqual(response.json, {'authenticated': False})
        self.assert_error(self.client.get('/api/auth/session'), 401, 'AUTH_REQUIRED')
        replay = self.app.test_client()
        replay.set_cookie('session', cookie)
        self.assert_error(replay.get('/api/auth/session'), 401, 'AUTH_REQUIRED')

    def test_server_session_expiry(self):
        self.login()
        with self.app.app_context():
            expiry = get_db().execute('SELECT expires_at FROM auth_sessions').fetchone()[0]
        with patch('backend.api.now', return_value=expiry):
            self.assert_error(self.client.get('/api/auth/session'), 401, 'AUTH_REQUIRED')

    def test_tampered_cookie(self):
        self.login()
        cookie = self.client.get_cookie('session').value
        self.client.set_cookie('session', cookie + 'tampered')
        self.assert_error(self.client.get('/api/auth/session'), 401, 'AUTH_REQUIRED')

    def test_protected_endpoints(self):
        for route in ['/auth/session', '/users/me', '/users/me/balances', '/remittances', '/remittances/1',
                      '/transactions', '/transactions/audit', '/transactions/'+'0x'+'a'*64+'/receipt']:
            self.assert_error(self.client.get('/api'+route), 401, 'AUTH_REQUIRED')
        self.assert_error(self.client.post('/api/auth/logout', json={}), 401, 'AUTH_REQUIRED')

    def test_schema_preserved_idempotent(self):
        with self.app.app_context():
            db = get_db()
            initialize(db)
            initialize(db)
            self.assertEqual(tuple(db.execute('SELECT * FROM user').fetchone()), ('legacy','2026-01-01'))
            self.assertEqual([row['name'] for row in db.execute('PRAGMA table_info(user)')], ['name','timestamp'])
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {'user','auth_nonces','app_wallets','auth_sessions','indexed_transactions','indexed_events','indexing_state'})

    def test_fresh_database_initialization(self):
        fresh = create_app({'TESTING':True, 'DATABASE':str(Path(self.temp.name)/'fresh.db')})
        self.assertEqual(fresh.test_client().get('/viewUser').status_code, 200)
        with fresh.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM user').fetchone()[0], 0)

    def test_records_survive_reopen(self):
        self.login()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT wallet_address FROM app_wallets').fetchone()[0], self.account.address.lower())
            self.assertIsNotNone(db.execute('SELECT consumed_at FROM auth_nonces').fetchone()[0])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_sessions').fetchone()[0], 1)

    def test_uniqueness_and_foreign_keys(self):
        self.login()
        with self.app.app_context():
            db = get_db()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO app_wallets SELECT * FROM app_wallets')
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO auth_nonces SELECT * FROM auth_nonces')
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO auth_sessions VALUES ('fake','missing',1,2,NULL)")
            db.rollback()
            row = (11155111, 'test-deployment', '0x'+'a'*64, self.account.address.lower(), None, 1, 'hash', 1, 1)
            db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?)',row)
            db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?)',row)
            db.rollback()
            event = (11155111,'test-deployment',row[2],0,1,'hash','TestOnly',None,'{}',1)
            db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?)',event)
            db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?)',event)
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?)', (11155111,'other','absent',0,1,'hash','Test',None,'{}',1))
            db.rollback()

    def test_legacy_pages_and_log_deletion_preserve_auth(self):
        self.login()
        for path in ['/', '/main','/depositMoney','/transferMoney','/viewUser']:
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.post('/main', data={'q':'new name'}).status_code, 303)
        self.assertIn('new name', self.client.get('/viewUser').get_data(as_text=True))
        self.assertEqual(self.client.post('/deleteUser').status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM user').fetchone()[0], 0)
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM app_wallets').fetchone()[0], 1)
        self.assertEqual(self.client.get('/api/auth/session').status_code, 200)

    def test_live_routes_unconfigured_no_fake_state(self):
        self.login()
        for route in ['/users/me/balances','/remittances','/remittances/1','/transactions/audit', '/transactions/'+'0x'+'a'*64+'/receipt']:
            response = self.client.get('/api'+route)
            self.assert_error(response,503,'BLOCKCHAIN_NOT_CONFIGURED')
            for fake in ['items','balance','status','sender','recipient']:
                self.assertNotIn(fake, response.json)
        history = self.client.get('/api/transactions').json
        self.assertEqual(history['items'], [])
        self.assertFalse(history['authoritative'])
        self.assertFalse(history['live_blockchain_checked'])

    def test_read_validation_and_no_write_api(self):
        self.login()
        for query in ['limit=0','limit=101','offset=-1','offset=abc','extra=1','limit=1&limit=2']:
            self.assert_error(self.client.get('/api/remittances?'+query),400,'INVALID_QUERY')
            self.assert_error(self.client.get('/api/transactions?'+query),400,'INVALID_QUERY')
        self.assert_error(self.client.get('/api/remittances/0'),400,'INVALID_REMITTANCE_ID')
        self.assert_error(self.client.get('/api/remittances/'+str(2**256)),400,'INVALID_REMITTANCE_ID')
        self.assert_error(self.client.get('/api/transactions/bad/receipt'),400,'INVALID_TRANSACTION_HASH')
        self.assert_error(self.client.post('/api/remittances',json={}),405,'METHOD_NOT_ALLOWED')
        self.assert_error(self.client.get('/api/not-a-route'),404,'NOT_FOUND')

    def configured(self):
        self.app.config.update(BLOCKCHAIN_RPC_URL='https://rpc.test.invalid', BLOCKCHAIN_CHAIN_ID=11155111,
                               BLOCKCHAIN_DEPLOYMENT_ID='test-only', ROLE_REGISTRY_ADDRESS='0x'+'1'*40,
                               FUNDING_CONTRACT_ADDRESS='0x'+'2'*40, REMITTANCE_CONTRACT_ADDRESS='0x'+'3'*40)

    def test_complete_configuration_still_unverified(self):
        self.login()
        self.configured()
        self.assert_error(self.client.get('/api/remittances'),503,'BLOCKCHAIN_DEPLOYMENT_UNVERIFIED')
        self.app.config['BLOCKCHAIN_DEPLOYMENT_VERIFIED'] = True
        self.assert_error(self.client.get('/api/remittances'),503,'BLOCKCHAIN_DEPLOYMENT_UNVERIFIED')

    def test_historical_addresses_invalid_and_no_network_fallback(self):
        self.login()
        self.configured()
        for field, value in [('FUNDING_CONTRACT_ADDRESS','0x1b6fc422422447D20aF3d26aEd82AB79E5520f48'),
                             ('REMITTANCE_CONTRACT_ADDRESS','0x91C798dEc35104fd1610D38a84aE89F2B94F0351'),
                             ('BLOCKCHAIN_CHAIN_ID',1),('ROLE_REGISTRY_ADDRESS','bad'),('BLOCKCHAIN_RPC_URL','https://[')]:
            self.configured()
            self.app.config[field] = value
            response = self.client.get('/api/remittances')
            self.assert_error(response,503,'BLOCKCHAIN_NOT_CONFIGURED')
            self.assertIn(field,response.json['error']['details']['invalid'])

    def test_cached_history_wallet_network_deployment_scope(self):
        self.login()
        self.app.config['BLOCKCHAIN_DEPLOYMENT_ID'] = 'test-only'
        with self.app.app_context():
            db = get_db()
            for chain, deployment, address, hash_char in [(11155111,'test-only',self.account.address.lower(),'a'),
                                                        (11155111,'test-only','other-wallet','b'),
                                                        (11155111,'other',self.account.address.lower(),'c'),
                                                        (1,'test-only',self.account.address.lower(),'d')]:
                db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?)',
                           (chain,deployment,'0x'+hash_char*64,address,None,1,'test-block',1,1))
            db.commit()
        response = self.client.get('/api/transactions').json
        self.assertEqual(len(response['items']), 1)
        self.assertEqual(response['items'][0]['tx_hash'], '0x'+'a'*64)
        self.assertEqual(response['source'],'sqlite_index')
        self.assertFalse(response['authoritative'])
        self.assertFalse(response['indexing_available'])

    def test_nonce_limit_and_body_limit(self):
        for _ in range(10):
            self.nonce()
        self.assert_error(self.client.post('/api/auth/nonce',json={'wallet':self.account.address}),429,'NONCE_LIMIT')
        self.assert_error(self.client.post('/api/auth/nonce', data='x'*20000,content_type='application/json'),413,'REQUEST_TOO_LARGE')

    def test_concurrent_nonce_consumption(self):
        value = self.signed(self.nonce())
        cookie = self.client.get_cookie('session').value
        def verify_once(_):
            client = self.app.test_client()
            client.set_cookie('session',cookie)
            return client.post('/api/auth/verify',json=value).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(verify_once,range(2)))
        self.assertEqual(sorted(results),[200,409])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_sessions').fetchone()[0],1)

    def test_storage_failure_is_json(self):
        with patch('backend.api.get_db',side_effect=sqlite3.OperationalError('test failure')):
            with self.assertLogs(self.app.logger,level='ERROR'):
                self.assert_error(self.client.post('/api/auth/nonce',json={'wallet':self.account.address}),503,'STORAGE_UNAVAILABLE')

    def test_production_configuration_and_cookie(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError,'FLASK_SECRET_KEY'):
                create_app({'APP_ENV':'production'})
            with self.assertRaisesRegex(RuntimeError,'AUTH_ORIGIN'):
                create_app({'APP_ENV':'production','SECRET_KEY':'test-only'})
            with self.assertRaisesRegex(RuntimeError,'HTTPS'):
                create_app({'APP_ENV':'production','SECRET_KEY':'test-only','AUTH_ORIGIN':'http://test.example'})
            prod = create_app({'APP_ENV':'production','SECRET_KEY':'test-only','AUTH_ORIGIN':'https://test.example','DATABASE':self.path,'TURSO_DATABASE_URL':'libsql://test.turso.io','TURSO_AUTH_TOKEN':'test-only'})
            from backend.turso import Connection
            with patch('backend.turso.Connection', side_effect=lambda url, token: Connection(self.path, '')):
                result = prod.test_client().post('/api/auth/nonce',json={'wallet':self.account.address},base_url='https://test.example')
            cookie = result.headers['Set-Cookie']
            for flag in ['Secure','HttpOnly','SameSite=Lax']:
                self.assertIn(flag,cookie)


if __name__ == '__main__':
    unittest.main()
