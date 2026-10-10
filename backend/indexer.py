"""Bounded confirmed-log index. SQLite stores evidence, never financial truth."""
import json
import time
from flask import current_app
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic
from .blockchain import BlockchainError, hex_value
from .database import get_db


def index_events(reader):
    db = get_db()
    deployment = reader.manifest['deploymentId']
    confirmations = max(1, int(current_app.config['BLOCKCHAIN_CONFIRMATIONS']))
    head = reader.block - confirmations + 1
    chunk = min(1000, max(1, int(current_app.config['BLOCKCHAIN_LOG_CHUNK'])))
    budget = max(1, int(current_app.config['BLOCKCHAIN_INDEX_MAX_BLOCKS']))
    states = db.execute('SELECT * FROM indexing_state WHERE chain_id=11155111 AND deployment_id=?', (deployment,)).fetchall()
    # If a checkpoint is orphaned, discard this deployment's cache and replay from deployment.
    reset = any(row['last_block'] > reader.block or row['last_block_hash'] != hex_value(reader.web3.eth.get_block(row['last_block'])['hash']) for row in states)
    completed = True
    with db:
        if reset:
            db.execute('DELETE FROM indexed_events WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
            db.execute('DELETE FROM indexed_transactions WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
            db.execute('DELETE FROM indexing_state WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
            states = []
        by_address = {row['contract_address']: row for row in states}
        for name, contract in reader.contracts.items():
            previous = by_address.get(contract.address.lower())
            start = reader.starts[name] if previous is None else previous['last_block'] + 1
            if start > head:
                continue
            end = min(head, start + budget - 1)
            completed = completed and end == head
            abis = {hex_value(event_abi_to_log_topic(abi)): abi for abi in contract.abi if abi['type'] == 'event'}
            for lower in range(start, end + 1, chunk):
                upper = min(end, lower + chunk - 1)
                end_hash = hex_value(reader.web3.eth.get_block(upper)['hash'])
                logs = reader.web3.eth.get_logs({'address': contract.address, 'fromBlock': lower, 'toBlock': upper})
                for log in logs:
                    if log.get('removed') or log['address'].lower() != contract.address.lower() or not lower <= log['blockNumber'] <= upper:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'RPC returned inconsistent logs; index update rolled back.')
                    if hex_value(log['blockHash']) != hex_value(reader.web3.eth.get_block(log['blockNumber'])['hash']):
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Log block was reorganized; retry indexing.')
                    abi = abis.get(hex_value(log['topics'][0]))
                    if abi is None:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Unexpected event signature.')
                    event = get_event_data(reader.web3.codec, abi, log)
                    args = dict(event['args'])
                    tx_hash = hex_value(log['transactionHash'])
                    receipt = reader.web3.eth.get_transaction_receipt(tx_hash)
                    if receipt['status'] != 1 or receipt['blockHash'] != log['blockHash']:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Event receipt mismatch.')
                    tx = reader.web3.eth.get_transaction(tx_hash)
                    sender = args.get('sender') or args.get('owner') or tx['from']
                    recipient = args.get('recipient') or args.get('wallet')
                    observed = int(time.time())
                    db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,tx_hash) DO UPDATE SET recipient_wallet=COALESCE(excluded.recipient_wallet,recipient_wallet)',
                               (11155111, deployment, tx_hash, sender.lower(), recipient.lower() if recipient else None, log['blockNumber'], hex_value(log['blockHash']), 1, observed))
                    payload = {'contract': name, 'address': contract.address, 'initiator': tx['from'], 'args': args}
                    db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,tx_hash,log_index) DO NOTHING',
                               (11155111, deployment, tx_hash, log['logIndex'], log['blockNumber'], hex_value(log['blockHash']), event['event'], str(args['remittanceId']) if 'remittanceId' in args else None, json.dumps(payload), observed))
                if end_hash != hex_value(reader.web3.eth.get_block(upper)['hash']):
                    raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Chain changed during indexing; update rolled back.')
            db.execute('INSERT INTO indexing_state VALUES (?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,contract_address) DO UPDATE SET last_block=excluded.last_block,last_block_hash=excluded.last_block_hash,updated_at=excluded.updated_at',
                       (11155111, deployment, contract.address.lower(), end, hex_value(reader.web3.eth.get_block(end)['hash']), int(time.time())))
        if reader.block_hash != hex_value(reader.web3.eth.get_block(reader.block)['hash']):
            raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Verification snapshot reorganized; update rolled back.')
    return {'confirmed_head': head, 'confirmations_required': confirmations, 'caught_up': completed, 'reconciled_reset': reset, 'source': 'verified_rpc_logs'}
