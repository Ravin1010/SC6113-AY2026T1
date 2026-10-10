"""Authoritative remittance discovery never depends on application history storage."""
import hashlib
import time
import unittest
from unittest.mock import patch
import test_blockchain as baseline
from backend.database import get_db
from backend.blockchain import BlockchainError


class RemittanceDiscoveryTests(unittest.TestCase):
    setUp = baseline.BlockchainTests.setUp

    def client(self, wallet=baseline.SENDER):
        wallet = wallet.lower()
        db = get_db()
        db.execute('INSERT INTO app_wallets VALUES (?,?,?)', (wallet, 1, 1))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,NULL)',
                   (hashlib.sha256(b'test').hexdigest(), wallet, 1, int(time.time()) + 3600))
        db.commit()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['auth_token'] = 'test'
        return client

    def scan(self, wallet=baseline.SENDER, query=''):
        client = self.client(wallet)
        with patch('backend.api.get_reader', return_value=self.reader), patch(
                'backend.api.index_events', side_effect=AssertionError('Index must not be requested')) as index:
            response = client.get('/api/remittances' + query)
        index.assert_not_called()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json['source'], 'verified_contract')
        self.assertTrue(response.json['authoritative'])
        self.assertEqual(response.json['discovery'], 'direct_contract_scan')
        self.assertNotIn('indexing', response.json)
        return response.json['items']

    def test_empty_index_existing_contract_record_and_financial_fields(self):
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0], 0)
        with patch.object(self.reader, 'call', wraps=self.reader.call) as calls:
            items = self.scan()
        self.assertEqual(items[0]['amount']['wei'], str(10**17))
        self.assertEqual(items[0]['status'], 'PENDING')
        self.assertTrue(items[0]['reservation_active'])
        self.assertIn(('paynow', 'transaction', 1), [c.args for c in calls.call_args_list])
        self.assertIn(('deposit_money', 'reservations', 1), [c.args for c in calls.call_args_list])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_transactions').fetchone()[0], 0)

    def test_index_rpc_failure_does_not_affect_list(self):
        client = self.client()
        with patch('backend.api.get_reader', return_value=self.reader), patch(
                'backend.api.index_events', side_effect=BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Slow history')) as index:
            response = client.get('/api/remittances')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['items']), 1)
        index.assert_not_called()

    def test_sender_sees_own(self):
        self.assertEqual([i['id'] for i in self.scan()], ['1'])

    def test_recipient_sees_own(self):
        self.assertEqual([i['id'] for i in self.scan(baseline.RECIPIENT)], ['1'])

    def test_unrelated_ordinary_wallet_cannot_see_others(self):
        wallet = '0x' + 'd' * 40
        self.roles[wallet] = {'sender': True, 'recipient': True, 'admin': False}
        self.assertEqual(self.scan(wallet), [])

    def test_admin_sees_all(self):
        self.assertEqual([i['id'] for i in self.scan(baseline.ADMIN)], ['1'])

    def records(self):
        self.reader.count = 5
        original = self.reader.call
        def call(contract, function, *args):
            if function == 'transaction':
                sender = '0x' + 'd' * 40 if args[0] == 4 else baseline.SENDER
                return [sender, baseline.RECIPIENT, args[0] * 10**16, 1 if args[0] == 3 else 0]
            return original(contract, function, *args)
        self.reader.call = call

    def test_newest_first(self):
        self.records()
        self.assertEqual([i['id'] for i in self.scan()], ['5', '3', '2', '1'])

    def test_pagination_applied_after_filtering_and_stops_after_page(self):
        self.records()
        with patch.object(self.reader, 'remittance', wraps=self.reader.remittance) as reads:
            items = self.scan(query='?limit=2&offset=1')
        self.assertEqual([i['id'] for i in items], ['3', '2'])
        self.assertEqual([c.args[0] for c in reads.call_args_list], [5, 4, 3, 2])
        self.assertEqual(items[0]['status'], 'COMPLETED')

    def test_offset_beyond_filtered_records(self):
        self.assertEqual(self.scan(query='?limit=1&offset=9'), [])

    def test_zero_onchain_count_returns_authoritative_empty_list(self):
        self.reader.count = 0
        self.assertEqual(self.scan(), [])

    def test_transactions_still_attempts_index_and_returns_partial_progress(self):
        client = self.client()
        progress = {'caught_up': False}
        with patch('backend.api.get_reader', return_value=self.reader), patch(
                'backend.api.index_events', return_value=progress) as index:
            response = client.get('/api/transactions')
        index.assert_called_once_with(self.reader)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['indexing'], progress)
        self.assertFalse(response.json['authoritative'])
        self.assertEqual(response.json['source'], 'sqlite_index')

    def test_direct_reader_failure_still_fails_closed(self):
        client = self.client()
        with patch('backend.api.get_reader', return_value=self.reader), patch.object(
                self.reader, 'remittance', side_effect=BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Unavailable')):
            response = client.get('/api/remittances')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json['error']['code'], 'BLOCKCHAIN_READER_UNAVAILABLE')
