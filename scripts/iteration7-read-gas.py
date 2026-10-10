"""Supplement local gas with existing receipts only. Never sign/send a transaction."""
import concurrent.futures
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from web3 import Web3
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic

ROOT = Path(__file__).resolve().parent.parent
if len(sys.argv) != 2:
    raise SystemExit('Usage: python scripts/iteration7-read-gas.py PUBLIC_READ_ONLY_RPC_URL')
web3 = Web3(Web3.HTTPProvider(sys.argv[1], request_kwargs={'timeout': 8}, exception_retry_configuration=None))
manifest = json.loads((ROOT / 'deployment/sepolia.json').read_text())
assert web3.eth.chain_id == 11155111
head = web3.eth.block_number
previous = json.loads((ROOT / 'deployment/live-smoke-evidence.json').read_text())
candidates = [(tx['actions'][0], tx['transaction_hash'], 'Iteration 6A historical smoke')
              for tx in previous['transactions'] if len(tx['actions']) == 1]
candidates += [('deposit', '0xfdb959d34b7f4ba6e82d0030f067fb9f5e36c3c7c18ced763c8a3441b02e2d28', 'Iteration 6B hosted'),
               ('transfer', '0x2f2d2ba058d5ca56ad4d18fc1fdc2a2d2bb90fd2ced22dbd189b267a6bbc69ba', 'Iteration 6B hosted'),
               ('claim', '0x23fd98f2e04e8f7b47eae0117a25935c6b90b618a560f4de81de57614b02a73c', 'Iteration 6B hosted')]
abis = {}
for name, item in manifest['contracts'].items():
    abi = json.loads((ROOT / f'static/abi/{name}.json').read_text())
    abis[item['address'].lower()] = {Web3.to_hex(event_abi_to_log_topic(e)): e for e in abi if e['type'] == 'event'}
expected = {'authorizeSender':'RoleAuthorized', 'authorizeRecipient':'RoleAuthorized', 'revokeRole':'RoleRevoked',
            'pause':'SystemPaused', 'unpause':'SystemUnpaused', 'deposit':'FundsDeposited', 'withdraw':'FundsWithdrawn',
            'transfer':'RemittanceCreated', 'claim':'RemittanceClaimed', 'cancel':'RemittanceCancelled'}

def read(candidate):
    action, tx_hash, evidence = candidate
    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        tx = web3.eth.get_transaction(tx_hash)
        block = web3.eth.get_block(receipt['blockNumber'])
        assert receipt['status'] == 1 and receipt['blockHash'] == block['hash']
        assert Web3.to_hex(receipt['transactionHash']).lower() == tx_hash.lower()
        assert head - receipt['blockNumber'] + 1 >= 6
        decoded = []
        for log in receipt['logs']:
            events = abis.get(log['address'].lower(), {})
            abi = events.get(Web3.to_hex(log['topics'][0])) if log['topics'] else None
            if abi:
                assert log['blockHash'] == receipt['blockHash'] and not log.get('removed', False)
                event = get_event_data(web3.codec, abi, log)
                decoded.append({'event': event['event'], 'args': dict(event['args'])})
        assert any(e['event'] == expected[action] for e in decoded)
        if action.startswith('authorize'):
            role = 0 if action == 'authorizeSender' else 1
            assert any(e['event'] == 'RoleAuthorized' and e['args']['role'] == role for e in decoded)
        return {'action':action, 'transaction_hash':tx_hash, 'evidence':evidence, 'source':'existing_sepolia_receipt',
                'gas_used':receipt['gasUsed'], 'block_number':receipt['blockNumber'], 'block_hash':Web3.to_hex(receipt['blockHash']),
                'confirmations':head-receipt['blockNumber']+1, 'canonical':True,
                'outer_to':tx['to'], 'outer_value_wei':str(tx['value']),
                'deployment_events':decoded,
                'comparison_note':'Whole outer transaction gas; wallet wrapper/batch overhead may be included. Not function-isolated gas.'}
    except Exception as error:
        # Never persist endpoint/credential-bearing exception strings.
        return {'action':action, 'transaction_hash':tx_hash, 'source':'existing_sepolia_receipt',
                'available':False, 'error_type':type(error).__name__}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    records = list(executor.map(read, candidates))
result = {'captured_at_utc':datetime.now(timezone.utc).isoformat(), 'chain_id':11155111,
          'snapshot_head':head, 'deployment_id':manifest['deploymentId'], 'blockchain_writes':0,
          'provenance':'Fresh read-only receipt/canonical-block checks of existing 6A/6B hashes; no authentication or application database access.',
          'records':records}
(ROOT / 'results/iteration7_sepolia_gas.json').write_text(json.dumps(result, indent=2)+'\n')
print(f"Read-only Sepolia gas: {sum('gas_used' in r for r in records)}/{len(records)} receipts available; zero writes.")
