"""Verified, read-only Sepolia access. No signer, private keys or send calls."""
import hashlib
import json
import copy
import time
from collections import OrderedDict
from threading import RLock
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from flask import current_app, g
from eth_utils import is_address
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ('BLOCKCHAIN_RPC_URL', 'BLOCKCHAIN_CHAIN_ID', 'ROLE_REGISTRY_ADDRESS',
          'FUNDING_CONTRACT_ADDRESS', 'REMITTANCE_CONTRACT_ADDRESS', 'BLOCKCHAIN_DEPLOYMENT_ID')
HISTORICAL_ADDRESSES = {'0x1b6fc422422447d20af3d26aed82ab79e5520f48', '0x91c798dec35104fd1610d38a84ae89f2b94f0351'}
NAMES = ('RoleRegistry', 'deposit_money', 'paynow')
ZERO = '0x'+'0'*40


class VerifiedBatchProvider(HTTPProvider):
    """Pinned Web3 7.14 batch transport with exact request/response ID validation."""
    def make_batch_request(self, batch_requests):
        payload = self.encode_batch_rpc_request(batch_requests)
        expected = [item['id'] for item in json.loads(payload)]
        raw = self._request_session_manager.make_post_request(
            self.endpoint_uri, payload, **self.get_request_kwargs())
        responses = self.decode_rpc_response(raw)
        if (not isinstance(responses, list) or len(responses) != len(expected)
                or any(not isinstance(item, dict) or type(item.get('id')) is not int
                       or item.get('jsonrpc') != '2.0' or 'error' in item
                       or not isinstance(item.get('result'), str) for item in responses)):
            raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Pinned batch read failed; no partial financial state is returned.')
        by_id = {item['id']: item for item in responses}
        if len(by_id) != len(expected) or set(by_id) != set(expected):
            raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Batch response identifiers did not match the verified request.')
        return [by_id[identifier] for identifier in expected]

# Process-local verified STATIC evidence only. Never a reader or wallet snapshot.
_STATIC_TTL_SECONDS = 60
_STATIC_LIMIT = 4
_static_lock = RLock()
_static_contexts = OrderedDict()

def clear_verified_deployments():
    with _static_lock:
        _static_contexts.clear()


class BlockchainError(Exception):
    def __init__(self, code, message, status=503):
        self.code, self.message, self.status = code, message, status


def checksum(value):
    return Web3.to_checksum_address(value)


def configuration_status():
    config = current_app.config
    missing = [name for name in FIELDS if not config.get(name)]
    invalid = []
    if str(config.get('BLOCKCHAIN_CHAIN_ID')) != '11155111':
        invalid.append('BLOCKCHAIN_CHAIN_ID')
    try:
        parsed = urlsplit(config.get('BLOCKCHAIN_RPC_URL') or '')
        if config.get('BLOCKCHAIN_RPC_URL') and (parsed.scheme not in ('http', 'https') or not parsed.netloc):
            invalid.append('BLOCKCHAIN_RPC_URL')
    except (ValueError, TypeError, AttributeError):
        invalid.append('BLOCKCHAIN_RPC_URL')
    addresses = []
    for field in FIELDS[2:5]:
        value = config.get(field)
        if value:
            if not isinstance(value, str) or not is_address(value) or value.lower() in HISTORICAL_ADDRESSES or int(value, 16) == 0:
                invalid.append(field)
            else:
                addresses.append(value.lower())
    if len(addresses) != len(set(addresses)):
        invalid.append('CONTRACT_ADDRESSES_NOT_DISTINCT')
    return {'configured': not missing and not invalid, 'missing': missing, 'invalid': invalid,
            'deployment_verified': False, 'reader_available': False}


def matching_runtime(actual, artifact):
    """Only mask compiler-declared immutable spans; retain exact metadata comparison."""
    actual = bytearray(actual)
    expected = bytearray.fromhex(artifact['runtimeBytecode'])
    if len(actual) != len(expected) or not actual:
        return False
    for references in artifact['immutableReferences'].values():
        for reference in references:
            start, length = reference['start'], reference['length']
            if start < 0 or length <= 0 or start+length > len(actual):
                return False
            actual[start:start+length] = expected[start:start+length]
    return actual == expected


