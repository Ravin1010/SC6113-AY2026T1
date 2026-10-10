"""Offline verification/preparation/indexing tests. Public fixture addresses, no deployment."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from hexbytes import HexBytes
from eth_utils import event_abi_to_log_topic
from web3 import Web3
from flask import g
from app import create_app
from backend.blockchain import SepoliaReader, BlockchainError, matching_runtime, ROOT, checksum, get_reader
from backend.database import get_db
from backend.indexer import index_events
from backend.preparation import prepare, ACTIONS

BUILD = json.loads((ROOT/'deployment/accepted-build.json').read_text())
ADMIN, SENDER, RECIPIENT = [checksum('0x'+letter*40) for letter in 'abc']
ADDRESSES = {name:checksum('0x'+str(i)*40) for i,name in enumerate(('RoleRegistry','deposit_money','paynow'),1)}
HASH = lambda n: HexBytes(n.to_bytes(32,'big'))


def fixture():
    reader = SepoliaReader.__new__(SepoliaReader)
    codec = Web3()
    reader.build = copy.deepcopy(BUILD)
    reader.contracts = {name:codec.eth.contract(address=address,abi=BUILD['contracts'][name]['abi']) for name,address in ADDRESSES.items()}
    reader.config = {'BLOCKCHAIN_DEPLOYMENT_ID':'offline-fixture'}
    reader.block, reader.block_hash = 20, Web3.to_hex(HASH(20))
    reader.manifest = {'chainId':11155111,'deploymentId':'offline-fixture','admin':ADMIN,'contracts':{}}
    codes,txs,receipts = {},{},{}
    for i,(name,address) in enumerate(ADDRESSES.items(),1):
        artifact = reader.build['contracts'][name]
        actual = bytearray.fromhex(artifact['runtimeBytecode'])
        for spans in artifact['immutableReferences'].values():
            for span in spans:actual[span['start']:span['start']+span['length']] = b'\x12'*span['length']
        codes[address] = bytes(actual)
        args = [] if name=='RoleRegistry' else [ADDRESSES['RoleRegistry']]
        if name=='paynow':args.append(ADDRESSES['deposit_money'])
        txhash = Web3.to_hex(HASH(i+100))
        txs[txhash] = {'input':HexBytes(bytes.fromhex(artifact['creationBytecode'])+codec.codec.encode(['address']*len(args),args)),'to':None,'from':ADMIN}
        receipts[txhash] = {'status':1,'contractAddress':address,'blockNumber':i,'blockHash':HASH(i),'transactionHash':HexBytes(txhash)}
        reader.manifest['contracts'][name] = {'address':address,'transactionHash':txhash,'blockNumber':i}
    roles = {SENDER.lower():{'sender':True,'recipient':False,'admin':False},RECIPIENT.lower():{'sender':False,'recipient':True,'admin':False},ADMIN.lower():{'sender':False,'recipient':False,'admin':True}}
    values = {('RoleRegistry','admin'):ADMIN,('RoleRegistry','paused'):False,('deposit_money','roleRegistry'):ADDRESSES['RoleRegistry'],('deposit_money','remittanceContract'):ADDRESSES['paynow'],('paynow','roleRegistry'):ADDRESSES['RoleRegistry'],('paynow','funding'):ADDRESSES['deposit_money'],('paynow','remittanceCount'):1}
    def call(name,function,*args):
        if function=='isSender':return roles.get(args[0].lower(),{}).get('sender',False)
        if function=='isRecipient':return roles.get(args[0].lower(),{}).get('recipient',False)
        if function=='availableBalance':return 10**18
        if function=='reservedBalance':return 10**17
        if function=='transaction':return [SENDER,RECIPIENT,10**17,0]
        if function=='reservations':return [SENDER,RECIPIENT,10**17,True]
        return values[name,function]
    reader.call = call
    eth = SimpleNamespace(chain_id=11155111, get_code=lambda address,**kwargs:codes[address], get_transaction=lambda txhash:txs[Web3.to_hex(txhash) if not isinstance(txhash,str) else txhash],
                          get_transaction_receipt=lambda txhash:receipts[Web3.to_hex(txhash) if not isinstance(txhash,str) else txhash],get_block=lambda n:{'hash':HASH(n)},call=lambda *args,**kwargs:b'',estimate_gas=lambda *args,**kwargs:50000,get_logs=lambda query:[])
    reader.web3 = SimpleNamespace(eth=eth,codec=codec.codec)
    reader.verify()
    return reader,values,roles,eth,codes,txs,receipts


class BlockchainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app = create_app({'TESTING':True,'DATABASE':str(Path(self.temp.name)/'test.db'),'SECRET_KEY':'test-only'})
        self.context=self.app.test_request_context();self.context.push();self.addCleanup(self.context.pop)
        self.reader,self.values,self.roles,self.eth,self.codes,self.txs,self.receipts = fixture()

    def rejection(self, change):
        change()
        with self.assertRaises(BlockchainError) as failure:self.reader.verify()
        self.assertEqual(failure.exception.code,'BLOCKCHAIN_DEPLOYMENT_UNVERIFIED')

    def test_reproduced_remix_build_retains_exact_sources_abi_and_strict_metadata(self):
        remix=json.loads((ROOT/'deployment/remix-build.json').read_text())
        self.assertEqual(remix['sources'],BUILD['sources'])
        self.assertEqual(remix['optimizer'],BUILD['optimizer'])
        self.assertEqual(remix['evmVersion'],'shanghai')
        for name,artifact in remix['contracts'].items():
            self.assertEqual(artifact['abi'],BUILD['contracts'][name]['abi'])
            self.assertTrue(artifact['source'].startswith('contracts/contracts/'))
            actual=bytearray.fromhex(artifact['runtimeBytecode'])
            self.assertTrue(matching_runtime(actual,artifact))
            self.assertFalse(matching_runtime(actual,BUILD['contracts'][name]))
            actual[-1]^=1
            self.assertFalse(matching_runtime(actual,artifact))

    def test_wallet_batch_receipt_uses_only_verified_contract_events(self):
        log=self.event();txhash=Web3.to_hex(log['transactionHash'])
        self.receipts[txhash].update(transactionHash=log['transactionHash'],blockNumber=4,logs=[log])
        self.txs[txhash]['to']=ADMIN
        result=self.reader.receipt(txhash)
        self.assertEqual(result['to'],ADMIN)
        self.assertEqual(result['deployment_logs'][0]['event'],'RemittanceCreated')
        self.assertEqual(result['deployment_logs'][0]['args']['recipient'],RECIPIENT)
        log['blockHash']=HASH(777)
        with self.assertRaises(BlockchainError):self.reader.receipt(txhash)

    def test_exact_sources_and_abis(self):
        for name,artifact in BUILD['contracts'].items():
            self.assertEqual(artifact['abi'],json.loads((ROOT/'static/abi'/f'{name}.json').read_text()))
        self.assertEqual(len(BUILD['contracts']),3)
        self.assertEqual(len(ACTIONS),10)

    def test_immutable_aware_runtime_and_metadata(self):
        for name,address in ADDRESSES.items():self.assertTrue(matching_runtime(self.codes[address],BUILD['contracts'][name]))
        modified=bytearray(self.codes[ADDRESSES['paynow']]);modified[-1]^=1
        self.assertFalse(matching_runtime(modified,BUILD['contracts']['paynow']))
        self.assertFalse(matching_runtime(b'',BUILD['contracts']['paynow']))

    def test_verified_getters_live_state(self):
        self.assertTrue(self.reader.state()['deployment_verified'])
        self.assertTrue(self.reader.wired)
        self.assertTrue(self.reader.user(SENDER)['sender'])
        self.assertEqual(self.reader.balances(SENDER)['available']['wei'],str(10**18))
        self.assertEqual(self.reader.remittance(1)['status'],'PENDING')
        with self.assertRaises(BlockchainError):self.reader.remittance(0)

    def test_wrong_chain_fail_closed(self):self.rejection(lambda:setattr(self.eth,'chain_id',1))
    def test_wrong_admin_fail_closed(self):self.rejection(lambda:self.values.update({('RoleRegistry','admin'):SENDER}))
    def test_wrong_funding_reference_fail_closed(self):self.rejection(lambda:self.values.update({('paynow','funding'):ADDRESSES['RoleRegistry']}))
    def test_wrong_trusted_contract_fail_closed(self):self.rejection(lambda:self.values.update({('deposit_money','remittanceContract'):SENDER}))
    def test_missing_code_fail_closed(self):self.rejection(lambda:self.codes.update({ADDRESSES['paynow']:b''}))
    def test_wrong_constructor_input_fail_closed(self):self.rejection(lambda:self.txs[next(iter(self.txs))].update(input=HexBytes('0x00')))
    def test_noncanonical_deployment_fail_closed(self):self.rejection(lambda:self.receipts[next(iter(self.receipts))].update(blockHash=HASH(999)))

    def test_reorg_during_live_read_rejected(self):
        self.eth.get_block=lambda n:{'hash':HASH(999)}
        with self.assertRaises(BlockchainError):self.reader.balances(SENDER)

    def test_terminal_actions_and_revoked_recipient_creation_rejected(self):
        actual=self.reader.call
        self.reader.call=lambda name,fn,*args:[SENDER,RECIPIENT,1,1] if fn=='transaction' else actual(name,fn,*args)
        for action,owner in [('claim',RECIPIENT),('cancel',SENDER)]:
            with self.assertRaises(BlockchainError):prepare(self.reader,owner,action,{'remittance_id':'1'},lambda a:a)
        self.roles[RECIPIENT.lower()]['recipient']=False
        with self.assertRaises(BlockchainError):prepare(self.reader,SENDER,'transfer',{'wallet':RECIPIENT,'amount_wei':'1'},lambda a:a)

    def test_pre_wiring_verified_but_actions_blocked(self):
        self.values['deposit_money','remittanceContract']='0x'+'0'*40;self.reader.verify()
        self.assertFalse(self.reader.wired)
        with self.assertRaises(BlockchainError) as failure:prepare(self.reader,SENDER,'deposit',{'amount_wei':'1'},lambda a:a)
        self.assertEqual(failure.exception.code,'BLOCKCHAIN_NOT_WIRED')

    def test_verification_flag_cannot_bypass(self):
        self.app.config.update(BLOCKCHAIN_DEPLOYMENT_VERIFIED=True,BLOCKCHAIN_RPC_URL='https://test.invalid',ROLE_REGISTRY_ADDRESS=ADDRESSES['RoleRegistry'],FUNDING_CONTRACT_ADDRESS=ADDRESSES['deposit_money'],REMITTANCE_CONTRACT_ADDRESS=ADDRESSES['paynow'],BLOCKCHAIN_DEPLOYMENT_ID='offline-fixture')
        with self.assertRaises(BlockchainError) as failure:get_reader()
        self.assertEqual(failure.exception.code,'BLOCKCHAIN_DEPLOYMENT_UNVERIFIED')

    def test_ten_unsigned_payloads_and_calldata(self):
        cases=[('authorizeSender',ADMIN,{'wallet':ADMIN}),('authorizeRecipient',ADMIN,{'wallet':ADMIN}),('revokeRole',ADMIN,{'wallet':SENDER,'role':0}),('pause',ADMIN,{}),('unpause',ADMIN,{}),('deposit',SENDER,{'amount_wei':'1'}),('withdraw',SENDER,{'amount_wei':'1'}),('transfer',SENDER,{'wallet':RECIPIENT,'amount_wei':'1'}),('claim',RECIPIENT,{'remittance_id':'1'}),('cancel',SENDER,{'remittance_id':'1'})]
        for action,owner,args in cases:
            with self.subTest(action=action):
                self.reader.paused=action=='unpause'
                result=prepare(self.reader,owner,action,args,lambda a:a)
                self.assertTrue(result['unsigned']);self.assertEqual(result['transaction']['chainId'],'0xaa36a7')
                name,function=ACTIONS[action]
                fn,decoded=self.reader.contracts[name].decode_function_input(result['transaction']['data'])
                self.assertEqual(fn.fn_name,function)
                self.assertEqual(result['transaction']['from'],owner)
                self.assertEqual(result['transaction']['value'],'0x1' if action=='deposit' else '0x0')
                self.assertEqual(result['gas_estimate'],'50000')

    def test_revocation_preserves_all_exit_preparation(self):
        self.roles[SENDER.lower()]['sender']=False;self.roles[RECIPIENT.lower()]['recipient']=False
        for action,owner,args in [('withdraw',SENDER,{'amount_wei':'1'}),('cancel',SENDER,{'remittance_id':'1'}),('claim',RECIPIENT,{'remittance_id':'1'})]:
            self.assertTrue(prepare(self.reader,owner,action,args,lambda a:a)['unsigned'])
        for action,args in [('deposit',{'amount_wei':'1'}),('transfer',{'wallet':RECIPIENT,'amount_wei':'1'})]:
            with self.assertRaises(BlockchainError):prepare(self.reader,SENDER,action,args,lambda a:a)

    def test_full_pause_all_five_actions_and_admin_allowed(self):
        self.reader.paused=True
        for action,owner,args in [('deposit',SENDER,{'amount_wei':'1'}),('withdraw',SENDER,{'amount_wei':'1'}),('transfer',SENDER,{'wallet':RECIPIENT,'amount_wei':'1'}),('claim',RECIPIENT,{'remittance_id':'1'}),('cancel',SENDER,{'remittance_id':'1'})]:
            with self.assertRaises(BlockchainError) as failure:prepare(self.reader,owner,action,args,lambda a:a)
            self.assertEqual(failure.exception.code,'SYSTEM_PAUSED')
        self.assertTrue(prepare(self.reader,ADMIN,'authorizeSender',{'wallet':ADMIN},lambda a:a)['unsigned'])

    def test_wrong_participants_and_nonadmin_rejected(self):
        for action,owner,args in [('claim',SENDER,{'remittance_id':'1'}),('cancel',RECIPIENT,{'remittance_id':'1'}),('pause',SENDER,{}),('transfer',SENDER,{'wallet':SENDER,'amount_wei':'1'}),('withdraw',SENDER,{'amount_wei':str(2*10**18)}),('revokeRole',ADMIN,{'wallet':SENDER,'role':2})]:
            with self.assertRaises(BlockchainError):prepare(self.reader,owner,action,args,lambda a:a)

    def test_simulation_failure_and_invalid_action_no_broadcast(self):
        self.eth.call=lambda *args,**kw:(_ for _ in ()).throw(ValueError('revert'))
        with self.assertRaises(BlockchainError) as failure:prepare(self.reader,SENDER,'deposit',{'amount_wei':'1'},lambda a:a)
        self.assertEqual(failure.exception.code,'TRANSACTION_SIMULATION_FAILED')
        with self.assertRaises(BlockchainError):prepare(self.reader,ADMIN,'setRemittanceContract',{},lambda a:a)
        self.assertFalse(hasattr(self.eth,'send_transaction'))

    def event(self,block=4):
        abi=next(a for a in BUILD['contracts']['paynow']['abi'] if a.get('name')=='RemittanceCreated')
        args=[1,SENDER,RECIPIENT,10**17,0]
        indexed=[(field,value) for field,value in zip(abi['inputs'],args) if field['indexed']]
        ordinary=[(field,value) for field,value in zip(abi['inputs'],args) if not field['indexed']]
        log={'address':ADDRESSES['paynow'],'topics':[HexBytes(event_abi_to_log_topic(abi))]+[HexBytes(self.reader.web3.codec.encode([field['type']],[value])) for field,value in indexed],
             'data':HexBytes(self.reader.web3.codec.encode([field['type'] for field,value in ordinary],[value for field,value in ordinary])),
             'blockNumber':block,'blockHash':HASH(block),'transactionHash':HASH(999),'transactionIndex':0,'logIndex':0,'removed':False}
        self.txs[Web3.to_hex(HASH(999))]={'from':SENDER,'to':ADDRESSES['paynow']}
        self.receipts[Web3.to_hex(HASH(999))]={'status':1,'blockHash':HASH(block)}
        self.eth.get_logs=lambda query:[log] if query['address']==ADDRESSES['paynow'] and query['fromBlock']<=block<=query['toBlock'] else []
        return log

    def test_index_starts_at_deployments_idempotent_confirmed_scope(self):
        self.event();queries=[];actual=self.eth.get_logs
        self.eth.get_logs=lambda query:(queries.append(query) or actual(query))
        result=index_events(self.reader);index_events(self.reader)
        db=get_db();self.assertEqual(db.execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM indexed_transactions').fetchone()[0],1)
        self.assertEqual(result['confirmed_head'],15)
        self.assertTrue(all(query['fromBlock']>=self.reader.starts[next(name for name,c in self.reader.contracts.items() if c.address==query['address'])] for query in queries))
        event=db.execute('SELECT * FROM indexed_events').fetchone();self.assertEqual(event['remittance_id'],'1');self.assertEqual(event['log_index'],0);self.assertEqual(event['block_hash'],Web3.to_hex(HASH(4)))
        self.assertEqual(json.loads(event['payload_json'])['args']['recipient'],RECIPIENT)

    def test_reorg_discards_orphaned_cache_and_replays(self):
        self.event();index_events(self.reader)
        self.eth.get_logs=lambda query:[]
        original=self.eth.get_block
        self.eth.get_block=lambda n:{'hash':HASH(444)} if n==15 else original(n)
        result=index_events(self.reader)
        self.assertTrue(result['reconciled_reset']);self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],0)

    def test_inconsistent_log_rolls_back(self):
        log=self.event();log['blockHash']=HASH(777)
        with self.assertRaises(BlockchainError):index_events(self.reader)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],0)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexing_state').fetchone()[0],0)

    def test_unconfirmed_log_not_indexed(self):
        self.event(block=19);index_events(self.reader)
        self.assertEqual(get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0],0)

    def test_receipt_canonical_success_and_confirmations(self):
        txhash=next(iter(self.receipts));self.receipts[txhash]['transactionHash']=HexBytes(txhash)
        result=self.reader.receipt(txhash)
        self.assertTrue(result['canonical']);self.assertEqual(result['confirmations'],20)
        self.assertEqual(result['status'],'CONFIRMED')

if __name__=='__main__':unittest.main()
