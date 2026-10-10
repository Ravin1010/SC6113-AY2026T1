"""Verified, read-only Sepolia access. No signer, private keys or send calls."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from flask import current_app, g
from eth_utils import is_address
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3._utils.events import get_event_data
from eth_utils import event_abi_to_log_topic

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ('BLOCKCHAIN_RPC_URL', 'BLOCKCHAIN_CHAIN_ID', 'ROLE_REGISTRY_ADDRESS',
          'FUNDING_CONTRACT_ADDRESS', 'REMITTANCE_CONTRACT_ADDRESS', 'BLOCKCHAIN_DEPLOYMENT_ID')
HISTORICAL_ADDRESSES = {'0x1b6fc422422447d20af3d26aed82ab79e5520f48', '0x91c798dec35104fd1610d38a84ae89f2b94f0351'}
NAMES = ('RoleRegistry', 'deposit_money', 'paynow')
ZERO = '0x'+'0'*40


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
    def __init__(self, config):
        self.config = config
        path = config.get('BLOCKCHAIN_MANIFEST_PATH')
        if not path:
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Deployment evidence is not configured. Manual deployment and verification are required.')
        try:
            self.manifest = json.loads(Path(path).read_text())
            prefix = self.manifest.get('compilerSourcePrefix', '')
            if prefix not in ('', 'contracts/'):
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Unsupported compiler source-path mapping.')
            artifact = 'remix-build.json' if prefix else 'accepted-build.json'
            self.build = json.loads((ROOT/'deployment'/artifact).read_text())
            if self.build.get('sourcePathPrefix', '') != prefix:
                raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Compiler source-path evidence mismatch.')
        except (OSError, ValueError):
            raise BlockchainError('BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Deployment evidence/build could not be read.')
        self.web3 = Web3(Web3.HTTPProvider(config['BLOCKCHAIN_RPC_URL'], request_kwargs={'timeout': 12}))
        self.block = self.web3.eth.block_number
        self.block_hash = hex_value(self.web3.eth.get_block(self.block)['hash'])
        self.contracts = {name: self.web3.eth.contract(address=checksum(config[field]), abi=self.build['contracts'][name]['abi'])
                          for name, field in zip(NAMES, FIELDS[2:5])}
        self.verify()

    def call(self, name, function, *args):
        return getattr(self.contracts[name].functions, function)(*args).call(block_identifier=self.block)

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
        for name, contract in self.contracts.items():
            evidence = manifest['contracts'][name]
            require(checksum(evidence['address']) == contract.address, 'Manifest address mismatch.')
            code = self.web3.eth.get_code(contract.address, block_identifier=self.block)
            artifact = self.build['contracts'][name]
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
        self.paused = self.call('RoleRegistry', 'paused')
        self.count = self.call('paynow', 'remittanceCount')
        require(self.block_hash == hex_value(self.web3.eth.get_block(self.block)['hash']), 'Chain changed during verification; retry.')

    def ensure_snapshot(self):
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
        result = {'available': True, 'source': 'verified_contract', 'sender': self.call('RoleRegistry', 'isSender', address),
                'recipient': self.call('RoleRegistry', 'isRecipient', address), 'admin': self.admin.lower() == wallet.lower(),
                'paused': self.paused}
        self.ensure_snapshot()
        return result

    def balances(self, wallet):
        result = {'source': 'verified_contract', 'authoritative': True, 'block_number': self.block,
                'available': eth_amount(self.call('deposit_money', 'availableBalance', checksum(wallet))),
                'reserved': eth_amount(self.call('deposit_money', 'reservedBalance', checksum(wallet))), 'deployment': self.state()}
        self.ensure_snapshot()
        return result

    def remittance(self, identifier):
        if not 0 < identifier <= self.count:
            raise BlockchainError('REMITTANCE_NOT_FOUND', 'Remittance does not exist.', 404)
        sender, recipient, amount, status = self.call('paynow', 'transaction', identifier)
        reservation = self.call('deposit_money', 'reservations', identifier)
        self.ensure_snapshot()
        return {'id': str(identifier), 'sender': sender, 'recipient': recipient, 'amount': eth_amount(amount),
                'status': ('PENDING', 'COMPLETED', 'CANCELLED')[status], 'reservation_active': reservation[3],
                'source': 'verified_contract', 'authoritative': True, 'block_number': self.block}

    def receipt(self, tx_hash):
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            return {'transaction_hash': tx_hash, 'status': 'PENDING_OR_NOT_FOUND', 'source': 'verified_rpc'}
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
            if abi is None or log['blockHash'] != receipt['blockHash'] or log['transactionHash'] != receipt['transactionHash']:
                raise BlockchainError('RECEIPT_LOG_MISMATCH', 'Deployment event does not match this receipt.')
            event = get_event_data(self.web3.codec, abi, log)
            logs.append({'contract': name, 'event': event['event'], 'args': dict(event['args']), 'log_index': log['logIndex']})
        return {'transaction_hash': hex_value(receipt['transactionHash']), 'status': 'CONFIRMED' if receipt['status'] else 'FAILED',
                'from': transaction['from'], 'to': transaction['to'], 'block_number': receipt['blockNumber'],
                'block_hash': hex_value(receipt['blockHash']), 'confirmations': max(0, self.block-receipt['blockNumber']+1),
                'canonical': hex_value(receipt['blockHash']) == hex_value(self.web3.eth.get_block(receipt['blockNumber'])['hash']),
                'source': 'verified_rpc', 'deployment_logs': logs}


def get_reader():
    if 'blockchain_reader' in g:
        return g.blockchain_reader
    state = configuration_status()
    if not state['configured']:
        raise BlockchainError('BLOCKCHAIN_NOT_CONFIGURED', 'Verified evolved Sepolia deployment configuration is incomplete or invalid.')
    try:
        reader = SepoliaReader(current_app.config)
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
