"""Controlled RPC evidence: no public network, production credentials or DB writes."""
import copy,json,tempfile,time,unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3
import backend.blockchain as b
from backend.preparation import prepare
import test_blockchain as old

class World:
    def __init__(self, latency=0):
        self.base,self.values,self.roles,self.eth,self.codes,self.txs,self.receipts=old.fixture()
        self.temp=tempfile.TemporaryDirectory();self.manifest=Path(self.temp.name)/'manifest.json'
        self.manifest.write_text(json.dumps(self.base.manifest))
        self.config={**dict(zip(b.FIELDS,['https://offline.invalid',11155111,*old.ADDRESSES.values(),'offline-fixture'])), 'BLOCKCHAIN_MANIFEST_PATH':str(self.manifest)}
        self.head=20;self.chain=11155111;self.counter=Counter();self.full=0;self.latency=latency
        self.available={old.SENDER.lower():10**18,old.RECIPIENT.lower():20}
        self.records={1:[old.SENDER,old.RECIPIENT,10**17,0]}
        world=self
        class Eth:
            @property
            def block_number(self):world.hit('block_number');return world.head
            @property
            def chain_id(self):world.hit('chain_id');return world.chain
            def contract(self, address,abi):return world.base.contracts[next(n for n,a in old.ADDRESSES.items() if a==address)]
            def get_code(self,*a,**kw):world.hit('get_code');return world.eth.get_code(*a,**kw)
            def get_transaction(self,*a):world.hit('get_transaction');return world.eth.get_transaction(*a)
            def get_transaction_receipt(self,*a):world.hit('get_transaction_receipt');return world.eth.get_transaction_receipt(*a)
            def get_block(self,*a):world.hit('get_block');return world.eth.get_block(*a)
            def get_logs(self,*a):world.hit('get_logs');return world.eth.get_logs(*a)
            def call(self,*a,**kw):world.hit('simulation');return world.eth.call(*a,**kw)
            def estimate_gas(self,*a,**kw):world.hit('estimate_gas');return world.eth.estimate_gas(*a,**kw)
        self.rpc=SimpleNamespace(eth=Eth(),codec=self.base.web3.codec)
    def hit(self,method):
        self.counter[method]+=1
        if self.latency:time.sleep(self.latency)
    def call(self,reader,name,fn,*args):
        self.hit('contract_call')
        if fn=='availableBalance':return self.available.get(args[0].lower(),0)
        if fn=='transaction':return self.records[args[0]]
        return self.base.call(name,fn,*args)
    def patches(self,module):
        world=self
        class FakeWeb3(Web3):
            HTTPProvider=staticmethod(lambda *a,**kw:None)
            def __new__(cls,*a,**kw):return world.rpc
        real_verify=module.SepoliaReader.verify
        def verify(reader):world.full+=1;return real_verify(reader)
        return [patch.object(module,'Web3',FakeWeb3),patch.object(module.SepoliaReader,'call',lambda reader,name,fn,*args:world.call(reader,name,fn,*args)),patch.object(module.SepoliaReader,'verify',verify)]
    def close(self):self.temp.cleanup()

