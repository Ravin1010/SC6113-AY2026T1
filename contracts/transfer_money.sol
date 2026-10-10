// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;

import "./RoleRegistry.sol";
import "./deposit_money.sol";

/// @notice Evolved classroom paynow: remittance lifecycle backed by reserved ETH.
contract paynow {
    enum Status { PENDING, COMPLETED, CANCELLED }
    struct Remittance {
        address sender;
        address recipient;
        uint256 amount;
        Status status;
    }

    RoleRegistry public immutable roleRegistry;
    deposit_money public immutable funding;
    uint256 public remittanceCount;
    mapping(uint256 => Remittance) private remittances;
    bool private entered;

    event RemittanceCreated(uint256 indexed remittanceId, address indexed sender, address indexed recipient, uint256 amount, Status status);
    event RemittanceClaimed(uint256 indexed remittanceId, address indexed sender, address indexed recipient, uint256 amount, Status status);
    event RemittanceCancelled(uint256 indexed remittanceId, address indexed sender, address indexed recipient, uint256 amount, Status status);

    constructor(address registryAddress, address fundingAddress) {
        require(registryAddress != address(0) && registryAddress.code.length > 0, "Invalid registry");
        require(fundingAddress != address(0) && fundingAddress.code.length > 0, "Invalid funding");
        roleRegistry = RoleRegistry(registryAddress);
        funding = deposit_money(fundingAddress);
        require(address(funding.roleRegistry()) == registryAddress, "Registry mismatch");
    }

    modifier whenNotPaused() {
        require(!roleRegistry.paused(), "System paused");
        _;
    }

    modifier nonReentrant() {
        require(!entered, "Reentrant call");
        entered = true;
        _;
        entered = false;
    }

    // Retains the classroom transfer purpose; sender is no longer user supplied.
    function transfer(address recipient, uint256 amount)
        external whenNotPaused nonReentrant returns (uint256 id)
    {
        require(roleRegistry.isSender(msg.sender), "Sender not authorized");
        require(recipient != address(0) && recipient != msg.sender, "Invalid recipient");
        require(roleRegistry.isRecipient(recipient), "Recipient not authorized");
        require(amount > 0, "Zero amount");
        require(funding.remittanceContract() == address(this), "Wiring incomplete");
        id = ++remittanceCount;
        remittances[id] = Remittance(msg.sender, recipient, amount, Status.PENDING);
        funding.reserveFunds(id, msg.sender, recipient, amount);
        emit RemittanceCreated(id, msg.sender, recipient, amount, Status.PENDING);
    }

    function claim(uint256 id) external whenNotPaused nonReentrant {
        Remittance storage remittance = pendingRemittance(id);
        require(msg.sender == remittance.recipient, "Recipient only");
        // Deliberately no current-role check: existing claim rights survive revocation.
        remittance.status = Status.COMPLETED;
        funding.releaseFunds(id);
        emit RemittanceClaimed(id, remittance.sender, remittance.recipient, remittance.amount, Status.COMPLETED);
    }

    function cancel(uint256 id) external whenNotPaused nonReentrant {
        Remittance storage remittance = pendingRemittance(id);
        require(msg.sender == remittance.sender, "Sender only");
        // Deliberately no current-role check: existing cancellation rights survive revocation.
        remittance.status = Status.CANCELLED;
        funding.unlockFunds(id);
        emit RemittanceCancelled(id, remittance.sender, remittance.recipient, remittance.amount, Status.CANCELLED);
    }

    function pendingRemittance(uint256 id) private view returns (Remittance storage remittance) {
        require(id > 0 && id <= remittanceCount, "Unknown remittance");
        remittance = remittances[id];
        require(remittance.status == Status.PENDING, "Remittance not pending");
    }

    /// @notice Retains the classroom read purpose, now addressed by remittance ID.
    function transaction(uint256 id) external view returns (Remittance memory) {
        require(id > 0 && id <= remittanceCount, "Unknown remittance");
        return remittances[id];
    }
}
