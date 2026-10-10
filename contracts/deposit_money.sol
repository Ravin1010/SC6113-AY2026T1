// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;

import "./RoleRegistry.sol";

// Configuration reads only; this interface is not another deployed contract.
interface IRemittanceConfiguration {
    function roleRegistry() external view returns (RoleRegistry);
    function funding() external view returns (address);
}

/// @notice Evolved classroom deposit_money: native test ETH funding and custody.
contract deposit_money {
    struct Reservation {
        address sender;
        address recipient;
        uint256 amount;
        bool active;
    }

    RoleRegistry public immutable roleRegistry;
    address public remittanceContract;
    mapping(address => uint256) public availableBalance;
    mapping(address => uint256) public reservedBalance;
    mapping(uint256 => Reservation) public reservations;
    uint256 public totalAvailable;
    uint256 public totalReserved;
    bool private entered;

    event RemittanceContractConfigured(address indexed remittanceContract, address indexed admin);
    event FundsDeposited(address indexed sender, uint256 amount);
    event FundsWithdrawn(address indexed owner, uint256 amount);
    event FundsReserved(uint256 indexed remittanceId, address indexed sender, address indexed recipient, uint256 amount);
    event ReservedFundsReleased(uint256 indexed remittanceId, address indexed sender, address indexed recipient, uint256 amount);
    event ReservedFundsUnlocked(uint256 indexed remittanceId, address indexed sender, uint256 amount);

    constructor(address registryAddress) {
        require(registryAddress != address(0) && registryAddress.code.length > 0, "Invalid registry");
        roleRegistry = RoleRegistry(registryAddress);
        require(roleRegistry.admin() != address(0), "Invalid admin");
    }

    modifier whenNotPaused() {
        require(!roleRegistry.paused(), "System paused");
        _;
    }

    modifier onlyRemittance() {
        require(msg.sender == remittanceContract && remittanceContract != address(0), "Trusted remittance only");
        _;
    }

    // Small local guard: protects every accounting entry point during ETH callbacks.
    modifier nonReentrant() {
        require(!entered, "Reentrant call");
        entered = true;
        _;
        entered = false;
    }

    /// @dev One-time deployment configuration, excluded from the 10 MVP actions.
    function setRemittanceContract(address transferAddress) external {
        require(msg.sender == roleRegistry.admin(), "Admin only");
        require(remittanceContract == address(0), "Already configured");
        require(transferAddress != address(0) && transferAddress.code.length > 0, "Invalid remittance contract");
        IRemittanceConfiguration candidate = IRemittanceConfiguration(transferAddress);
        require(address(candidate.roleRegistry()) == address(roleRegistry), "Registry mismatch");
        require(candidate.funding() == address(this), "Funding mismatch");
        remittanceContract = transferAddress;
        emit RemittanceContractConfigured(transferAddress, msg.sender);
    }

    /// @notice Identity and amount are actual msg.sender and msg.value.
    function deposit() external payable whenNotPaused nonReentrant {
        require(roleRegistry.isSender(msg.sender), "Sender not authorized");
        require(msg.value > 0, "Zero amount");
        availableBalance[msg.sender] += msg.value;
        totalAvailable += msg.value;
        emit FundsDeposited(msg.sender, msg.value);
    }

    /// @notice Existing ownership survives ordinary-role revocation.
    function withdraw(uint256 amount) external whenNotPaused nonReentrant {
        require(amount > 0, "Zero amount");
        require(availableBalance[msg.sender] >= amount, "Insufficient available balance");
        availableBalance[msg.sender] -= amount;
        totalAvailable -= amount;
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "ETH transfer failed");
        emit FundsWithdrawn(msg.sender, amount);
    }

    /// @dev Coordination action, not a separate user transaction type.
    function reserveFunds(uint256 id, address sender, address recipient, uint256 amount)
        external onlyRemittance whenNotPaused nonReentrant
    {
        require(id > 0, "Invalid remittance ID");
        require(sender != address(0) && recipient != address(0) && sender != recipient, "Invalid participants");
        require(amount > 0, "Zero amount");
        require(reservations[id].sender == address(0), "Reservation already exists");
        require(availableBalance[sender] >= amount, "Insufficient available balance");
        availableBalance[sender] -= amount;
        reservedBalance[sender] += amount;
        totalAvailable -= amount;
        totalReserved += amount;
        reservations[id] = Reservation(sender, recipient, amount, true);
        emit FundsReserved(id, sender, recipient, amount);
    }

    /// @dev Recipient is taken from the reservation, never a payout parameter.
    function releaseFunds(uint256 id) external onlyRemittance whenNotPaused nonReentrant {
        Reservation storage reservation = reservations[id];
        require(reservation.active, "Reservation not active");
        reservation.active = false;
        reservedBalance[reservation.sender] -= reservation.amount;
        totalReserved -= reservation.amount;
        (bool success, ) = payable(reservation.recipient).call{value: reservation.amount}("");
        require(success, "ETH transfer failed");
        emit ReservedFundsReleased(id, reservation.sender, reservation.recipient, reservation.amount);
    }

    function unlockFunds(uint256 id) external onlyRemittance whenNotPaused nonReentrant {
        Reservation storage reservation = reservations[id];
        require(reservation.active, "Reservation not active");
        reservation.active = false;
        reservedBalance[reservation.sender] -= reservation.amount;
        availableBalance[reservation.sender] += reservation.amount;
        totalReserved -= reservation.amount;
        totalAvailable += reservation.amount;
        emit ReservedFundsUnlocked(id, reservation.sender, reservation.amount);
    }

    /// @notice Retains the classroom read helper, now for the caller's balances.
    function deposit_view() external view returns (uint256 available, uint256 reserved) {
        return (availableBalance[msg.sender], reservedBalance[msg.sender]);
    }
}
