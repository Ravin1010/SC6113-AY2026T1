"""Real Web3 ABI/batch formatting over a controlled HTTP transport, never Sepolia."""
import json
import unittest
from unittest.mock import patch
from web3 import Web3
from eth_utils.abi import collapse_if_tuple
import backend.blockchain as b
from test_blockchain import BUILD, ADDRESSES, SENDER, RECIPIENT


class PinnedBatchTests(unittest.TestCase):
    def setUp(self):
        self.provider = b.VerifiedBatchProvider('https://offline.invalid')
        self.web3 = Web3(self.provider)
        self.reader = b.SepoliaReader.__new__(b.SepoliaReader)
        self.reader.web3 = self.web3
        self.reader.block = 20
        self.reader.count = 11
        self.reader.admin = ADDRESSES['RoleRegistry']
        self.reader.paused = False
        self.reader.contracts = {name: self.web3.eth.contract(address=address, abi=BUILD['contracts'][name]['abi'])
                                 for name, address in ADDRESSES.items()}
        self.reader.ensure_snapshot = lambda: None
        self.payloads = []
        self.mode = 'normal'
        self.sender_role = True
        self.recipient_role = True
        self.paused = False
        self.available = 123
        self.status = 0
        self.patch = patch.object(self.provider._request_session_manager, 'make_post_request', side_effect=self.transport)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def transport(self, endpoint, data, **kwargs):
        payload = json.loads(data); self.payloads.append(payload)
        def answer(item):
            if item['method'] == 'eth_chainId':
                result = '0xaa36a7'
            elif item['method'] == 'eth_estimateGas':
                self.assertEqual(item['params'][1], '0x14')
                result = '0xc350'
            else:
                self.assertEqual(item['method'], 'eth_call')
                self.assertEqual(item['params'][1], '0x14')
                transaction = item['params'][0]
                contract = next(c for c in self.reader.contracts.values() if c.address.lower() == transaction['to'].lower())
                function, arguments = contract.decode_function_input(transaction['data'])
                name = function.fn_name
                value = {'isSender': self.sender_role, 'isRecipient': self.recipient_role, 'paused':self.paused,'remittanceCount':11,'availableBalance': self.available,
                         'reservedBalance': 50, 'transaction': (SENDER, RECIPIENT, 7, self.status),
                         'reservations': (SENDER, RECIPIENT, 7, True), 'transfer': 7}.get(name,())
                types = [collapse_if_tuple(output) for output in function.abi['outputs']]
                values = value if len(types) > 1 else (value,) if types else ()
                result = Web3.to_hex(self.web3.codec.encode(types, values))
            return {'jsonrpc': '2.0', 'id': item['id'], 'result': result}
        if not isinstance(payload, list):
            return json.dumps(answer(payload)).encode()
        responses = [answer(item) for item in reversed(payload)]
        if self.mode == 'missing': responses.pop()
        if self.mode == 'duplicate': responses[0]['id'] = responses[1]['id']
        if self.mode == 'unknown': responses[0]['id'] = 999999
        if self.mode == 'error': responses[0] = {'jsonrpc': '2.0', 'id': responses[0]['id'], 'error': {'code': -32000}}
        if self.mode == 'malformed': responses[0]['result'] = '0x12'
        if self.mode == 'timeout': raise TimeoutError('controlled transport failure')
        return json.dumps(responses).encode()

    def requests(self):
        return [('RoleRegistry', 'isSender', (SENDER,)), ('deposit_money', 'availableBalance', (SENDER,))]

    def test_reordered_response_mapping_pinned_and_request_local_dedup(self):
        self.assertEqual(self.reader.calls(self.requests()), [True, 123])
        batches = [p for p in self.payloads if isinstance(p, list)]
        self.assertEqual(len(batches), 1)
        self.assertTrue(all(p['params'][1] == '0x14' for p in batches[0]))
        self.assertEqual(self.reader.calls(self.requests()), [True, 123])
        self.assertEqual(len([p for p in self.payloads if isinstance(p, list)]), 1)

    def test_missing_response_fails_without_partial_cache(self): self.reject('missing')
    def test_duplicate_identifier_fails_without_partial_cache(self): self.reject('duplicate')
    def test_unknown_identifier_fails_without_partial_cache(self): self.reject('unknown')
    def test_rpc_error_fails_without_partial_cache(self): self.reject('error')
    def test_malformed_abi_fails_without_partial_cache(self): self.reject('malformed')
    def test_timeout_fails_without_partial_cache(self): self.reject('timeout')

    def reject(self, mode):
        self.mode = mode
        with self.assertRaises(b.BlockchainError) as error: self.reader.calls(self.requests())
        self.assertEqual(error.exception.code, 'BLOCKCHAIN_READER_UNAVAILABLE')
        self.assertFalse(self.reader._calls)

    def test_ten_remittances_one_transport_batch_and_no_duplicate_pair_reads(self):
        with self.reader.snapshot_batch():
            items = list(self.reader.remittances(list(range(10, 0, -1))))
        self.assertEqual([i['id'] for i in items], [str(i) for i in range(10, 0, -1)])
        batches = [p for p in self.payloads if isinstance(p, list)]
        self.assertEqual(len(batches), 1); self.assertEqual(len(batches[0]), 20)
        self.assertTrue(all(i['authoritative'] and i['reservation_active'] for i in items))

    def test_fresh_reader_role_and_wallet_state_not_shared(self):
        self.assertTrue(self.reader.user(SENDER)['sender'])
        self.sender_role = False
        self.reader._calls = {}  # Equivalent to a distinct fresh request reader.
        self.assertFalse(self.reader.user(RECIPIENT)['sender'])

    def test_execution_simulation_and_gas_estimation_share_pinned_transport(self):
        transaction={'from':SENDER,'to':ADDRESSES['paynow'],
                     'data':self.reader.contracts['paynow'].encode_abi('transfer',args=[RECIPIENT,1]),'value':'0x0'}
        self.assertEqual(self.reader.simulate(transaction),50000)
        batches=[p for p in self.payloads if isinstance(p,list)]
        self.assertEqual(len(batches),1)
        self.assertEqual([p['method'] for p in batches[0]],['eth_call','eth_estimateGas'])
        self.assertTrue(all(p['params'][1]=='0x14' for p in batches[0]))

    def test_execution_batch_partial_response_fails_closed(self):
        self.mode='missing'
        transaction={'from':SENDER,'to':ADDRESSES['paynow'],
                     'data':self.reader.contracts['paynow'].encode_abi('transfer',args=[RECIPIENT,1]),'value':'0x0'}
        with self.assertRaises(b.BlockchainError):self.reader.simulate(transaction)

    def test_all_ten_actions_use_one_dynamic_validation_batch_and_same_block_execution(self):
        from backend.preparation import prepare
        from test_blockchain import ADMIN
        self.reader.read_mode='prepare';self.reader.wired=True;self.reader.admin=ADMIN
        self.reader.block_hash='0x'+'0'*64;self.reader.manifest={'deploymentId':'fixture'}
        cases=[('transfer',SENDER,{'wallet':RECIPIENT,'amount_wei':'1'}),('deposit',SENDER,{'amount_wei':'1'}),
               ('withdraw',SENDER,{'amount_wei':'1'}),('claim',RECIPIENT,{'remittance_id':'1'}),('cancel',SENDER,{'remittance_id':'1'}),
               ('authorizeSender',ADMIN,{'wallet':RECIPIENT}),('authorizeRecipient',ADMIN,{'wallet':SENDER}),
               ('revokeRole',ADMIN,{'wallet':SENDER,'role':0}),('pause',ADMIN,{}),('unpause',ADMIN,{})]
        for action,owner,args in cases:
            with self.subTest(action=action):
                self.reader._calls={};self.payloads.clear()
                self.sender_role=action!='authorizeSender';self.recipient_role=action!='authorizeRecipient';self.paused=action=='unpause'
                self.assertTrue(prepare(self.reader,owner,action,args,lambda value:value)['unsigned'])
                batches=[p for p in self.payloads if isinstance(p,list)]
                self.assertEqual(len(batches),2)
                self.assertTrue(all(p['method']=='eth_call' and p['params'][1]=='0x14' for p in batches[0]))
                self.assertEqual([p['method'] for p in batches[1]],['eth_call','eth_estimateGas'])

    def test_narrow_prepare_current_invalid_conditions_never_reach_simulation(self):
        from backend.preparation import prepare
        from test_blockchain import ADMIN
        self.reader.read_mode='prepare';self.reader.wired=True;self.reader.admin=ADMIN
        self.reader.block_hash='0x'+'0'*64;self.reader.manifest={'deploymentId':'fixture'}
        for failure in ['sender','recipient','balance','pause','terminal','participant','admin']:
            with self.subTest(failure=failure):
                self.reader._calls={};self.payloads.clear()
                self.sender_role=failure!='sender';self.recipient_role=failure!='recipient'
                self.available=0 if failure=='balance' else 123;self.paused=failure=='pause';self.status=1 if failure=='terminal' else 0
                action='claim' if failure in ('terminal','participant') else 'pause' if failure=='admin' else 'transfer'
                owner=RECIPIENT if failure=='terminal' else SENDER
                args={'remittance_id':'1'} if action=='claim' else {} if action=='pause' else {'wallet':RECIPIENT,'amount_wei':'1'}
                with self.assertRaises(b.BlockchainError):prepare(self.reader,owner,action,args,lambda value:value)
                self.assertFalse(any(p['method']=='eth_estimateGas' for payload in self.payloads for p in (payload if isinstance(payload,list) else [payload])))

