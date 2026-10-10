"""Read-only live API evidence using isolated Flask session fixtures; no wallet keys."""
import json
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import create_app
from backend.api import digest
from backend.database import get_db
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'deployment/sepolia.json').read_text())
results={
    'network':'Sepolia','authentication':'Isolated server-session fixture; no real MetaMask login or transaction signing claimed.',
    'blockchain_writes':0,'checks':[],'responses':{},'transient_errors':[],
    'earlier_run_observation':'Six read routes passed; initial run stopped on transient RPC unavailability at role lookup.' ,
}
with tempfile.TemporaryDirectory() as temp:
    app=create_app({'TESTING':True,'SECRET_KEY':secrets.token_hex(32),'DATABASE':str(Path(temp)/'reads.db'),
                   'BLOCKCHAIN_CHAIN_ID':manifest['chainId'],'BLOCKCHAIN_DEPLOYMENT_ID':manifest['deploymentId'],'BLOCKCHAIN_MANIFEST_PATH':str(root/'deployment/sepolia.json'),
                   'ROLE_REGISTRY_ADDRESS':manifest['contracts']['RoleRegistry']['address'],'FUNDING_CONTRACT_ADDRESS':manifest['contracts']['deposit_money']['address'],'REMITTANCE_CONTRACT_ADDRESS':manifest['contracts']['paynow']['address']})
    token,csrf=secrets.token_hex(32),secrets.token_hex(32)
    with app.app_context():
        db=get_db();now=int(time.time());address=manifest['admin'].lower()
        db.execute('INSERT INTO app_wallets VALUES (?,?,?)',(address,now,now))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,NULL)',(digest(token),address,now,now+3600));db.commit()
    client=app.test_client()
    with client.session_transaction() as session:session['auth_token'],session['csrf_token']=token,csrf
    def fetch(route):
        for attempt in range(3):
            response=client.get(route)
            if response.status_code!=503 or response.json.get('error',{}).get('code')!='BLOCKCHAIN_READER_UNAVAILABLE':
                return response
            results['transient_errors'].append({'route':route,'attempt':attempt+1,'error':response.json['error']['code']})
            (root/'deployment/live-read-validation.json').write_text(json.dumps(results,indent=2)+'\n')
            time.sleep(1)
        return response
    routes=['/api/users/me','/api/users/me/balances','/api/remittances','/api/transactions','/api/transactions/'+manifest['wiring']['transactionHash']+'/receipt','/api/transactions/audit','/api/users/roles/'+manifest['admin']]
    for route in routes:
        response=fetch(route)
        assert response.status_code==200,(route,response.status_code,response.json)
        value=response.json
        if route=='/api/users/me':
            assert value['roles']['admin'] is True and value['roles']['source']=='verified_contract'
            value.pop('application_metadata',None)
        if route=='/api/users/me/balances':assert value['authoritative'] and value['source']=='verified_contract'
        if route=='/api/remittances':assert value['authoritative'] and value['source']=='verified_contract'
        if route in ('/api/transactions','/api/transactions/audit'):assert not value['authoritative'] and value['live_blockchain_checked']
        if route.endswith('/receipt'):assert value['status']=='CONFIRMED' and value['canonical'] and len(value['deployment_logs'])==1
        results['responses'][route]=value;results['checks'].append({'route':route,'status':response.status_code,'passed':True})
        (root/'deployment/live-read-validation.json').write_text(json.dumps(results,indent=2)+'\n')
        print('PASS',route,flush=True)
    first=results['responses']['/api/transactions']['items']
    second=fetch('/api/transactions').json['items']
    assert len(first)==len(second)==1 and first[0]['tx_hash']==manifest['wiring']['transactionHash']
    results['checks'].append({'check':'canonical wiring event indexed; repeat request creates no duplicates','passed':True})
    response=client.post('/api/transactions/prepare',json={'action':'authorizeSender','arguments':{'wallet':manifest['admin']}},headers={'X-CSRF-Token':csrf})
    assert response.status_code==200 and response.json['unsigned'] is True
    results['responses']['unsigned_admin_simulation']=response.json
    results['checks'].append({'check':'unsigned authorizeSender calldata/read-only simulation; no send','passed':True})
    results['pass_count']=len(results['checks'])
    (root/'deployment/live-read-validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Live read checks:',results['pass_count'],'passed. Zero blockchain writes.',flush=True)
