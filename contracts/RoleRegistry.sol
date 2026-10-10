// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;

/// @notice Single-admin Sender/Recipient authorization for the coursework MVP.
contract RoleRegistry {
    enum Role { Sender, Recipient }

    address public immutable admin;
    bool public paused;
    mapping(address => bool) public isSender;
    mapping(address => bool) public isRecipient;

    event RoleAuthorized(address indexed wallet, Role indexed role, address indexed admin);
    event RoleRevoked(address indexed wallet, Role indexed role, address indexed admin);
    event SystemPaused(address indexed admin);
    event SystemUnpaused(address indexed admin);

    constructor() { admin = msg.sender; }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Admin only");
        _;
    }

    function authorizeSender(address wallet) external onlyAdmin {
        require(wallet != address(0), "Zero wallet");
        require(!isSender[wallet], "Sender already authorized");
        isSender[wallet] = true;
        emit RoleAuthorized(wallet, Role.Sender, msg.sender);
    }

    function authorizeRecipient(address wallet) external onlyAdmin {
        require(wallet != address(0), "Zero wallet");
        require(!isRecipient[wallet], "Recipient already authorized");
        isRecipient[wallet] = true;
        emit RoleAuthorized(wallet, Role.Recipient, msg.sender);
    }

    // The enum contains ordinary roles only; Admin cannot be passed/revoked.
    function revokeRole(address wallet, Role role) external onlyAdmin {
        require(wallet != address(0), "Zero wallet");
        if (role == Role.Sender) {
            require(isSender[wallet], "Sender not authorized");
            isSender[wallet] = false;
        } else {
            require(isRecipient[wallet], "Recipient not authorized");
            isRecipient[wallet] = false;
        }
        emit RoleRevoked(wallet, role, msg.sender);
    }

    function pause() external onlyAdmin {
        require(!paused, "Already paused");
        paused = true;
        emit SystemPaused(msg.sender);
    }

    function unpause() external onlyAdmin {
        require(paused, "Not paused");
        paused = false;
        emit SystemUnpaused(msg.sender);
    }
}
