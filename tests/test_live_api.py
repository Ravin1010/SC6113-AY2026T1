"""Authenticated API integration with explicit offline verified-reader fixtures."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from eth_account import Account
from eth_account.messages import encode_defunct
from web3.exceptions import Web3RPCError
from app import create_app
from test_blockchain import fixture, RECIPIENT


class LiveAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=create_app({'TESTING':True,'DATABASE':str(Path(self.temp.name)/'test.db'),'SECRET_KEY':'test-only','BLOCKCHAIN_DEPLOYMENT_ID':'offline-fixture'})
        self.client=self.app.test_client();self.account=Account.create()
        nonce=self.client.post('/api/auth/nonce',json={'wallet':self.account.address}).json
        signature=self.account.sign_message(encode_defunct(text=nonce['message'])).signature.hex()
        login=self.client.post('/api/auth/verify',json={'wallet':self.account.address,'nonce':nonce['nonce'],'signature':signature})
        self.csrf={'X-CSRF-Token':login.json['csrf_token']}
        self.reader,_,self.roles,*_=fixture()
        self.roles[self.account.address.lower()]={'sender':True,'recipient':False,'admin':False}
        actual=self.reader.call
        self.reader.call=lambda name,fn,*args:[self.account.address,RECIPIENT,10**17,0] if fn=='transaction' else actual(name,fn,*args)
        self.mock=patch('backend.api.get_reader',return_value=self.reader);self.mock.start();self.addCleanup(self.mock.stop)

    def test_live_roles_balances_and_detail_authority(self):
        me=self.client.get('/api/users/me');self.assertTrue(me.json['roles']['sender']);self.assertFalse(me.json['roles']['admin'])
        balance=self.client.get('/api/users/me/balances');self.assertEqual(balance.json['available']['wei'],str(10**18));self.assertTrue(balance.json['authoritative'])
        detail=self.client.get('/api/remittances/1');self.assertEqual(detail.json['status'],'PENDING');self.assertTrue(detail.json['authoritative'])

    def test_list_contract_discovery_and_history_cache_provenance(self):
        items=self.client.get('/api/remittances').json;self.assertEqual([item['id'] for item in items['items']],['1']);self.assertEqual(items['discovery'],'direct_contract_scan');self.assertTrue(items['authoritative'])
        history=self.client.get('/api/transactions').json;self.assertTrue(history['live_blockchain_checked']);self.assertFalse(history['authoritative']);self.assertTrue(history['indexing_available'])

    def test_admin_derived_from_chain_only(self):
        self.assertEqual(self.client.get('/api/transactions/audit').status_code,403)
        self.reader.admin=self.account.address
        self.assertEqual(self.client.get('/api/transactions/audit').status_code,200)

    def test_prepare_csrf_auth_validation(self):
        endpoint='/api/transactions/prepare';body={'action':'deposit','arguments':{'amount_wei':'1'}}
        self.assertEqual(self.app.test_client().post(endpoint,json=body).status_code,401)
        self.assertEqual(self.client.post(endpoint,json=body).status_code,403)
        result=self.client.post(endpoint,json=body,headers=self.csrf);self.assertEqual(result.status_code,200);self.assertTrue(result.json['unsigned'])
        self.assertEqual(result.json['transaction']['from'],self.account.address)
        for payload in [{'action':'setRemittanceContract','arguments':{}},{'action':'deposit','arguments':{'amount_wei':1}},{'action':'deposit','arguments':{'amount_wei':'1','from':'forged'}}]:
            self.assertEqual(self.client.post(endpoint,json=payload,headers=self.csrf).status_code,400)

    def test_role_lookup_validates_address(self):
        self.assertEqual(self.client.get('/api/users/roles/bad').status_code,400)
        self.assertTrue(self.client.get('/api/users/roles/'+RECIPIENT).json['recipient'])

    def test_rpc_failure_is_structured(self):
        self.reader.balances=lambda *args:(_ for _ in ()).throw(Web3RPCError('test unavailable'))
        response=self.client.get('/api/users/me/balances');self.assertEqual(response.status_code,503);self.assertEqual(response.json['error']['code'],'BLOCKCHAIN_READER_UNAVAILABLE')

    def test_claim_prepare_survives_role_revocation(self):
        self.roles[self.account.address.lower()]['sender']=False
        response=self.client.post('/api/transactions/prepare',json={'action':'cancel','arguments':{'remittance_id':'1'}},headers=self.csrf)
        self.assertEqual(response.status_code,200)

    def test_batched_receipt_association_uses_verified_participants(self):
        tx_hash='0x'+'f'*64
        wrapper='0x'+'b'*40
        relayer='0x'+'c'*40
        result={'from':relayer,'to':wrapper,'status':'CONFIRMED','canonical':True,
                'deployment_logs':[{'contract':'paynow','event':'RemittanceClaimed',
                    'args':{'sender':RECIPIENT,'recipient':self.account.address}}]}
        self.reader.receipt=lambda _:result
        self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,200)
        for event,field in [('FundsDeposited','sender'),('FundsWithdrawn','owner'),
                            ('RemittanceCancelled','sender'),('RoleAuthorized','admin')]:
            result['deployment_logs']=[{'event':event,'args':{field:self.account.address}}]
            self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,200)
        result['deployment_logs']=[{'event':'RemittanceClaimed','args':{'sender':RECIPIENT,'recipient':RECIPIENT}}]
        self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,403)
        result['deployment_logs']=[]
        self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,403)
        result['from']=self.account.address
        self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,403)
        result['to']=next(iter(self.reader.contracts.values())).address
        self.assertEqual(self.client.get('/api/transactions/'+tx_hash+'/receipt').status_code,200)

if __name__=='__main__':unittest.main()
