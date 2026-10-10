"""Recover existing canonical Sepolia smoke evidence; never sign or broadcast."""
import json
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from backend.blockchain import get_reader, hex_value
from backend.database import get_db
from backend.indexer import index_events

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / 'deployment/sepolia.json').read_text())
with tempfile.TemporaryDirectory() as directory:
    app = create_app({
        'TESTING': True, 'SECRET_KEY': secrets.token_hex(32),
        'DATABASE': str(Path(directory) / 'smoke-evidence.db'),
        'BLOCKCHAIN_CHAIN_ID': manifest['chainId'],
        'BLOCKCHAIN_DEPLOYMENT_ID': manifest['deploymentId'],
        'BLOCKCHAIN_MANIFEST_PATH': str(root / 'deployment/sepolia.json'),
        'ROLE_REGISTRY_ADDRESS': manifest['contracts']['RoleRegistry']['address'],
        'FUNDING_CONTRACT_ADDRESS': manifest['contracts']['deposit_money']['address'],
        'REMITTANCE_CONTRACT_ADDRESS': manifest['contracts']['paynow']['address'],
    })
    with app.test_request_context():
        reader = get_reader()
        transactions = set()
        for name, contract in reader.contracts.items():
            for start in range(reader.starts[name], reader.block + 1, 500):
                logs = reader.web3.eth.get_logs({
                    'address': contract.address, 'fromBlock': start,
                    'toBlock': min(start + 499, reader.block),
                })
                transactions.update(hex_value(log['transactionHash']) for log in logs)
        records, wallets = [], set()
        fixed_actions = {
            'RoleRevoked': 'revokeRole', 'SystemPaused': 'pause',
            'SystemUnpaused': 'unpause', 'FundsDeposited': 'deposit',
            'FundsWithdrawn': 'withdraw', 'RemittanceCreated': 'transfer',
            'RemittanceClaimed': 'claim', 'RemittanceCancelled': 'cancel',
        }
        for tx_hash in transactions:
            receipt = reader.receipt(tx_hash)
            assert receipt['status'] == 'CONFIRMED' and receipt['canonical']
            assert receipt['confirmations'] >= 6
            actions = []
            for event in receipt['deployment_logs']:
                args = event['args']
                if event['event'] == 'RoleAuthorized':
                    actions.append('authorizeSender' if args['role'] == 0 else 'authorizeRecipient')
                elif event['event'] in fixed_actions:
                    actions.append(fixed_actions[event['event']])
                for field in ('sender', 'recipient', 'owner', 'wallet', 'admin'):
                    if field in args:
                        wallets.add(args[field])
            receipt['actions'] = actions
            receipt['timestamp'] = reader.web3.eth.get_block(receipt['block_number'])['timestamp']
            receipt['outer_sender_is_participant'] = any(
                str(event['args'].get(field, '')).lower() == receipt['from'].lower()
                for event in receipt['deployment_logs']
                for field in ('sender', 'owner', 'admin', 'recipient')
            )
            records.append(receipt)
        records.sort(key=lambda record: (record['block_number'], record['transaction_hash']))
        covered = sorted({action for record in records for action in record['actions']})
        expected = sorted(['authorizeSender', 'authorizeRecipient', 'revokeRole', 'pause',
                           'unpause', 'deposit', 'withdraw', 'transfer', 'claim', 'cancel'])
        assert covered == expected, covered
        remittances = [reader.remittance(identifier) for identifier in range(1, reader.count + 1)]
        assert {'COMPLETED', 'CANCELLED'} <= {record['status'] for record in remittances}
        snapshot = {wallet: {'roles': reader.user(wallet), 'balances': reader.balances(wallet)}
                    for wallet in sorted(wallets)}
        indexing = index_events(reader)
        db = get_db()
        before = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for table in ('indexed_transactions', 'indexed_events')}
        index_events(reader)
        after = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                 for table in before}
        assert before == after
        assert before['indexed_transactions'] == len(records)
        assert before['indexed_events'] == sum(len(record['deployment_logs']) for record in records)
        reader.ensure_snapshot()
        evidence = {
            'captured_at_utc': datetime.now(timezone.utc).isoformat(),
            'blockchain_writes': 0,
            'provenance': 'Existing user-signed smoke transactions recovered through verified-contract logs and canonical receipts; no new transactions.',
            'ui_evidence': 'User reported completed manual live smoke testing and accepted the correction package. This script independently verifies on-chain evidence, not browser interactions.',
            'deployment': reader.state(), 'transactions': records,
            'distinct_transaction_types': covered, 'remittances': remittances,
            'wallet_snapshot': snapshot,
            'indexing': {'result': indexing, 'record_counts': before,
                         'repeat_run_counts': after, 'idempotent': True},
        }
        output = root / 'deployment/live-smoke-evidence.json'
        output.write_text(json.dumps(evidence, indent=2) + '\n')
        print(f'{len(records)} canonical transactions, {len(covered)} action types, '
              f'{before["indexed_events"]} indexed events; repeat indexing unchanged. Zero blockchain writes.')
