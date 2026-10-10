"""Real libsql driver compatibility against isolated files; remote proof is a hosted checkpoint."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import create_app
from backend.database import get_db, initialize
from backend.turso import Connection
import test_backend


class LibsqlBackendTests(test_backend.BackendTests):
    """Run the complete accepted API/auth/db suite with the actual libsql driver."""
    def setUp(self):
        super().setUp()
        self.app.config.update(TURSO_DATABASE_URL=self.path, TURSO_AUTH_TOKEN='')


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'persistence.db')

    def app(self, remote=False):
        return create_app({'TESTING':True,'SECRET_KEY':'test-only','DATABASE':self.path,
                           'TURSO_DATABASE_URL':self.path if remote else '', 'TURSO_AUTH_TOKEN':''})

    def test_user_log_both_backends_and_delete_scope(self):
        for remote in [False,True]:
            app=self.app(remote);client=app.test_client()
            for value in ['', '  ', '\n\t', 'x'*121]:
                self.assertEqual(client.post('/',data={'q':value}).status_code,400)
            self.assertEqual(client.post('/',data={'q':'  test name  '}).status_code,303)
            with app.app_context():
                db=get_db();row=db.execute('SELECT * FROM user').fetchone()
                self.assertEqual(row['name'],'test name');self.assertIn('+00:00',row['timestamp'])
                db.execute('INSERT INTO app_wallets VALUES (?,?,?)',('test',1,1));db.commit()
            self.assertIn('test name',client.get('/viewUser').text)
            self.assertEqual(client.post('/deleteUser').status_code,200)
            with app.app_context():
                db=get_db();self.assertEqual(db.execute('SELECT COUNT(*) FROM user').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM app_wallets').fetchone()[0],1)
                db.execute('DELETE FROM app_wallets');db.commit()

    def test_real_driver_transaction_rollback_reopen_and_upsert(self):
        db=Connection(self.path,'');initialize(db);initialize(db)
        with db:
            db.execute("INSERT INTO user VALUES ('durable','now')")
            db.execute('INSERT INTO indexing_state VALUES (1,?,?,?,?,?)',('test','address',3,'hash',1))
            db.execute('INSERT INTO indexing_state VALUES (1,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,contract_address) DO UPDATE SET last_block=excluded.last_block',('test','address',4,'hash',2))
        with self.assertRaises(sqlite3.IntegrityError):
            with db:
                db.execute("INSERT INTO user VALUES ('rollback','now')")
                db.execute('INSERT INTO indexing_state VALUES (1,?,?,?,?,?)',('test','address',5,'hash',3))
        db.close();db=Connection(self.path,'')
        self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM user').fetchall()],[('durable','now')])
        self.assertEqual(db.execute('SELECT last_block FROM indexing_state').fetchone()['last_block'],4)
        db.close()

    def test_production_never_falls_back_to_local_sqlite(self):
        common={'APP_ENV':'production','SECRET_KEY':'test-only','AUTH_ORIGIN':'https://test.example'}
        for url,token in [('', ''),('file:test.db','token'),('libsql://test.turso.io',''),('libsql://user:pass@test.turso.io','token')]:
            with self.assertRaises(RuntimeError):create_app({**common,'TURSO_DATABASE_URL':url,'TURSO_AUTH_TOKEN':token})


if __name__=='__main__':unittest.main()