def hex_value(value):
    return Web3.to_hex(value)


def eth_amount(wei):
    return {'wei': str(wei), 'test_eth': format(Web3.from_wei(wei, 'ether'), 'f')}


class SepoliaReader:
    def __init__(self, config, *, receipt_only=False, read_mode='generic'):
        self.config = config
        self.receipt_only = receipt_only
        if read_mode not in ('generic','prepare','balance'):
            raise ValueError('Unsupported verified reader mode')
        self.read_mode = read_mode
        path = config.get('BLOCKCHAIN_MANIFEST_PATH')
        if not path:
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Deployment evidence is not configured. Manual deployment and verification are required.')
        try:
            manifest_bytes = Path(path).read_bytes()
            self.manifest = json.loads(manifest_bytes)
            prefix = self.manifest.get('compilerSourcePrefix', '')
            if prefix not in ('', 'contracts/'):
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Unsupported compiler source-path mapping.')
            artifact = 'remix-build.json' if prefix else 'accepted-build.json'
            build_bytes = (ROOT/'deployment'/artifact).read_bytes()
            # Content fingerprints detect changes even if size/mtime are preserved.
            digest = hashlib.sha256()
            digest.update(json.dumps([str(config.get(field, '')) for field in FIELDS] +
                                     [str(Path(path).resolve()), str(ROOT.resolve()), artifact]).encode())
            for data in [manifest_bytes, build_bytes] + [(ROOT/'contracts'/name).read_bytes() for name in
                     ('RoleRegistry.sol', 'deposit_money.sol', 'transfer_money.sol')]:
                digest.update(len(data).to_bytes(8, 'big'));digest.update(data)
            self._static_key = digest.hexdigest()
        except (OSError, ValueError):
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Deployment evidence/build could not be read.')
        self.web3 = Web3(VerifiedBatchProvider(config['BLOCKCHAIN_RPC_URL'], request_kwargs={'timeout': 12}))
        latest = self.web3.eth.get_block('latest')
        self.block = latest['number']
        if type(self.block) is not int or self.block < 0 or len(latest['hash']) != 32:
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Invalid latest block snapshot.')
        self.block_hash = hex_value(latest['hash'])
        # Single-flight full static verification; separate Web3/contracts/snapshot per request.
        with _static_lock:
            entry = _static_contexts.get(self._static_key)
            valid = entry is not None and time.monotonic() < entry['expires']
            if not valid:
                _static_contexts.pop(self._static_key, None)
            self.build = copy.deepcopy(entry['build']) if valid else json.loads(build_bytes)
            if self.build.get('sourcePathPrefix', '') != prefix:
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Compiler source-path evidence mismatch.')
            if set(self.build['sources']) != {'contracts/RoleRegistry.sol', 'contracts/deposit_money.sol', 'contracts/transfer_money.sol'}:
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Unexpected compiler source set.')
            self.contracts = {name: self.web3.eth.contract(address=checksum(config[field]), abi=self.build['contracts'][name]['abi'])
                              for name, field in zip(NAMES, FIELDS[2:5])}
            try:
                if valid:
                    self._verify_cached_context(entry)
                else:
                    self.verify()
                    if entry and self._verified_codes != entry['codes']:
                        raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Previously verified runtime identity changed on revalidation.')
                    # Unwired funding is not yet immutable: never cache that relationship.
                    if self.wired:
                        _static_contexts[self._static_key] = {
                            'expires': time.monotonic()+_STATIC_TTL_SECONDS,
                            'build': copy.deepcopy(self.build), 'codes': self._verified_codes.copy(),
                            'anchors': self._deployment_anchors.copy(),
                            'verification_block': self.block, 'verification_hash': self.block_hash,
                            'admin': self.admin, 'starts': self.starts.copy()}
                        while len(_static_contexts)>_STATIC_LIMIT:
                            _static_contexts.popitem(last=False)
            except Exception:
                _static_contexts.pop(self._static_key, None)
                raise

    def _verify_cached_context(self, entry):
        def require(condition, message):
            if not condition:
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', message)
        require(self.web3.eth.chain_id == 11155111, 'RPC is not Sepolia.')
        require(entry['verification_block'] <= self.block, 'RPC snapshot predates verified wiring.')
        # Runtime/deployment history/wiring are immutable evidence, revalidated at TTL.
        # Fresh chain identity, current snapshot, financial state and receipts stay live.
        self.admin, self.starts, self.wired = entry['admin'], entry['starts'].copy(), True
        if not self.receipt_only and self.read_mode=='generic':
            self.paused, self.count = self.calls([('RoleRegistry', 'paused', ()), ('paynow', 'remittanceCount', ())])
        if self.read_mode=='generic':
            self.ensure_snapshot()

    @contextmanager
    def snapshot_batch(self):
        """Pinned reads checked once on exit; no partially read batch may be returned."""
        self._batch_depth = getattr(self, '_batch_depth', 0)+1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if not self._batch_depth:
                self.ensure_snapshot()

    def call(self, name, function, *args):
        key = (name, function, args)
        cache = self.__dict__.setdefault('_calls', {})
        if key not in cache:
            cache[key] = getattr(self.contracts[name].functions, function)(*args).call(block_identifier=self.block)
        return cache[key]

    def calls(self, requests):
        """Independent reads only, same request/block. No global dynamic-state cache."""
        if not isinstance(getattr(self.web3, 'provider', None), VerifiedBatchProvider):
            return [self.call(name, function, *args) for name, function, args in requests]
        cache = self.__dict__.setdefault('_calls', {})
        missing = list(dict.fromkeys(item for item in requests if item not in cache))
        if missing:
            try:
                with self.web3.batch_requests() as batch:
                    for name, function, args in missing:
                        batch.add(getattr(self.contracts[name].functions, function)(*args).call(block_identifier=self.block))
                    values = batch.execute()
                if len(values) != len(missing):
                    raise ValueError('incomplete batch')
            except Exception:
                raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Pinned contract batch unavailable; no partial state is returned.') from None
            cache.update(zip(missing, values))
        return [cache[item] for item in requests]

    def simulate(self, transaction):
        """Retain both independent execution simulation and gas estimation."""
        if isinstance(getattr(self.web3, 'provider', None), VerifiedBatchProvider):
            with self.web3.batch_requests() as batch:
                batch.add(self.web3.eth.call(transaction, block_identifier=self.block))
                batch.add(self.web3.eth.estimate_gas(transaction, block_identifier=self.block))
                values = batch.execute()
            if len(values) != 2 or not isinstance(values[1], int) or values[1] <= 0:
                raise BlockchainError('TRANSACTION_SIMULATION_FAILED', 'Incomplete simulation or gas estimate.', 409)
            return values[1]
        self.web3.eth.call(transaction, block_identifier=self.block)
        return self.web3.eth.estimate_gas(transaction, block_identifier=self.block)

    def verify(self):
        def require(condition, message):
            if not condition:
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', message)
        manifest = self.manifest
        require(self.web3.eth.chain_id == 11155111 and manifest['chainId'] == 11155111, 'RPC/manifest is not Sepolia.')
        require(manifest['deploymentId'] == self.config['BLOCKCHAIN_DEPLOYMENT_ID'], 'Deployment identifier mismatch.')
        for source, expected_hash in self.build['sources'].items():
            require(hashlib.sha256((ROOT/source).read_bytes()).hexdigest() == expected_hash, 'Accepted source/build mismatch; regenerate exact artifacts.')
        require(self.build['compiler'].startswith('0.8.34+commit.80d5c536') and self.build['optimizer'] == {'enabled': True, 'runs': 200} and self.build['evmVersion'] == 'shanghai', 'Compiler settings mismatch.')
        self.starts = {}
        self._verified_codes, self._deployment_anchors = {}, {}
        for name, contract in self.contracts.items():
            evidence = manifest['contracts'][name]
            require(checksum(evidence['address']) == contract.address, 'Manifest address mismatch.')
            code = self.web3.eth.get_code(contract.address, block_identifier=self.block)
            artifact = self.build['contracts'][name]
            self._verified_codes[name] = bytes(code)
            require(matching_runtime(code, artifact), f'{name}: code/source/settings mismatch (immutable-aware comparison).')
            tx = self.web3.eth.get_transaction(evidence['transactionHash'])
            receipt = self.web3.eth.get_transaction_receipt(evidence['transactionHash'])
            args = [] if name == 'RoleRegistry' else [self.contracts['RoleRegistry'].address]
            if name == 'paynow':
                args.append(self.contracts['deposit_money'].address)
            constructor_types = [] if not args else ['address'] * len(args)
            expected_input = bytes.fromhex(artifact['creationBytecode']) + self.web3.codec.encode(constructor_types, args)
            require(bytes(tx['input']) == expected_input and tx['to'] is None, f'{name}: deployment input mismatch.')
            require(tx['from'].lower() == manifest['admin'].lower(), f'{name}: unexpected deployer.')
            require(receipt['status'] == 1 and checksum(receipt['contractAddress']) == contract.address, f'{name}: deployment receipt mismatch.')
            require(receipt['blockNumber'] == evidence['blockNumber'] and 0 <= receipt['blockNumber'] <= self.block, 'Deployment block mismatch.')
            require(hex_value(receipt['blockHash']) == hex_value(self.web3.eth.get_block(receipt['blockNumber'])['hash']), 'Deployment receipt is not canonical.')
            self.starts[name] = receipt['blockNumber']
            self._deployment_anchors[receipt['blockNumber']] = hex_value(receipt['blockHash'])
        self.admin = self.call('RoleRegistry', 'admin')
        require(self.admin != ZERO and self.admin.lower() == manifest['admin'].lower(), 'Admin/deployer mismatch.')
        registry = self.contracts['RoleRegistry'].address
        funding = self.contracts['deposit_money'].address
        transfer = self.contracts['paynow'].address
        require(self.call('deposit_money', 'roleRegistry') == registry, 'Funding registry mismatch.')
        require(self.call('paynow', 'roleRegistry') == registry, 'Remittance registry mismatch.')
        require(self.call('paynow', 'funding') == funding, 'Remittance funding mismatch.')
        trusted = self.call('deposit_money', 'remittanceContract')
        require(trusted in (ZERO, transfer), 'Funding is permanently wired to another address.')
        self.wired = trusted == transfer
        if not getattr(self, 'receipt_only', False) and getattr(self,'read_mode','generic')=='generic':
            self.paused = self.call('RoleRegistry', 'paused')
            self.count = self.call('paynow', 'remittanceCount')
        require(self.block_hash == hex_value(self.web3.eth.get_block(self.block)['hash']), 'Chain changed during verification; retry.')

    def ensure_snapshot(self):
        if getattr(self, '_batch_depth', 0):
            return
        if self.block_hash != hex_value(self.web3.eth.get_block(self.block)['hash']):
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Verified snapshot reorganized. Retry before taking any action.')

    def state(self):
        return {'configured': True, 'deployment_verified': True, 'reader_available': True,
                'wired': self.wired, 'paused': self.paused, 'chain_id': 11155111,
                'deployment_id': self.manifest['deploymentId'], 'admin': self.admin,
                'addresses': {name: contract.address for name, contract in self.contracts.items()},
                'block_number': self.block, 'block_hash': self.block_hash, 'remittance_count': str(self.count)}

    def user(self, wallet):
        address = checksum(wallet)
        sender, recipient = self.calls([('RoleRegistry', 'isSender', (address,)), ('RoleRegistry', 'isRecipient', (address,))])
        result = {'available': True, 'source': 'verified_contract', 'sender': sender,
                'recipient': recipient, 'admin': self.admin.lower() == wallet.lower(),
                'paused': self.paused}
        self.ensure_snapshot()
        return result

    def balances(self, wallet):
        requests=[('deposit_money', 'availableBalance', (checksum(wallet),)), ('deposit_money', 'reservedBalance', (checksum(wallet),))]
        if getattr(self,'read_mode','generic')=='balance':
            available,reserved,self.paused,self.count=self.calls(requests+[('RoleRegistry','paused',()),('paynow','remittanceCount',())])
        else:
            available,reserved=self.calls(requests)
        result = {'source': 'verified_contract', 'authoritative': True, 'block_number': self.block,
                'available': eth_amount(available), 'reserved': eth_amount(reserved), 'deployment': self.state()}
        self.ensure_snapshot()
        return result

    def remittance(self, identifier):
        if not 0 < identifier <= self.count:
            raise BlockchainError('REMITTANCE_NOT_FOUND', 'Remittance does not exist.', 404)
        transaction, reservation = self.calls([('paynow', 'transaction', (identifier,)), ('deposit_money', 'reservations', (identifier,))])
        sender, recipient, amount, status = transaction
        self.ensure_snapshot()
        return {'id': str(identifier), 'sender': sender, 'recipient': recipient, 'amount': eth_amount(amount),
                'status': ('PENDING', 'COMPLETED', 'CANCELLED')[status], 'reservation_active': reservation[3],
                'source': 'verified_contract', 'authoritative': True, 'block_number': self.block}

    def remittances(self, identifiers):
        """At most ten IDs / twenty eth_calls per transport batch."""
        if len(identifiers) > 10 or any(not 0 < identifier <= self.count for identifier in identifiers):
            raise BlockchainError('INVALID_REMITTANCE_ID', 'Invalid bounded remittance batch.', 400)
        if isinstance(getattr(self.web3, 'provider', None), VerifiedBatchProvider):
            self.calls([(name, function, (identifier,)) for identifier in identifiers
                        for name, function in [('paynow', 'transaction'), ('deposit_money', 'reservations')]])
        return (self.remittance(identifier) for identifier in identifiers)

    def receipt(self, tx_hash):
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            return {'transaction_hash': tx_hash, 'status': 'PENDING_OR_NOT_FOUND', 'source': 'verified_rpc'}
        if hex_value(receipt['transactionHash']).lower() != tx_hash.lower():
            raise BlockchainError('RECEIPT_LOG_MISMATCH', 'Receipt does not match the requested transaction.')
        transaction = self.web3.eth.get_transaction(tx_hash)
        deployed = {contract.address.lower(): (name, contract) for name, contract in self.contracts.items()}
        logs = []
        for log in receipt.get('logs', []):
            match = deployed.get(log['address'].lower())
            if not match or not log['topics']:
                continue
            name, contract = match
            events = {hex_value(event_abi_to_log_topic(abi)): abi for abi in contract.abi if abi['type'] == 'event'}
            abi = events.get(hex_value(log['topics'][0]))
            if (abi is None or log.get('removed') or log['blockNumber'] != receipt['blockNumber']
                    or log['blockHash'] != receipt['blockHash'] or log['transactionHash'] != receipt['transactionHash']):
                raise BlockchainError('RECEIPT_LOG_MISMATCH', 'Deployment event does not match this receipt.')
            event = get_event_data(self.web3.codec, abi, log)
            logs.append({'contract': name, 'event': event['event'], 'args': dict(event['args']), 'log_index': log['logIndex']})
        self.ensure_snapshot()
        return {'transaction_hash': hex_value(receipt['transactionHash']), 'status': 'CONFIRMED' if receipt['status'] else 'FAILED',
                'from': transaction['from'], 'to': transaction['to'], 'block_number': receipt['blockNumber'],
                'block_hash': hex_value(receipt['blockHash']), 'confirmations': max(0, self.block-receipt['blockNumber']+1),
                'canonical': hex_value(receipt['blockHash']) == hex_value(self.web3.eth.get_block(receipt['blockNumber'])['hash']),
                'source': 'verified_rpc', 'deployment_logs': logs}


def get_reader(*, receipt_only=False, read_mode='generic'):
    if 'blockchain_reader' in g:
        return g.blockchain_reader
    state = configuration_status()
    if not state['configured']:
        raise BlockchainError('BLOCKCHAIN_NOT_CONFIGURED', 'Verified evolved Sepolia deployment configuration is incomplete or invalid.')
    try:
        reader = SepoliaReader(current_app.config, receipt_only=receipt_only, read_mode=read_mode)
    except BlockchainError:
        raise
    except (KeyError, TypeError, ValueError, OSError):
        raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Deployment evidence or on-chain relationships could not be verified.')
    except Exception:
        raise BlockchainError('BLOCKCHAIN_READER_UNAVAILABLE', 'Sepolia RPC is unavailable or verification reads failed. Actions remain disabled.')
    g.blockchain_reader = reader
    return reader


def unavailable_state():
    try:
        reader = get_reader()
        return None, None, reader.state()
    except BlockchainError as error:
        return error.code, error.message, configuration_status()
