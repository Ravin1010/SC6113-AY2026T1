"""Receipt fast path: verified server logs, atomic history writes, no checkpoint movement."""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
from web3 import Web3
from hexbytes import HexBytes
import test_blockchain as baseline
import test_remittance_discovery as discovery
from backend.database import get_db
from backend.indexer import index_events
from backend.blockchain import BlockchainError


class ReceiptIndexTests(unittest.TestCase):
    setUp = baseline.BlockchainTests.setUp
    event = baseline.BlockchainTests.event
    client = discovery.RemittanceDiscoveryTests.client

    def receipt(self, block=4):
        log = self.event(block)
        tx_hash = Web3.to_hex(log['transactionHash'])
        self.receipts[tx_hash].update(transactionHash=log['transactionHash'], blockNumber=block, logs=[log])
        return tx_hash, log

    def verify(self, client, tx_hash):
        with patch('backend.api.get_reader', return_value=self.reader):
            return client.get('/api/transactions/' + tx_hash + '/receipt')

    def test_confirmed_receipt_immediately_indexes_canonical_fields(self):
        tx_hash, log = self.receipt()
        result = self.verify(self.client(), tx_hash)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json['activity_indexed'])
        row = get_db().execute('SELECT * FROM indexed_transactions').fetchone()
        self.assertEqual(row['tx_hash'], tx_hash)
        self.assertEqual(row['sender_wallet'], baseline.SENDER.lower())
        self.assertEqual(row['recipient_wallet'], baseline.RECIPIENT.lower())
        self.assertEqual(row['block_hash'], Web3.to_hex(log['blockHash']))
        event = get_db().execute('SELECT * FROM indexed_events').fetchone()
        payload = json.loads(event['payload_json'])
        self.assertEqual(payload['contract'], 'paynow')
        self.assertEqual(payload['address'], baseline.ADDRESSES['paynow'])
        self.assertEqual(payload['initiator'], baseline.SENDER)
        self.assertEqual(payload['args']['amount'], 10**17)
        self.assertEqual(event['remittance_id'], '1')
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexing_state').fetchone()[0], 0)

    def test_duplicate_receipt_and_later_backfill_idempotent(self):
        tx_hash, _ = self.receipt();client = self.client()
        self.verify(client, tx_hash)
        before = tuple(get_db().execute('SELECT * FROM indexed_events').fetchone())
        self.verify(client, tx_hash)
        self.assertEqual(tuple(get_db().execute('SELECT * FROM indexed_events').fetchone()), before)
        self.assertTrue(index_events(self.reader)['caught_up'])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0], 1)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_transactions').fetchone()[0], 1)

    def test_existing_checkpoint_not_advanced_by_isolated_new_receipt(self):
        self.reader.block = 100;self.reader.block_hash = Web3.to_hex(baseline.HASH(100))
        self.app.config['BLOCKCHAIN_INDEX_MAX_BLOCKS'] = 1
        self.assertFalse(index_events(self.reader)['caught_up'])
        before = [tuple(row) for row in get_db().execute('SELECT * FROM indexing_state')]
        tx_hash, _ = self.receipt(90)
        self.verify(self.client(), tx_hash)
        self.assertEqual([tuple(row) for row in get_db().execute('SELECT * FROM indexing_state')], before)

    def test_participant_wrapper_receipt_index_scoping(self):
        self.app.config['BLOCKCHAIN_DEPLOYMENT_ID'] = 'offline-fixture'
        tx_hash, _ = self.receipt();client = self.client(baseline.RECIPIENT)
        self.txs[tx_hash].update({'from': '0x' + 'd'*40, 'to': '0x' + 'e'*40})
        self.assertTrue(self.verify(client, tx_hash).json['activity_indexed'])
        with patch('backend.api.get_reader', return_value=self.reader), patch('backend.api.index_events', return_value={'caught_up': False}):
            history = client.get('/api/transactions').json
        self.assertEqual(len(history['items']), 1)
        self.assertFalse(history['authoritative'])

    def test_unrelated_wallet_rejected_without_index_write(self):
        tx_hash, _ = self.receipt()
        self.assertEqual(self.verify(self.client('0x'+'d'*40), tx_hash).status_code, 403)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_transactions').fetchone()[0], 0)

    def test_atomic_multiple_event_failure_rolls_back(self):
        tx_hash, log = self.receipt()
        self.receipts[tx_hash]['logs'].append(dict(copy.deepcopy(log), logIndex=1))
        db = get_db();actual = db.execute
        class Broken:
            def __enter__(self):return self
            def __exit__(self, kind, *_):db.rollback() if kind else db.commit()
            def execute(self, sql, args=()):
                if sql.startswith('INSERT INTO indexed_events') and args[3] == 1:
                    raise sqlite3.DatabaseError('controlled failure')
                return actual(sql, args)
        client = self.client()
        with patch('backend.indexer.get_db', return_value=Broken()):response = self.verify(client, tx_hash)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM indexed_transactions').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0], 0)

    def test_unconfirmed_noncanonical_or_failed_receipts_not_indexed(self):
        tx_hash, _ = self.receipt();client = self.client()
        self.reader.block = 5;self.reader.block_hash = Web3.to_hex(baseline.HASH(5))
        self.assertFalse(self.verify(client, tx_hash).json['activity_indexed'])
        self.reader.block = 20;self.reader.block_hash = Web3.to_hex(baseline.HASH(20))
        self.receipts[tx_hash]['status'] = 0
        self.assertFalse(self.verify(client, tx_hash).json['activity_indexed'])
        self.receipts[tx_hash]['status'] = 1
        self.eth.get_block = lambda n: {'hash': baseline.HASH(777) if n == 4 else baseline.HASH(n)}
        self.assertFalse(self.verify(client, tx_hash).json['activity_indexed'])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0], 0)

    def test_removed_or_mismatched_receipt_log_rejected(self):
        tx_hash, log = self.receipt();client = self.client()
        for field, value in [('removed', True), ('blockNumber', 999)]:
            original = log[field];log[field] = value
            self.assertEqual(self.verify(client, tx_hash).status_code, 503)
            log[field] = original
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0], 0)

    def test_recent_receipt_visible_while_historical_rpc_unavailable(self):
        self.app.config['BLOCKCHAIN_DEPLOYMENT_ID'] = 'offline-fixture'
        tx_hash, _ = self.receipt();client = self.client()
        self.verify(client, tx_hash)
        with patch('backend.api.get_reader', return_value=self.reader), patch(
                'backend.api.index_events', side_effect=BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'History RPC slow')):
            response = client.get('/api/transactions')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['items'][0]['tx_hash'], tx_hash)
        self.assertFalse(response.json['authoritative'])
        self.assertEqual(response.json['live_error']['code'], 'BLOCKCHAIN_READER_UNAVAILABLE')

    def test_batched_multi_participant_history_uses_verified_event_participants(self):
        self.app.config['BLOCKCHAIN_DEPLOYMENT_ID'] = 'offline-fixture'
        tx_hash, log = self.receipt();client = self.client(baseline.RECIPIENT)
        other = copy.deepcopy(log);other['logIndex'] = 1
        other['topics'][3] = HexBytes(self.reader.web3.codec.encode(['address'], ['0x'+'d'*40]))
        self.receipts[tx_hash]['logs'].append(other)
        self.assertTrue(self.verify(client, tx_hash).json['activity_indexed'])
        self.assertNotEqual(get_db().execute('SELECT recipient_wallet FROM indexed_transactions').fetchone()[0], baseline.RECIPIENT.lower())
        with patch('backend.api.get_reader', return_value=self.reader), patch('backend.api.index_events', return_value={'caught_up': False}):
            response = client.get('/api/transactions')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['items']), 1)
        self.assertEqual(len(response.json['items'][0]['events']), 2)
