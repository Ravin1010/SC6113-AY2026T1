"""Short, resumable confirmed-log indexing; the database is never financial authority."""
import json
import time
from flask import current_app
from web3 import Web3, HTTPProvider
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic
from .blockchain import BlockchainError, hex_value
from .database import get_db


class BudgetExhausted(Exception):
    pass


class BudgetProvider(HTTPProvider):
    """No retry/backoff; every HTTP call fits the remaining indexing budget."""
    def __init__(self, endpoint, deadline):
        super().__init__(endpoint, exception_retry_configuration=None)
        self.deadline = deadline

    def get_request_kwargs(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise BudgetExhausted()
        values = super().get_request_kwargs()
        values['timeout'] = (min(.5, remaining / 2), min(1., remaining / 2))
        return values


def index_events(reader):
    deadline = time.monotonic() + min(8., max(.05, float(current_app.config.get('BLOCKCHAIN_INDEX_SECONDS', 6))))
    # A dedicated short-timeout transport leaves authoritative contract reads unchanged.
    rpc = (Web3(BudgetProvider(reader.web3.provider.endpoint_uri, deadline))
           if isinstance(getattr(reader.web3, 'provider', None), HTTPProvider) else reader.web3)
    db = get_db()
    deployment = reader.manifest['deploymentId']
    confirmations = max(1, int(current_app.config['BLOCKCHAIN_CONFIRMATIONS']))
    head = reader.block - confirmations + 1
    chunk = min(25, max(1, int(current_app.config['BLOCKCHAIN_LOG_CHUNK'])))
    max_blocks = max(1, int(current_app.config['BLOCKCHAIN_INDEX_MAX_BLOCKS']))
    blocks, receipts, transactions = {}, {}, {}
    reset = False
    checkpoints_verified = False
    states = db.execute('SELECT * FROM indexing_state WHERE chain_id=11155111 AND deployment_id=?', (deployment,)).fetchall()
    by_address = {row['contract_address']: row for row in states}

    def call(function, *args):
        if time.monotonic() >= deadline:
            raise BudgetExhausted()
        try:
            value = function(*args)
            if time.monotonic() >= deadline:
                raise BudgetExhausted()
            return value
        except BudgetExhausted:
            raise
        except Exception:
            raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'RPC indexing read failed. Retry or refresh to continue.') from None

    def block(number, fresh=False):
        if fresh or number not in blocks:
            value = call(rpc.eth.get_block, number)
            if not fresh:
                blocks[number] = value
            return value
        return blocks[number]

    def caught_up():
        return all((by_address.get(contract.address.lower())['last_block']
                    if contract.address.lower() in by_address else reader.starts[name] - 1) >= head
                   for name, contract in reader.contracts.items())

    try:
        # Deduplicate shared checkpoint heights, but always check against the current chain.
        reset = any(row['last_block'] > reader.block or row['last_block_hash'] != hex_value(block(row['last_block'])['hash']) for row in states)
        if reset:
            with db:
                db.execute('DELETE FROM indexed_events WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
                db.execute('DELETE FROM indexed_transactions WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
                db.execute('DELETE FROM indexing_state WHERE chain_id=11155111 AND deployment_id=?', (deployment,))
            by_address = {}
        checkpoints_verified = True
        for name, contract in reader.contracts.items():
            previous = by_address.get(contract.address.lower())
            start = reader.starts[name] if previous is None else previous['last_block'] + 1
            end = min(head, start + max_blocks - 1)
            abis = {hex_value(event_abi_to_log_topic(abi)): abi for abi in contract.abi if abi['type'] == 'event'}
            for lower in range(start, end + 1, chunk):
                upper = min(end, lower + chunk - 1)
                end_hash = hex_value(block(upper)['hash'])
                logs = call(rpc.eth.get_logs, {'address': contract.address, 'fromBlock': lower, 'toBlock': upper})
                rows = []
                for log in logs:
                    if log.get('removed') or log['address'].lower() != contract.address.lower() or not lower <= log['blockNumber'] <= upper:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'RPC returned inconsistent logs; chunk rolled back.')
                    if hex_value(log['blockHash']) != hex_value(block(log['blockNumber'])['hash']):
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Log block was reorganized; retry indexing.')
                    abi = abis.get(hex_value(log['topics'][0]))
                    if abi is None:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Unexpected event signature.')
                    event = get_event_data(reader.web3.codec, abi, log)
                    args = dict(event['args'])
                    tx_hash = hex_value(log['transactionHash'])
                    if tx_hash not in receipts:
                        receipts[tx_hash] = call(rpc.eth.get_transaction_receipt, tx_hash)
                    receipt = receipts[tx_hash]
                    if receipt['status'] != 1 or receipt['blockHash'] != log['blockHash']:
                        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Event receipt mismatch.')
                    if tx_hash not in transactions:
                        transactions[tx_hash] = call(rpc.eth.get_transaction, tx_hash)
                    tx = transactions[tx_hash]
                    sender = args.get('sender') or args.get('owner') or tx['from']
                    recipient = args.get('recipient') or args.get('wallet')
                    rows.append((log, event, args, tx_hash, sender, recipient, tx))
                # These deliberate fresh reads are reorg fences, not redundant lookups.
                if end_hash != hex_value(block(upper, fresh=True)['hash']) or reader.block_hash != hex_value(block(reader.block, fresh=True)['hash']):
                    raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'Chain changed during indexing; chunk rolled back.')
                if time.monotonic() >= deadline:
                    raise BudgetExhausted()
                # Only a completely validated chunk advances durable progress.
                with db:
                    for log, event, args, tx_hash, sender, recipient, tx in rows:
                        observed = int(time.time())
                        db.execute('INSERT INTO indexed_transactions VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,tx_hash) DO UPDATE SET recipient_wallet=COALESCE(excluded.recipient_wallet,recipient_wallet)',
                                   (11155111, deployment, tx_hash, sender.lower(), recipient.lower() if recipient else None, log['blockNumber'], hex_value(log['blockHash']), 1, observed))
                        payload = {'contract': name, 'address': contract.address, 'initiator': tx['from'], 'args': args}
                        db.execute('INSERT INTO indexed_events VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,tx_hash,log_index) DO NOTHING',
                                   (11155111, deployment, tx_hash, log['logIndex'], log['blockNumber'], hex_value(log['blockHash']), event['event'], str(args['remittanceId']) if 'remittanceId' in args else None, json.dumps(payload), observed))
                    db.execute('INSERT INTO indexing_state VALUES (?,?,?,?,?,?) ON CONFLICT(chain_id,deployment_id,contract_address) DO UPDATE SET last_block=excluded.last_block,last_block_hash=excluded.last_block_hash,updated_at=excluded.updated_at',
                               (11155111, deployment, contract.address.lower(), upper, end_hash, int(time.time())))
                by_address[contract.address.lower()] = {'last_block': upper}
    except BudgetExhausted:
        if not checkpoints_verified:
            raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Index checkpoint verification timed out; retry before reading indexed evidence.') from None
        # Completed chunks are already committed; retry starts at the next block.
        return {'confirmed_head': head, 'confirmations_required': confirmations, 'caught_up': False, 'reconciled_reset': reset, 'source': 'verified_rpc_logs'}
    except (KeyError, TypeError, IndexError, ValueError):
        raise BlockchainError('INDEX_RECONCILIATION_FAILED', 'RPC indexing evidence was malformed; incomplete chunk was not committed.') from None
    return {'confirmed_head': head, 'confirmations_required': confirmations, 'caught_up': caught_up(), 'reconciled_reset': reset, 'source': 'verified_rpc_logs'}
