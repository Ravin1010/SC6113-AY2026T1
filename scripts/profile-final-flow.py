"""Controlled final-path comparison; no hosted timing or public-chain access.

Uses the preceding reproducible fixture definitions without executing their CLI.
Network round-trip waits are emulated; real Web3 batch semantics are separately tested.
"""
import csv,json,types,sys,time,contextlib,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
source=(ROOT/'scripts/profile-warm-reads.py').read_text().split('parser = argparse.ArgumentParser()')[0]
source=source.replace("BASE = 'bd571500c73690bd2a58a991d49fded4bb025ac9'", "BASE = '558fb854168a355f8373e60272ebe53c09e56c7c'")
source=source.replace("else: (baseline_prepare if label == 'before' else prepare)(reader,SENDER,'transfer',{'wallet':RECIPIENT,'amount_wei':'1'},lambda x:x)", """elif endpoint == 'receipt':
                tx=next(iter(world.receipts));world.receipts[tx]['logs']=[];world.txs[tx]['to']=world.base.contracts['RoleRegistry'].address
                reader.receipt(tx)
            else:
                action=endpoint.split('/')[-1];owner,arguments=SCENARIOS[action]
                prepare(reader,owner,action,arguments,lambda x:x)""")
source=source.replace("reader = module.SepoliaReader(world.config)", "reader = module.SepoliaReader(world.config,receipt_only=True) if endpoint=='receipt' and hasattr(module.SepoliaReader,'simulate') else module.SepoliaReader(world.config)")
source=source.replace("stack.enter_context(patch.object(module.SepoliaReader,'remittances',many))", """stack.enter_context(patch.object(module.SepoliaReader,'remittances',many))
            if hasattr(module.SepoliaReader,'simulate'):
                def simulate(reader,transaction):
                    world.hit('batch_transport');saved=world.latency;world.latency=0
                    try:
                        reader.web3.eth.call(transaction,block_identifier=reader.block)
                        gas=reader.web3.eth.estimate_gas(transaction,block_identifier=reader.block)
                    finally:world.latency=saved
                    world.counter['batched_messages']+=2
                    return gas
                stack.enter_context(patch.object(module.SepoliaReader,'simulate',simulate))""")
fixture=types.ModuleType('final_profile_fixture');fixture.__file__=str(ROOT/'scripts/profile-warm-reads.py')
exec(compile(source,fixture.__file__,'exec'),fixture.__dict__)
from test_blockchain import ADMIN,SENDER,RECIPIENT
from backend.preparation import prepare as current_prepare
fixture.SCENARIOS={'transfer':(SENDER,{'wallet':RECIPIENT,'amount_wei':'1'}),'deposit':(SENDER,{'amount_wei':'1'}),
 'withdraw':(SENDER,{'amount_wei':'1'}),'claim':(RECIPIENT,{'remittance_id':'1'}),'cancel':(SENDER,{'remittance_id':'1'}),
 'authorizeSender':(ADMIN,{'wallet':RECIPIENT})}
rows=[]
for label,module in [('before',fixture.legacy('backend/blockchain.py','previous_reader')),('after',fixture.after)]:
 fixture.prepare=fixture.legacy('backend/preparation.py','previous_prepare').prepare if label=='before' else current_prepare
 modes=[('dashboard',['users/me','users/me/balances','remittances','transactions'] if label=='before' else ['users/me','users/me/balances','remittances']),
        ('warm',['transactions/prepare/'+action for action in fixture.SCENARIOS]+['receipt'])]
 for mode,endpoints in modes:
  data=fixture.run(module,'after',mode,endpoints,.005)
  for row in data:row['implementation']=label
  rows+=data
with tempfile.TemporaryDirectory() as temporary:
 from app import create_app
 from backend.database import get_db
 import hashlib
 app=create_app({'TESTING':True,'DATABASE':str(Path(temporary)/'cache.db'),'SECRET_KEY':'profile-only','BLOCKCHAIN_DEPLOYMENT_ID':'offline-fixture'})
 with app.app_context():
  db=get_db();wallet=SENDER.lower()
  db.execute('INSERT INTO app_wallets VALUES (?,?,?)',(wallet,1,1))
  db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,NULL)',(hashlib.sha256(b'profile-only').hexdigest(),wallet,1,int(time.time())+3600));db.commit()
 client=app.test_client()
 with client.session_transaction() as session:session['auth_token']='profile-only'
 started=time.perf_counter();response=client.get('/api/transactions?limit=10&offset=0');elapsed=round((time.perf_counter()-started)*1000,2)
 assert response.status_code==200 and response.json['authoritative'] is False and response.json['live_blockchain_checked'] is False
 rows.append({'implementation':'after','mode':'cached SQLite HTTP','endpoint':'/api/transactions','rpc_messages':0,'transport_round_trips':0,'static_verifications':0,'runtime_code':0,'block_reads':0,'chain_id':0,'contract_calls':0,'batch_transports':0,'elapsed_ms':elapsed,'breakdown':'{}'})
path=ROOT/'results/iteration9_final_performance.csv'
with path.open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
lines=['# Final controlled preparation/read characterization','', 'Baseline: 558fb854168a355f8373e60272ebe53c09e56c7c. Five ms emulated round-trip wait; 11 remittances, empty-event history. Logical messages differ from transports. No hosted timing claims.',
 '| Implementation / operation | Messages | Round trips | Elapsed ms |','|---|---:|---:|---:|']
for row in rows:lines.append(f"| {row['implementation']} {row['mode']} {row['endpoint']} | {row['rpc_messages']} | {row['transport_round_trips']} | {row['elapsed_ms']} |")
lines+=['','After /api/transactions is DB-only: zero RPC messages/round trips. Explicit POST sync retains bounded historical indexing separately. Before dashboard readiness awaited indexed Activity; after readiness excludes Activity.',
 'Browser performance evidence, including local input validation and confirmation-visible latency, is recorded separately by tests/frontend.cjs when FRONTEND_PERF_OUTPUT is set.',
 'Middleware/provider-specific calls, Turso/network latency, wallet approval and Sepolia block inclusion are outside this fixture.']
(ROOT/'results/iteration9_final_performance.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
