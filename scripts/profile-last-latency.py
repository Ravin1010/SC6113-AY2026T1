"""Actual Web3 transport/ABI profiling with in-memory synthetic RPC; no public chain."""
import contextlib,csv,json,subprocess,sys,time,types
from pathlib import Path
from unittest.mock import patch
from eth_utils.abi import collapse_if_tuple
from web3 import Web3,HTTPProvider
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_static_verification import World
from test_blockchain import ADMIN,SENDER,RECIPIENT,HASH,ADDRESSES,BUILD
import backend.blockchain as after
from backend.preparation import prepare as current_prepare
BASE='8fdb117e33cebdad69784938408f45e204984f26'
def legacy(path,name):
 module=types.ModuleType(name);module.__file__=str(ROOT/path);module.__package__='backend'
 exec(compile(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True),module.__file__,'exec'),module.__dict__)
 return module
cases={'transfer':(SENDER,{'wallet':RECIPIENT,'amount_wei':'1'}),'deposit':(SENDER,{'amount_wei':'1'}),
 'withdraw':(SENDER,{'amount_wei':'1'}),'claim':(RECIPIENT,{'remittance_id':'1'}),'cancel':(SENDER,{'remittance_id':'1'}),
 'authorizeSender':(ADMIN,{'wallet':RECIPIENT}),'pause':(ADMIN,{})}
rows=[]
for label,module,prepare in [('before',legacy('backend/blockchain.py','previous_reader'),legacy('backend/preparation.py','previous_prepare').prepare),('after',after,current_prepare)]:
 world=World();world.values['paynow','remittanceCount']=11
 contracts={name:Web3().eth.contract(address=address,abi=BUILD['contracts'][name]['abi']) for name,address in ADDRESSES.items()}
 requests=[]
 def encode(value):
  if isinstance(value,bytes):return Web3.to_hex(value)
  if isinstance(value,list):return [encode(x) for x in value]
  if isinstance(value,dict):return {key:encode(x) for key,x in value.items()}
  return value
 def transport(provider,endpoint,data,**kwargs):
  payload=json.loads(data);requests.append(payload);time.sleep(.005)
  def answer(item):
   method,params=item['method'],item['params']
   if method=='eth_chainId':value='0xaa36a7'
   elif method=='eth_blockNumber':value=hex(world.head)
   elif method=='eth_getBlockByNumber':
    n=world.head if params[0]=='latest' else int(params[0],16);value={'hash':HASH(n),'number':hex(n)}
   elif method=='eth_getCode':value=world.codes[next(a for a in world.codes if a.lower()==params[0].lower())]
   elif method=='eth_getTransactionByHash':value=world.txs[params[0]]
   elif method=='eth_getTransactionReceipt':value=world.receipts[params[0]]
   elif method=='eth_estimateGas':value='0xc350'
   elif method=='eth_call':
    contract=next(c for c in contracts.values() if c.address.lower()==params[0]['to'].lower())
    name=next(n for n,c in contracts.items() if c.address==contract.address)
    function,args=contract.decode_function_input(params[0]['data']);fn=function.fn_name
    if function.abi.get('stateMutability') in ('view','pure'):
     value=world.call(None,name,fn,*args.values())
    else:value=1 if fn=='transfer' else ()
    types_=[collapse_if_tuple(x) for x in function.abi['outputs']]
    values=value if len(types_)>1 else (value,) if types_ else ()
    value=Web3.to_hex(Web3().codec.encode(types_,values))
   else:raise AssertionError(method)
   return {'jsonrpc':'2.0','id':item['id'],'result':encode(value)}
  return json.dumps([answer(item) for item in reversed(payload)] if isinstance(payload,list) else answer(payload)).encode()
 module.clear_verified_deployments()
 with patch('web3._utils.http_session_manager.HTTPSessionManager.make_post_request',new=transport):
  module.SepoliaReader(world.config) # Full static proof primes the unchanged 60-second context.
  for action,(owner,args) in cases.items():
   requests.clear();started=time.perf_counter()
   reader=module.SepoliaReader(world.config,read_mode='prepare') if label=='after' else module.SepoliaReader(world.config)
   result=prepare(reader,owner,action,args,lambda address:address)
   assert result['unsigned'] and result['transaction']['from']==owner
   messages=[item for payload in requests for item in (payload if isinstance(payload,list) else [payload])]
   rows.append({'implementation':label,'operation':action,'logical_rpc_messages':len(messages),'transport_round_trips':len(requests),'elapsed_ms':round((time.perf_counter()-started)*1000,2),
                'sequence':json.dumps([[x['method'] for x in payload] if isinstance(payload,list) else [payload['method']] for payload in requests])})
  requests.clear();started=time.perf_counter()
  reader=module.SepoliaReader(world.config,read_mode='balance') if label=='after' else module.SepoliaReader(world.config)
  assert reader.balances(SENDER)['authoritative']
  messages=[item for payload in requests for item in (payload if isinstance(payload,list) else [payload])]
  rows.append({'implementation':label,'operation':'balances','logical_rpc_messages':len(messages),'transport_round_trips':len(requests),'elapsed_ms':round((time.perf_counter()-started)*1000,2),
              'sequence':json.dumps([[x['method'] for x in payload] if isinstance(payload,list) else [payload['method']] for payload in requests])})
 world.close()
with (ROOT/'results/iteration9_last_latency.csv').open('w',newline='') as file:
 writer=csv.DictWriter(file,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
lines=['# Final latency transport characterization','',f'Baseline `{BASE}`. Real Web3 7.14 transport/middleware/ABI pipeline with a synthetic in-memory RPC and 5 ms delay per HTTP envelope; warmed static proof; no public-chain or hosted timing claim.',
 '| Action | Logical messages before → after | HTTP transports before → after | ms before → after |','|---|---:|---:|---:|']
for old,new in zip(rows[:8],rows[8:]):lines.append(f"| {old['operation']} | {old['logical_rpc_messages']} → {new['logical_rpc_messages']} | {old['transport_round_trips']} → {new['transport_round_trips']} | {old['elapsed_ms']} → {new['elapsed_ms']} |")
lines+=['','The CSV records every actual wire-method group, including middleware chain checks. Fresh latest header, chain identity, same-block dynamic validation, simulation/gas and final hash fence all remain. Cold proof is intentionally outside warm measurements.']
(ROOT/'results/iteration9_last_latency.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
