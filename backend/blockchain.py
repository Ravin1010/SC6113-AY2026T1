"""Fail-closed deployment boundary. No RPC reads/writes in Iteration 4."""
from urllib.parse import urlsplit
from flask import current_app
from eth_utils import is_address

FIELDS = ('BLOCKCHAIN_RPC_URL', 'BLOCKCHAIN_CHAIN_ID', 'ROLE_REGISTRY_ADDRESS',
          'FUNDING_CONTRACT_ADDRESS', 'REMITTANCE_CONTRACT_ADDRESS', 'BLOCKCHAIN_DEPLOYMENT_ID')
HISTORICAL_ADDRESSES = {'0x1b6fc422422447d20af3d26aed82ab79e5520f48',
                        '0x91c798dec35104fd1610d38a84ae89f2b94f0351'}


def configuration_status():
    config = current_app.config
    missing = [name for name in FIELDS if not config.get(name)]
    invalid = []
    try:
        if isinstance(config['BLOCKCHAIN_CHAIN_ID'], bool) or int(config['BLOCKCHAIN_CHAIN_ID']) != 11155111:
            invalid.append('BLOCKCHAIN_CHAIN_ID')
    except (TypeError, ValueError):
        invalid.append('BLOCKCHAIN_CHAIN_ID')
    rpc = config.get('BLOCKCHAIN_RPC_URL')
    if rpc:
        try:
            parsed = urlsplit(rpc)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                invalid.append('BLOCKCHAIN_RPC_URL')
        except (ValueError, TypeError, AttributeError):
            invalid.append('BLOCKCHAIN_RPC_URL')
    addresses = []
    for field in FIELDS[2:5]:
        address = config.get(field)
        if address:
            if (not isinstance(address, str) or not is_address(address)
                    or address.lower() in HISTORICAL_ADDRESSES or int(address, 16) == 0):
                invalid.append(field)
            else:
                addresses.append(address.lower())
    if len(addresses) != len(set(addresses)):
        invalid.append('CONTRACT_ADDRESSES_NOT_DISTINCT')
    return {'configured': not missing and not invalid, 'missing': missing, 'invalid': invalid,
            'deployment_verified': config.get('BLOCKCHAIN_DEPLOYMENT_VERIFIED') is True,
            'reader_available': False}


def unavailable_state():
    state = configuration_status()
    if not state['configured']:
        return 'BLOCKCHAIN_NOT_CONFIGURED', 'Verified evolved Sepolia deployment configuration is incomplete or invalid.', state
    if not state['deployment_verified']:
        return 'BLOCKCHAIN_DEPLOYMENT_UNVERIFIED', 'Configured addresses have not been independently verified as the evolved deployment.', state
    return 'BLOCKCHAIN_READER_UNAVAILABLE', 'Live contract read integration is deferred; no blockchain state has been fetched.', state
