"""Activity cache has no financial authority and never invokes RPC until explicit sync."""
import unittest
from unittest.mock import patch
import test_remittance_discovery as discovery
from history_helper import sync_history


class CachedActivityTests(unittest.TestCase):
    setUp=discovery.RemittanceDiscoveryTests.setUp
    client=discovery.RemittanceDiscoveryTests.client
    def test_cached_rows_never_require_reader_or_index_and_label_unchecked(self):
        client=self.client()
        with patch('backend.api.get_reader',side_effect=AssertionError('RPC must not run')), patch(
                'backend.api.index_events',side_effect=AssertionError('Index must not run')):
            response=client.get('/api/transactions')
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json['authoritative'])
        self.assertFalse(response.json['live_blockchain_checked'])
        self.assertEqual(response.json['reconciliation'],'not_checked')
    def test_explicit_sync_requires_csrf_and_keeps_partial_index_provenance(self):
        client=self.client()
        self.assertEqual(client.post('/api/transactions/sync',json={}).status_code,403)
        with patch('backend.api.get_reader',return_value=self.reader),patch('backend.api.index_events',return_value={'caught_up':False}) as index:
            response=sync_history(client)
        index.assert_called_once_with(self.reader)
        self.assertTrue(response.json['live_blockchain_checked'])
        self.assertFalse(response.json['authoritative']);self.assertFalse(response.json['indexing']['caught_up'])
    def test_explicit_sync_rejects_unauthenticated_request(self):
        self.assertEqual(self.app.test_client().post('/api/transactions/sync',json={}).status_code,401)
