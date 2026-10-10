"""Iteration 7: run critical index semantics through real libSQL, without remote credentials."""
import tempfile
import unittest
from pathlib import Path
from app import create_app
from backend.database import get_db, initialize
import test_receipt_index as receipt
import test_hosted_indexer as history
import test_remittance_discovery as discovery


class LibsqlMixin:
    def setUp(self):
        super().setUp()
        # Fixture setup performs contract reads only; the first DB open uses libSQL.
        self.app.config.update(TURSO_DATABASE_URL=self.app.config['DATABASE'], TURSO_AUTH_TOKEN='')


class LibsqlReceiptTests(LibsqlMixin, receipt.ReceiptIndexTests):
    pass


class LibsqlBoundedIndexTests(LibsqlMixin, history.HostedIndexTests):
    pass


class LibsqlDirectRemittanceTests(LibsqlMixin, discovery.RemittanceDiscoveryTests):
    pass


class DeleteIsolationTests(unittest.TestCase):
    def test_user_delete_preserves_every_support_table_both_drivers(self):
        for driver in ('sqlite', 'libsql'):
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as directory:
                path = str(Path(directory) / 'test.db')
                app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'DATABASE': path,
                                  'TURSO_DATABASE_URL': path if driver == 'libsql' else '',
                                  'TURSO_AUTH_TOKEN': ''})
                with app.app_context():
                    db = get_db(); initialize(db); initialize(db)
                    with db:
                        db.execute('INSERT INTO app_wallets VALUES (?,?,?)', ('wallet', 1, 1))
                        db.execute('INSERT INTO auth_nonces VALUES (?,?,?,?,?,?,?)', ('nonce', 'wallet', 'attempt', 'message', 1, 2, None))
                        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,?)', ('token-hash', 'wallet', 1, 2, None))
                        db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?)', (11155111, 'fixture', 'tx', 'wallet', None, 1, 'hash', 1, 1))
                        db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?)', (11155111, 'fixture', 'tx', 0, 1, 'hash', 'Fixture', None, '{}', 1))
                        db.execute('INSERT INTO indexing_state VALUES (?,?,?,?,?,?)', (11155111, 'fixture', 'contract', 1, 'hash', 1))
                    tables = ('app_wallets', 'auth_nonces', 'auth_sessions', 'indexed_transactions', 'indexed_events', 'indexing_state')
                    before = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in tables}
                client = app.test_client()
                self.assertEqual(client.post('/', data={'q': '  verification name  '}).status_code, 303)
                self.assertIn('verification name', client.get('/viewUser').text)
                self.assertEqual(client.post('/deleteUser').status_code, 200)
                with app.app_context():
                    db = get_db()
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM user').fetchone()[0], 0)
                    self.assertEqual({table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in tables}, before)

    def test_name_is_parameterized_and_html_escaped_both_drivers(self):
        for driver in ('sqlite', 'libsql'):
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as directory:
                path = str(Path(directory) / 'test.db')
                app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'DATABASE': path,
                                  'TURSO_DATABASE_URL': path if driver == 'libsql' else '', 'TURSO_AUTH_TOKEN': ''})
                client = app.test_client()
                name = "<script>alert(1)</script>'; DROP TABLE user; --"
                self.assertEqual(client.post('/', data={'q': name}).status_code, 303)
                page = client.get('/viewUser').text
                self.assertNotIn('<script>alert(1)</script>', page)
                self.assertIn('&lt;script&gt;', page)
                with app.app_context():
                    self.assertEqual(get_db().execute('SELECT name FROM user').fetchone()[0], name)
