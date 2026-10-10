"""Bounded clean-index catch-up and transport regressions, no public-chain writes."""
import copy
import hashlib
import time
import unittest
from unittest.mock import patch
from requests.exceptions import ReadTimeout
from web3 import Web3
import test_blockchain as baseline
from backend.database import get_db
from backend.indexer import index_events, BudgetProvider


class HostedIndexTests(unittest.TestCase):
    setUp = baseline.BlockchainTests.setUp
    event = baseline.BlockchainTests.event

    def test_empty_index_bounded_checkpoint_continues_to_complete_idempotent(self):
        self.reader.block=200;self.reader.block_hash=Web3.to_hex(baseline.HASH(200))
        self.app.config['BLOCKCHAIN_INDEX_MAX_BLOCKS']=25
        self.event()
        first=index_events(self.reader)
        self.assertFalse(first['caught_up'])
        first_states=[r['last_block'] for r in get_db().execute('SELECT * FROM indexing_state')]
        self.assertEqual(len(first_states),3)
        second=index_events(self.reader)
        self.assertFalse(second['caught_up'])
        self.assertTrue(all(r['last_block']>before for r,before in zip(get_db().execute('SELECT * FROM indexing_state'),first_states)))
        for _ in range(10):
            if index_events(self.reader)['caught_up']:break
        else:self.fail('Catch-up did not complete')
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],1)
        self.assertTrue(index_events(self.reader)['caught_up'])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],1)

    def test_multiple_logs_share_receipt_transaction_and_block_lookup(self):
        log=self.event();other=copy.deepcopy(log);other['logIndex']=1
        original=self.eth.get_logs
        self.eth.get_logs=lambda q:[log,other] if original(q) else []
        with patch.object(self.eth,'get_transaction_receipt',wraps=self.eth.get_transaction_receipt) as receipts, patch.object(self.eth,'get_transaction',wraps=self.eth.get_transaction) as transactions, patch.object(self.eth,'get_block',wraps=self.eth.get_block) as blocks:
            self.assertTrue(index_events(self.reader)['caught_up'])
            self.assertEqual(receipts.call_count,1);self.assertEqual(transactions.call_count,1)
            self.assertEqual(sum(c.args==(4,) for c in blocks.call_args_list),1)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],2)

    def test_slow_receipt_exhausts_budget_without_advancing_incomplete_chunk(self):
        self.event();clock=[0.]
        original=self.eth.get_transaction_receipt
        def slow(tx):
            clock[0]+=7
            return original(tx)
        with patch('backend.indexer.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.eth,'get_transaction_receipt',side_effect=slow):
            result=index_events(self.reader)
        self.assertFalse(result['caught_up'])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],0)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexing_state').fetchone()[0],2)
        self.assertTrue(index_events(self.reader)['caught_up'])
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],1)

    def client(self):
        db=get_db();wallet=baseline.SENDER.lower()
        db.execute('INSERT INTO app_wallets VALUES (?,?,?)',(wallet,1,1))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,NULL)',(hashlib.sha256(b'test').hexdigest(),wallet,1,int(time.time())+3600));db.commit()
        client=self.app.test_client()
        with client.session_transaction() as session:session['auth_token']='test'
        return client

    def test_history_receipt_failure_returns_structured_unavailable_not_500(self):
        self.event();client=self.client()
        with patch('backend.api.get_reader',return_value=self.reader),patch.object(self.eth,'get_transaction_receipt',side_effect=ReadTimeout('secret URL must not leak')):
            response=client.get('/api/transactions?limit=20&offset=0')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['live_error']['code'],'BLOCKCHAIN_READER_UNAVAILABLE')
        self.assertNotIn('secret',response.text)

    def test_budget_returns_normal_partial_http_response_with_authoritative_reads(self):
        self.event();client=self.client();clock=[0.]
        original=self.eth.get_transaction_receipt
        def slow(tx):clock[0]+=7;return original(tx)
        with patch('backend.api.get_reader',return_value=self.reader),patch('backend.indexer.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.eth,'get_transaction_receipt',side_effect=slow):
            response=client.get('/api/transactions?limit=20&offset=0')
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json['indexing']['caught_up'])
        self.assertEqual(response.json['items'],[])
        with patch('backend.api.get_reader',return_value=self.reader):
            response=client.get('/api/remittances/1')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['authoritative'])
        self.assertEqual(response.json['status'],'PENDING')

    def test_http_transport_short_timeout_and_no_retries(self):
        provider=BudgetProvider('https://example.invalid',time.monotonic()+.1)
        self.assertIsNone(provider.exception_retry_configuration)
        connect,read=provider.get_request_kwargs()['timeout']
        self.assertLessEqual(connect+read,.1)

    def test_real_slow_http_receipt_times_out_promptly_without_retries(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        log=self.event();requests=[]
        def encode(value):
            if isinstance(value,bytes):return Web3.to_hex(value)
            if isinstance(value,list):return [encode(v) for v in value]
            if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
            return value
        class Server(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                method=body['method'];requests.append(method)
                if method=='eth_getBlockByNumber':result={'hash':Web3.to_hex(baseline.HASH(int(body['params'][0],16)))}
                elif method=='eth_getLogs':
                    q=body['params'][0]
                    address=q['address'][0] if isinstance(q['address'],list) else q['address']
                    result=[encode(log)] if address.lower()==baseline.ADDRESSES['paynow'].lower() else []
                elif method=='eth_getTransactionReceipt':
                    time.sleep(.3);result={'status':'0x1','blockHash':Web3.to_hex(baseline.HASH(4))}
                else:result=None
                payload=json.dumps({'jsonrpc':'2.0','id':body['id'],'result':result}).encode()
                try:self.send_response(200);self.end_headers();self.wfile.write(payload)
                except (BrokenPipeError,ConnectionResetError):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Server)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        self.reader.web3=Web3(Web3.HTTPProvider(f'http://127.0.0.1:{server.server_port}'))
        self.app.config['BLOCKCHAIN_INDEX_SECONDS']=.2
        client=self.client();started=time.monotonic()
        with patch('backend.api.get_reader',return_value=self.reader):response=client.get('/api/transactions?limit=20&offset=0')
        self.assertLess(time.monotonic()-started,1)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json['live_error']['code'],'BLOCKCHAIN_READER_UNAVAILABLE')
        self.assertEqual(requests.count('eth_getTransactionReceipt'),1)

    def test_unverified_checkpoint_budget_never_exposes_old_evidence(self):
        self.event();index_events(self.reader)
        clock=[0.];original=self.eth.get_block
        def slow(n):clock[0]+=7;return original(n)
        with patch('backend.indexer.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.eth,'get_block',side_effect=slow):
            with self.assertRaises(baseline.BlockchainError) as failure:index_events(self.reader)
        self.assertEqual(failure.exception.code,'BLOCKCHAIN_READER_UNAVAILABLE')
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],1)

    def test_history_malformed_receipt_returns_unavailable_and_no_incomplete_checkpoint(self):
        log=self.event();client=self.client()
        del self.receipts[Web3.to_hex(log['transactionHash'])]['blockHash']
        with patch('backend.api.get_reader',return_value=self.reader):response=client.get('/api/transactions?limit=20&offset=0')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['live_error']['code'],'INDEX_RECONCILIATION_FAILED')
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],0)