class StaticVerificationTests(unittest.TestCase):
    def setUp(self):
        b.clear_verified_deployments();self.addCleanup(b.clear_verified_deployments)
        self.world=World();self.addCleanup(self.world.close)
        for p in self.world.patches(b):p.start();self.addCleanup(p.stop)
    def reader(self):return b.SepoliaReader(self.world.config)
    def test_static_single_verification_and_distinct_dynamic_reader(self):
        a=self.reader();c=self.reader();self.assertIsNot(a,c);self.assertEqual(self.world.full,1)
        self.assertEqual(self.world.counter['get_transaction'],3);self.assertEqual(self.world.counter['get_transaction_receipt'],3)
    def test_dynamic_wallet_balance_pause_count_and_head_fresh(self):
        a=self.reader();self.world.head=21;self.world.values[('RoleRegistry','paused')]=True
        self.world.values[('paynow','remittanceCount')]=2;self.world.available[old.SENDER.lower()]=7
        self.world.roles[old.SENDER.lower()]['sender']=False
        self.world.records[1][3]=1
        c=self.reader();self.assertEqual(c.block,21);self.assertTrue(c.paused);self.assertFalse(a.paused)
        self.assertEqual(c.count,2);self.assertEqual(c.balances(old.SENDER)['available']['wei'],'7')
        self.assertEqual(c.balances(old.RECIPIENT)['available']['wei'],'20')
        self.assertEqual(c.remittance(1)['status'],'COMPLETED')
        self.assertFalse(c.user(old.SENDER)['sender']);self.assertTrue(c.user(old.RECIPIENT)['recipient']);self.assertEqual(self.world.full,1)
    def test_rpc_identity_change_reverifies(self):
        self.reader();self.world.config['BLOCKCHAIN_RPC_URL']='https://another-offline.invalid'
        self.reader();self.assertEqual(self.world.full,2)
    def test_manifest_change_reverifies_and_mismatch_rejects(self):
        self.reader();m=json.loads(self.world.manifest.read_text());m['admin']=old.SENDER
        self.world.manifest.write_text(json.dumps(m))
        with self.assertRaises(b.BlockchainError):self.reader()
        self.assertEqual(self.world.full,2)
    def test_build_and_source_content_changes_reject_even_same_mtime(self):
        self.reader()
        # Copy inputs, never alter committed build/source files.
        root=Path(self.world.temp.name)/'root'
        for folder in ['deployment','contracts']:
            (root/folder).mkdir(parents=True)
            for file in (b.ROOT/folder).glob('*'):
                if file.is_file():(root/folder/file.name).write_bytes(file.read_bytes())
        with patch.object(b,'ROOT',root):
            self.reader()
            source=root/'contracts/RoleRegistry.sol';source.write_bytes(source.read_bytes()+b'\n')
            with self.assertRaises(b.BlockchainError):self.reader()
            source.write_bytes((old.ROOT/'contracts/RoleRegistry.sol').read_bytes())
            build=root/'deployment/accepted-build.json';obj=json.loads(build.read_text());obj['compiler']='bad';build.write_text(json.dumps(obj))
            with self.assertRaises(b.BlockchainError):self.reader()
    def test_runtime_identity_including_immutable_bytes_fresh(self):
        reader=self.reader();addr=old.ADDRESSES['paynow'];code=bytearray(self.world.codes[addr])
        references=reader.build['contracts']['paynow']['immutableReferences']
        start=next(iter(references.values()))[0]['start']
        code[start]^=1;self.world.codes[addr]=bytes(code)
        with self.assertRaises(b.BlockchainError):self.reader()
        self.assertFalse(b._static_contexts)
    def test_chain_change_rejected_on_cache_hit(self):
        self.reader();self.world.chain=1
        with self.assertRaises(b.BlockchainError):self.reader()
    def test_historical_anchor_reorg_rejects_cached_evidence(self):
        self.reader();actual=self.world.eth.get_block
        self.world.eth.get_block=lambda n:{'hash':old.HASH(999)} if n==1 else actual(n)
        with self.assertRaises(b.BlockchainError):self.reader()
    def test_ttl_revalidation_failure_has_no_stale_fallback(self):
        with patch.object(b.time,'monotonic',return_value=0):self.reader()
        self.world.eth.get_transaction=lambda _:(_ for _ in ()).throw(RuntimeError('offline failure'))
        with patch.object(b.time,'monotonic',return_value=61):
            with self.assertRaises(RuntimeError):self.reader()
        self.assertFalse(b._static_contexts)
    def test_unwired_relationship_never_cached(self):
        self.world.values[('deposit_money','remittanceContract')]=b.ZERO
        self.assertFalse(self.reader().wired);self.assertFalse(b._static_contexts)
        self.world.values[('deposit_money','remittanceContract')]=old.ADDRESSES['paynow']
        self.assertTrue(self.reader().wired);self.assertEqual(self.world.full,2)
    def test_receipt_confirmations_and_canonicality_not_cached(self):
        a=self.reader();tx=next(iter(self.world.receipts));self.world.receipts[tx]['logs']=[];self.world.txs[tx]['to']=old.ADDRESSES['RoleRegistry']
        first=a.receipt(tx);self.world.head=21;c=self.reader();second=c.receipt(tx)
        self.assertEqual(second['confirmations'],first['confirmations']+1)
        self.world.eth.get_block=lambda n:{'hash':old.HASH(777) if n==1 else old.HASH(n)}
        self.assertFalse(c.receipt(tx)['canonical'])
    def test_preparation_rechecks_dynamic_roles_pause_balance_recipient(self):
        self.reader()
        for kind in ['role','pause','balance','recipient']:
            with self.subTest(kind=kind):
                self.world.roles[old.SENDER.lower()]['sender']=kind!='role'
                self.world.roles[old.RECIPIENT.lower()]['recipient']=kind!='recipient'
                self.world.values[('RoleRegistry','paused')]=kind=='pause'
                self.world.available[old.SENDER.lower()]=0 if kind=='balance' else 10**18
                reader=self.reader()
                with self.assertRaises(b.BlockchainError):prepare(reader,old.SENDER,'transfer',{'wallet':old.RECIPIENT,'amount_wei':'1'},lambda x:x)
    def test_batch_checks_reorg_before_any_results_escape(self):
        reader=self.reader();actual=self.world.eth.get_block
        with self.assertRaises(b.BlockchainError):
            with reader.snapshot_batch():
                reader.remittance(1)
                self.world.eth.get_block=lambda n:{'hash':old.HASH(999)} if n==reader.block else actual(n)
    def test_cache_clear_forces_complete_verification(self):
        self.reader();b.clear_verified_deployments();self.reader();self.assertEqual(self.world.full,2)
    def test_concurrent_static_verification_is_single_flight(self):
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda _:self.reader(),range(3)))
        self.assertEqual(self.world.full,1)
