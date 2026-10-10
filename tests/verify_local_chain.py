"""Verify real Web3 HTTP/ABI/event behavior against the ephemeral local test EVM."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import create_app
from backend.blockchain import get_reader
from backend.indexer import index_events
from backend.database import get_db
from backend.preparation import prepare
value=json.load(sys.stdin)
manifest=json.loads(Path(value['manifest']).read_text())
app=create_app({'TESTING':True,'DATABASE':value['database'],
                'TURSO_DATABASE_URL':value['database'] if os.getenv('LOCAL_DB_DRIVER')=='libsql' else '',
                'TURSO_AUTH_TOKEN':'','BLOCKCHAIN_RPC_URL':value['rpc'],'BLOCKCHAIN_DEPLOYMENT_ID':manifest['deploymentId'],'BLOCKCHAIN_MANIFEST_PATH':value['manifest'],
                'ROLE_REGISTRY_ADDRESS':manifest['contracts']['RoleRegistry']['address'],'FUNDING_CONTRACT_ADDRESS':manifest['contracts']['deposit_money']['address'],'REMITTANCE_CONTRACT_ADDRESS':manifest['contracts']['paynow']['address']})
with app.test_request_context():
    reader=get_reader();assert reader.state()['wired']
    assert reader.user(value['sender'])['sender']
    assert reader.balances(value['sender'])['available']['wei']==str(2*10**15)
    assert reader.remittance(1)['status']=='COMPLETED'
    assert reader.remittance(2)['status']=='CANCELLED'
    progress=index_events(reader);assert progress['caught_up']
    before=get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0]
    assert before>=10
    index_events(reader);assert get_db().execute('SELECT COUNT(*) FROM indexed_events').fetchone()[0]==before
    assert prepare(reader,value['sender'],'withdraw',{'amount_wei':'1'},lambda a:a)['unsigned']
    print(f'Local HTTP integration ({os.getenv("LOCAL_DB_DRIVER", "sqlite3")}): 8 assertions passed; {before} canonical events indexed, repeat run unchanged. No Sepolia access.')
