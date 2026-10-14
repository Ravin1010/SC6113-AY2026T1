"""Prepare unsigned calldata with Web3; never sign or broadcast a transaction."""
from .blockchain import BlockchainError, checksum

ACTIONS = {'authorizeSender': ('RoleRegistry', 'authorizeSender'), 'authorizeRecipient': ('RoleRegistry', 'authorizeRecipient'),
           'revokeRole': ('RoleRegistry', 'revokeRole'), 'pause': ('RoleRegistry', 'pause'), 'unpause': ('RoleRegistry', 'unpause'),
           'deposit': ('deposit_money', 'deposit'), 'withdraw': ('deposit_money', 'withdraw'),
           'transfer': ('paynow', 'transfer'), 'claim': ('paynow', 'claim'), 'cancel': ('paynow', 'cancel')}


def uint(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or not 1 <= len(value) <= 78 or not 0 < int(value) < 2**256:
        raise BlockchainError('INVALID_AMOUNT_OR_ID', 'Positive uint256 values must be supplied as decimal strings.', 400)
    return int(value)


def prepare(reader, owner, action, arguments, validate_wallet):
    with reader.snapshot_batch():
        if getattr(reader,'read_mode','generic')=='prepare':
            _validation_batch(reader,owner,action,arguments,validate_wallet)
        return _prepare(reader, owner, action, arguments, validate_wallet)


def _validation_batch(reader,owner,action,arguments,validate_wallet):
    """One independent same-block dynamic batch, followed by unchanged checks."""
    if not isinstance(action,str) or action not in ACTIONS or not isinstance(arguments,dict):
        raise BlockchainError('INVALID_ACTION','Select a supported action.',400)
    requests=[('RoleRegistry','paused',()),('paynow','remittanceCount',())]
    if action in ('deposit','transfer'):
        requests.append(('RoleRegistry','isSender',(checksum(owner),)))
    if action in ('withdraw','transfer'):
        requests.append(('deposit_money','availableBalance',(checksum(owner),)))
    if action in ('authorizeSender','authorizeRecipient','revokeRole','transfer') and 'wallet' in arguments:
        target=checksum(validate_wallet(arguments['wallet']))
        role='isSender' if action=='authorizeSender' else 'isRecipient'
        if action=='revokeRole':
            if type(arguments.get('role')) is not int or arguments['role'] not in (0,1):
                raise BlockchainError('INVALID_ROLE','Ordinary role must be Sender or Recipient.',400)
            role='isSender' if arguments['role']==0 else 'isRecipient'
        requests.append(('RoleRegistry',role,(target,)))
    if action in ('claim','cancel'):
        identifier=uint(arguments.get('remittance_id'))
        requests.extend([('paynow','transaction',(identifier,)),('deposit_money','reservations',(identifier,))])
    values=reader.calls(requests)
    reader.paused,reader.count=values[:2]


def _prepare(reader, owner, action, arguments, validate_wallet):
    def require(condition, message, code='ACTION_NOT_ALLOWED'):
        if not condition:
            raise BlockchainError(code, message, 409)
    if not isinstance(action, str) or action not in ACTIONS or not isinstance(arguments, dict):
        raise BlockchainError('INVALID_ACTION', 'Select one of the ten supported actions.', 400)
    require(reader.wired, 'Permanent contract wiring is not verified.', 'BLOCKCHAIN_NOT_WIRED')
    name, function = ACTIONS[action]
    # Immutable Admin governs admin actions; existing exit rights do not require roles.
    # Only new deposits/remittances require current Sender authorization.
    identity = {'admin': reader.admin.lower() == owner.lower()}
    if action == 'deposit':
        identity['sender'] = reader.call('RoleRegistry', 'isSender', checksum(owner))
    args, value = [], 0
    required = {'authorizeSender': {'wallet'}, 'authorizeRecipient': {'wallet'}, 'revokeRole': {'wallet', 'role'},
                'deposit': {'amount_wei'}, 'withdraw': {'amount_wei'}, 'transfer': {'wallet', 'amount_wei'},
                'claim': {'remittance_id'}, 'cancel': {'remittance_id'}}.get(action, set())
    if set(arguments) != required:
        raise BlockchainError('INVALID_INPUT', 'Unexpected or missing action arguments.', 400)
    if name == 'RoleRegistry':
        require(identity['admin'], 'Only the immutable on-chain Admin may initiate this action.')
        if 'wallet' in arguments:
            target = checksum(validate_wallet(arguments['wallet']))
            args.append(target)
            if action == 'revokeRole':
                role = arguments['role']
                if type(role) is not int or role not in (0, 1):
                    raise BlockchainError('INVALID_ROLE', 'Ordinary role must be 0 (Sender) or 1 (Recipient).', 400)
                args.append(role)
                require(reader.call(name, 'isSender' if role == 0 else 'isRecipient', target), 'The ordinary role is not currently authorized.')
            else:
                require(not reader.call(name, 'isSender' if action == 'authorizeSender' else 'isRecipient', target), 'This role is already authorized.')
        else:
            require(reader.paused if action == 'unpause' else not reader.paused, 'Pause state already matches the requested action.')
    else:
        require(not reader.paused, 'System is paused.', 'SYSTEM_PAUSED')
        if action == 'deposit':
            require(identity['sender'], 'Sender permission is required for new funding/remittances.')
        if action in ('deposit', 'withdraw', 'transfer'):
            amount = uint(arguments['amount_wei'])
            if action == 'transfer':
                target = checksum(validate_wallet(arguments['wallet']))
                require(target.lower() != owner.lower(), 'Sender and recipient must differ.')
                sender, available, recipient = reader.calls([('RoleRegistry', 'isSender', (checksum(owner),)),
                                                     ('deposit_money', 'availableBalance', (checksum(owner),)),
                                                     ('RoleRegistry', 'isRecipient', (target,))])
                require(sender, 'Sender permission is required for new remittances.')
                require(amount <= available, 'Insufficient available balance.')
                require(recipient, 'Recipient permission is required.')
            if action != 'deposit':
                if action != 'transfer':
                    require(amount <= reader.call('deposit_money', 'availableBalance', checksum(owner)), 'Insufficient available balance.')
            if action == 'deposit':
                value = amount
            elif action == 'withdraw':
                args.append(amount)
            else:
                args.extend((target, amount))
        else:
            identifier = uint(arguments['remittance_id'])
            remittance = reader.remittance(identifier)
            require(remittance['status'] == 'PENDING', 'Remittance is terminal.')
            participant = remittance['recipient' if action == 'claim' else 'sender']
            require(participant.lower() == owner.lower(), 'Only the recorded participant may initiate this action.')
            args.append(identifier)
    contract = reader.contracts[name]
    transaction = {'from': checksum(owner), 'to': contract.address, 'data': contract.encode_abi(function, args=args), 'value': hex(value)}
    try:
        gas = reader.simulate(transaction)
    except Exception:
        raise BlockchainError('TRANSACTION_SIMULATION_FAILED', 'Read-only simulation or gas estimation failed. No transaction was sent.', 409)
    reader.ensure_snapshot()
    transaction.update(chainId=hex(11155111), gas=hex((gas * 120 + 99)//100))
    return {'action': action, 'transaction': transaction, 'deployment': reader.state(), 'unsigned': True, 'gas_estimate': str(gas)}
