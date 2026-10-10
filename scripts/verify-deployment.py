"""Read-only manual-checkpoint verification; never signs/broadcasts/wires."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import create_app
from backend.blockchain import get_reader, BlockchainError, ZERO, hex_value
from web3.exceptions import ContractLogicError, Web3RPCError

parser=argparse.ArgumentParser()
parser.add_argument('--phase', choices=('pre-wiring','post-wiring'), required=True)
parser.add_argument('--wiring-tx')
parser.add_argument('--manifest', help='Public deployment evidence file; RPC URL still comes from BLOCKCHAIN_RPC_URL')
arguments=parser.parse_args()
configuration = None
if arguments.manifest:
    try:
        manifest = json.loads(Path(arguments.manifest).read_text())
        configuration = {
            'BLOCKCHAIN_CHAIN_ID': manifest['chainId'],
            'BLOCKCHAIN_DEPLOYMENT_ID': manifest['deploymentId'],
            'BLOCKCHAIN_MANIFEST_PATH': arguments.manifest,
            'ROLE_REGISTRY_ADDRESS': manifest['contracts']['RoleRegistry']['address'],
            'FUNDING_CONTRACT_ADDRESS': manifest['contracts']['deposit_money']['address'],
            'REMITTANCE_CONTRACT_ADDRESS': manifest['contracts']['paynow']['address'],
        }
    except (OSError, KeyError, TypeError, ValueError):
        print(json.dumps({'error': {'code': 'INVALID_MANIFEST', 'message': 'Public deployment manifest is invalid.'}}))
        sys.exit(1)
app=create_app(configuration)
try:
    with app.test_request_context():
        reader=get_reader()
        if arguments.phase=='pre-wiring':
            if reader.wired or reader.paused or reader.count != 0:
                raise BlockchainError('PRE_WIRING_CHECK_FAILED','Expected unset trusted address, unpaused system and zero remittances.')
        else:
            if not reader.wired or not arguments.wiring_tx:
                raise BlockchainError('WIRING_CHECK_FAILED','Verified permanent wiring and its public transaction hash are required.')
            receipt=reader.receipt(arguments.wiring_tx)
            tx=reader.web3.eth.get_transaction(arguments.wiring_tx)
            funding=reader.contracts['deposit_money']
            expected=funding.encode_abi('setRemittanceContract',args=[reader.contracts['paynow'].address])
            wiring_events = [log for log in receipt['deployment_logs'] if log['contract'] == 'deposit_money' and log['event'] == 'RemittanceContractConfigured'
                             and log['args']['admin'].lower() == reader.admin.lower()
                             and log['args']['remittanceContract'].lower() == reader.contracts['paynow'].address.lower()]
            direct = receipt['to'] == funding.address and hex_value(tx['input']) == expected
            if receipt['status']!='CONFIRMED' or not receipt['canonical'] or receipt['from'].lower()!=reader.admin.lower() or len(wiring_events) != 1 or receipt['block_number'] != reader.manifest['wiring']['blockNumber'] or tx['value'] != 0:
                raise BlockchainError('WIRING_CHECK_FAILED','Wiring transaction evidence mismatch.')
            try:
                reader.web3.eth.call({'from':reader.admin,'to':funding.address,'data':expected},block_identifier=reader.block)
            except (ContractLogicError,Web3RPCError) as error:
                if 'Already configured' not in str(error):
                    raise BlockchainError('WIRING_SIMULATION_UNCLEAR','Repeat wiring reverted without the expected one-time configuration reason.')
            else:
                raise BlockchainError('WIRING_CHECK_FAILED','Repeat wiring simulation unexpectedly succeeded.')
        print(json.dumps({'phase':arguments.phase,'verified':reader.state(),'deployment_evidence':reader.manifest['contracts'],'wiring_receipt':None if arguments.phase=='pre-wiring' else receipt,'wiring_call_path':None if arguments.phase=='pre-wiring' else ('direct' if direct else 'wallet batch; verified funding event'),'repeat_wiring_simulation':'not attempted' if arguments.phase=='pre-wiring' else 'reverted: Already configured'},indent=2))
except BlockchainError as error:
    print(json.dumps({'error':{'code':error.code,'message':error.message}}))
    sys.exit(1)
