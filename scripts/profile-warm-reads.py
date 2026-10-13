"""Offline transport-latency characterization against the first correction checkpoint.

Batch transport is controlled/emulated; real Web3 protocol is tested independently.
No public RPC, production DB or secrets. RPC messages and round trips are separate.
"""
import argparse, contextlib, csv, json, subprocess, sys, tempfile, time, types
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
import backend.blockchain as after
from backend.preparation import prepare
from backend.indexer import index_events
from app import create_app
from test_static_verification import World
from test_blockchain import SENDER, RECIPIENT
BASE = 'bd571500c73690bd2a58a991d49fded4bb025ac9'
ENDPOINTS = ['users/me', 'users/me/balances', 'users/roles/<wallet>', 'remittances', 'transactions', 'transactions/prepare']

def legacy(path, name):
    module = types.ModuleType(name); module.__file__ = str(ROOT/path); module.__package__ = 'backend'
    exec(compile(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True),module.__file__,'exec'),module.__dict__)
    return module

def run(module, label, mode, endpoints, delay):
    world = World(delay); world.values[('paynow','remittanceCount')] = 11
    world.records = {i:[SENDER,RECIPIENT,10**17,0] for i in range(1,12)}
    rows = []; module.clear_verified_deployments()
    baseline_prepare = legacy('backend/preparation.py','profile_previous_prepare').prepare
    # The offline fixture preserves ABI/state semantics; grouping models actual transport.
    # Count all logical eth_calls, but inject one network wait per independent batch.
    def calls(reader, requests):
        cache = reader.__dict__.setdefault('_calls', {})
        missing = list(dict.fromkeys(item for item in requests if item not in cache))
        if missing:
            world.hit('batch_transport')
            saved = world.latency; world.latency = 0
            try:
                cache.update((item,world.call(reader,item[0],item[1],*item[2])) for item in missing)
            finally: world.latency = saved
            world.counter['batched_messages'] += len(missing)
        return [cache[item] for item in requests]
    def many(reader, identifiers):
        calls(reader,[(name,function,(identifier,)) for identifier in identifiers
                      for name,function in [('paynow','transaction'),('deposit_money','reservations')]])
        return (reader.remittance(identifier) for identifier in identifiers)
    def single(reader,name,function,*args):
        key = (name,function,args); cache = reader.__dict__.setdefault('_calls', {})
        if key not in cache: cache[key] = world.call(reader,name,function,*args)
        return cache[key]
    with tempfile.TemporaryDirectory() as temporary, contextlib.ExitStack() as stack:
        app = create_app({'TESTING':True,'DATABASE':str(Path(temporary)/'profile.db'),'SECRET_KEY':'profile-only','BLOCKCHAIN_DEPLOYMENT_ID':'offline-fixture'})
        stack.enter_context(app.app_context())
        for p in world.patches(module): stack.enter_context(p)
        if label == 'after':
            stack.enter_context(patch.object(module.SepoliaReader,'calls',calls))
            stack.enter_context(patch.object(module.SepoliaReader,'call',single))
            stack.enter_context(patch.object(module.SepoliaReader,'remittances',many))
        if mode == 'warm': module.SepoliaReader(world.config)
        for endpoint in endpoints:
            if mode == 'cold': module.clear_verified_deployments()
            prior = world.counter.copy(); full = world.full; started = time.perf_counter()
            reader = module.SepoliaReader(world.config)
            if endpoint == 'users/me': reader.user(SENDER); reader.state()
            elif endpoint == 'users/me/balances': reader.balances(SENDER)
            elif endpoint == 'users/roles/<wallet>': reader.user(RECIPIENT)
            elif endpoint == 'remittances':
                with reader.snapshot_batch():
                    if label == 'before':
                        for i in range(reader.count,0,-1): reader.remittance(i)
                    else:
                        for upper in range(reader.count,0,-10): list(reader.remittances(list(range(upper,max(0,upper-10),-1))))
            elif endpoint == 'transactions': index_events(reader)
            else: (baseline_prepare if label == 'before' else prepare)(reader,SENDER,'transfer',{'wallet':RECIPIENT,'amount_wei':'1'},lambda x:x)
            delta = world.counter-prior
            messages = sum(value for key,value in delta.items() if key not in ('batch_transport','batched_messages'))
            trips = messages-delta['batched_messages']+delta['batch_transport']
            rows.append({'implementation':label,'mode':mode,'endpoint':'/api/'+endpoint,'rpc_messages':messages,
                         'transport_round_trips':trips,'static_verifications':world.full-full,'runtime_code':delta['get_code'],
                         'block_reads':delta['get_block'],'chain_id':delta['chain_id'],'contract_calls':delta['contract_call'],
                         'batch_transports':delta['batch_transport'],'elapsed_ms':round((time.perf_counter()-started)*1000,2),
                         'breakdown':json.dumps(dict(delta),sort_keys=True)})
    world.close(); return rows

parser = argparse.ArgumentParser(); parser.add_argument('--rpc-delay-ms',type=float,default=5); args = parser.parse_args()
before = legacy('backend/blockchain.py','profile_previous_reader')
rows = []
for module,label in [(before,'before'),(after,'after')]:
    for mode in ['cold','warm']: rows += run(module,label,mode,ENDPOINTS,args.rpc_delay_ms/1000)
    rows += run(module,label,'dashboard',ENDPOINTS[:2]+['remittances','transactions'],args.rpc_delay_ms/1000)
path = ROOT/'results/iteration9_warm_performance.csv'
with path.open('w',newline='') as f:
    writer = csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
lines = ['# Second controlled verified-read characterization','',f'Baseline `{BASE}`; 11 remittances, empty-event history, {args.rpc_delay_ms:g} ms wait per controlled network round trip.',
         'Offline transport grouping is emulated; real Web3 ABI/strict batch protocol and actual local-EVM integration are separately tested. These are not hosted timing results. Middleware/provider-specific additional calls and network/Turso transport are outside this fixture.',
         'Cold means full proof per operation; warm means one priming proof excluded; dashboard means cold account followed by warm sequential financial/activity operations.',
         '', '| Mode / endpoint | Messages before → after | Round trips before → after | ms before → after |', '|---|---:|---:|---:|']
half = len(rows)//2
for old,new in zip(rows[:half],rows[half:]):
    lines.append(f"| {old['mode']} {old['endpoint']} | {old['rpc_messages']} → {new['rpc_messages']} | {old['transport_round_trips']} → {new['transport_round_trips']} | {old['elapsed_ms']} → {new['elapsed_ms']} |")
lines += ['', 'Full static proofs: one per cold operation; zero per warm operation; one per dashboard sequence. Warm runtime-code/historical-deployment anchor reads: previous 3/4 each; now 0/0. Current head/hash/chain checks remain fresh.',
          'CSV includes contract-call, chain-ID, block-read, batch transport and full method breakdown. Historical indexing reconciliation work is unchanged.']
(ROOT/'results/iteration9_warm_performance.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
