"""Reproducible controlled RPC comparison; never accesses Sepolia or credentials."""
import argparse,contextlib,csv,json,subprocess,sys,tempfile,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import backend.blockchain as after
from backend.indexer import index_events
from backend.preparation import prepare
from app import create_app
from test_static_verification import World
from test_blockchain import SENDER,RECIPIENT
BASE='324a0f913b432ae0b0746f5ade5128860fbf303b'
def run(module,label,delay):
 world=World(delay);world.values[('paynow','remittanceCount')]=11
 world.records={i:[SENDER,RECIPIENT,10**17,0] for i in range(1,12)}
 rows=[]
 with tempfile.TemporaryDirectory() as temporary,contextlib.ExitStack() as stack:
  app=create_app({'TESTING':True,'DATABASE':str(Path(temporary)/'profile.db'),'SECRET_KEY':'profile-only','BLOCKCHAIN_DEPLOYMENT_ID':'offline-fixture'})
  stack.enter_context(app.app_context())
  for p in world.patches(module):stack.enter_context(p)
  for endpoint in ['users/me','users/me/balances','remittances','transactions','transactions/prepare']:
   prior=world.counter.copy();full=world.full;started=time.perf_counter()
   reader=module.SepoliaReader(world.config)
   if endpoint=='users/me':reader.user(SENDER)
   elif endpoint=='users/me/balances':reader.balances(SENDER)
   elif endpoint=='remittances':
    with reader.snapshot_batch() if hasattr(reader,'snapshot_batch') else contextlib.nullcontext():
     for i in range(reader.count,0,-1):reader.remittance(i)
   elif endpoint=='transactions':index_events(reader)
   else:prepare(reader,SENDER,'transfer',{'wallet':RECIPIENT,'amount_wei':'1'},lambda x:x)
   delta=world.counter-prior
   rows.append({'implementation':label,'endpoint':'/api/'+endpoint,'rpc_calls':sum(delta.values()),'static_verifications':world.full-full,'elapsed_ms':round((time.perf_counter()-started)*1000,2),'controlled_rpc_delay_ms':delay*1000,'rpc_breakdown':json.dumps(dict(delta),sort_keys=True)})
 world.close();return rows
parser=argparse.ArgumentParser();parser.add_argument('--rpc-delay-ms',type=float,default=5);args=parser.parse_args()
before=types.ModuleType('profile_before');before.__file__=str(ROOT/'backend/blockchain.py')
exec(compile(subprocess.check_output(['git','show',BASE+':backend/blockchain.py'],cwd=ROOT,text=True),before.__file__,'exec'),before.__dict__)
after.clear_verified_deployments()
rows=run(before,'before',args.rpc_delay_ms/1000)+run(after,'after',args.rpc_delay_ms/1000)
path=ROOT/'results/iteration9_read_performance.csv'
with path.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
text=['# Controlled verified-read characterization','',f'Baseline: `{BASE}`. Synthetic RPC fixture; 11 remittances, empty-event historical catch-up; {args.rpc_delay_ms:g} ms injected per counted RPC operation.','Counts cover the verified-reader and endpoint operation, not authentication/HTTP/Turso transport. First account request is cold; subsequent requests share verified static evidence. No public RPC or new transactions.','', '| Endpoint | Before RPC | After RPC | Before full verify | After full verify | Before ms | After ms |','|---|---:|---:|---:|---:|---:|---:|']
for old,new in zip(rows[:5],rows[5:]):text.append(f"| {old['endpoint']} | {old['rpc_calls']} | {new['rpc_calls']} | {old['static_verifications']} | {new['static_verifications']} | {old['elapsed_ms']} | {new['elapsed_ms']} |")
text+=['','Warm reads still fetch runtime bytes, chain ID, historical/verification anchors, fresh snapshot, pause/count and endpoint-specific state. A 60-second expiry/restart/input change reruns full proof.','These measured local numbers are not hosted speed claims. Real RPC latency, remittance scanning, index catch-up and synchronous dashboard ordering remain limitations.']
(ROOT/'results/iteration9_read_performance.md').write_text('\n'.join(text)+'\n')
for row in rows:print(row['implementation'],row['endpoint'],row['rpc_calls'],row['static_verifications'],row['elapsed_ms'])
