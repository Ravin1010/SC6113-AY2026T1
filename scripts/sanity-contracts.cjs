// Focused Iteration 3 checks only: isolated in-memory EVM, no RPC/network deployment.
const assert = require('node:assert/strict');
const ganache = require('ganache');
const { ethers } = require('ethers');
const { compile } = require('./compile-contracts.cjs');

// Test-only receiver compiled in memory; not a fourth application contract.
const receiverSource = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;
contract SanityReceiver {
    bool public reject;
    bool public attempted;
    bool public nestedSucceeded;
    address private target;
    bytes private payload;
    function configure(bool reject_, address target_, bytes calldata payload_) external {
        reject = reject_; target = target_; payload = payload_;
        attempted = false; nestedSucceeded = false;
    }
    function execute(address target_, bytes calldata payload_) external payable {
        (bool success, ) = target_.call{value: msg.value}(payload_);
        require(success, "Fixture action failed");
    }
    receive() external payable {
        require(!reject, "Fixture rejects ETH");
        if (target != address(0)) {
            attempted = true;
            (nestedSucceeded, ) = target.call(payload);
        }
    }
}`;

async function main() {
  const { output, warnings } = compile({ 'sanity/Receiver.sol': { content: receiverSource } });
  assert.equal(warnings.length, 0);
  const production = Object.entries(output.contracts)
    .filter(([source]) => source.startsWith('contracts/'))
    .flatMap(([, contracts]) => Object.entries(contracts).filter(([, a]) => a.evm.bytecode.object));
  assert.deepEqual(production.map(([name]) => name).sort(), ['RoleRegistry', 'deposit_money', 'paynow']);

  const rpc = ganache.provider({
    logging: { quiet: true },
    chain: { hardfork: 'shanghai', chainId: 31337 },
    wallet: { deterministic: true, totalAccounts: 5 }
  });
  try {
    // Avoid caching an estimate from before a preceding setup/role transaction.
    const provider = new ethers.BrowserProvider(rpc, undefined, { cacheTimeout: -1 });
    provider.pollingInterval = 10;
    const signers = await Promise.all([0, 1, 2, 3, 4].map(i => provider.getSigner(i)));
    const [admin, sender, recipient, stranger] = signers;
    const [adminAddress, senderAddress, recipientAddress, strangerAddress] = await Promise.all(
      signers.slice(0, 4).map(s => s.getAddress())
    );
    const artifact = name => production.find(([n]) => n === name)[1];
    async function deploy(name, args = [], customArtifact) {
      const a = customArtifact || artifact(name);
      const c = await new ethers.ContractFactory(a.abi, a.evm.bytecode.object, admin).deploy(...args);
      await c.waitForDeployment();
      return c;
    }
    const tx = async promise => (await promise).wait();
    let checks = 0;
    async function rejects(action) {
      await assert.rejects(async () => {
        const result = await action();
        if (result && typeof result.wait === 'function') await result.wait();
      });
      checks++;
    }
    async function group(name, action) { await action(); console.log(`PASS ${name}`); }
    const roles = await deploy('RoleRegistry');
    const funding = await deploy('deposit_money', [roles.target]);
    const remittance = await deploy('paynow', [roles.target, funding.target]);
    const one = ethers.parseEther('1');
    const half = one / 2n;
    async function accounting() {
      const liabilities = await funding.totalAvailable() + await funding.totalReserved();
      const actual = BigInt(await rpc.request({ method: 'eth_getBalance', params: [funding.target, 'latest'] }));
      assert.equal(actual, liabilities); // No forced ETH in these sanity scenarios.
      assert.equal(await funding.reservedBalance(senderAddress), await funding.totalReserved());
    }

    await group('exact three application contracts, ten MVP actions, event responsibilities', async () => {
      const expected = {
        RoleRegistry: ['authorizeRecipient(address)', 'authorizeSender(address)', 'pause()', 'revokeRole(address,uint8)', 'unpause()'],
        deposit_money: ['deposit()', 'withdraw(uint256)'],
        paynow: ['cancel(uint256)', 'claim(uint256)', 'transfer(address,uint256)']
      };
      for (const [name, actions] of Object.entries(expected)) {
        const excluded = name === 'deposit_money'
          ? ['setRemittanceContract', 'reserveFunds', 'releaseFunds', 'unlockFunds'] : [];
        const writes = artifact(name).abi.filter(a => a.type === 'function'
          && !['view', 'pure'].includes(a.stateMutability) && !excluded.includes(a.name));
        const signatures = writes.map(a => `${a.name}(${a.inputs.map(i => i.type).join(',')})`).sort();
        assert.deepEqual(signatures, actions.slice().sort());
      }
      const events = {
        RoleRegistry: ['RoleAuthorized', 'RoleRevoked', 'SystemPaused', 'SystemUnpaused'],
        deposit_money: ['FundsDeposited', 'FundsWithdrawn', 'FundsReserved', 'ReservedFundsReleased', 'ReservedFundsUnlocked'],
        paynow: ['RemittanceCreated', 'RemittanceClaimed', 'RemittanceCancelled']
      };
      for (const [name, required] of Object.entries(events)) {
        const available = artifact(name).abi.filter(a => a.type === 'event').map(a => a.name);
        required.forEach(event => assert(available.includes(event)));
      }
    });

    await group('single Admin and validated permanent wiring', async () => {
      assert.equal(await roles.admin(), adminAddress);
      await rejects(() => roles.connect(stranger).authorizeSender(strangerAddress));
      await rejects(() => roles.authorizeSender(ethers.ZeroAddress));
      await rejects(() => roles.authorizeRecipient(ethers.ZeroAddress));
      await rejects(() => roles.revokeRole(adminAddress, 2));
      await rejects(() => funding.connect(stranger).setRemittanceContract(remittance.target));
      await rejects(() => funding.setRemittanceContract(ethers.ZeroAddress));
      await rejects(() => funding.setRemittanceContract(strangerAddress));
      const otherFunding = await deploy('deposit_money', [roles.target]);
      const wrongFunding = await deploy('paynow', [roles.target, otherFunding.target]);
      await rejects(() => funding.setRemittanceContract(wrongFunding.target));
      const otherRoles = await deploy('RoleRegistry');
      await rejects(() => deploy('paynow', [otherRoles.target, funding.target]));
      await tx(roles.authorizeSender(senderAddress));
      await tx(roles.authorizeRecipient(recipientAddress));
      await tx(roles.authorizeRecipient(senderAddress)); // Both ordinary permissions allowed.
      await rejects(() => roles.authorizeSender(senderAddress));
      await rejects(() => roles.authorizeRecipient(recipientAddress));
      await tx(funding.connect(sender).deposit({ value: one * 3n }));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, one));
      await tx(funding.setRemittanceContract(remittance.target));
      await rejects(() => funding.setRemittanceContract(remittance.target));
      assert.equal(await funding.remittanceContract(), remittance.target);
    });

    await group('funding identity, bounds and trusted-only coordination', async () => {
      await rejects(() => funding.connect(stranger).deposit({ value: one }));
      await rejects(() => funding.connect(sender).deposit());
      await rejects(() => funding.connect(sender).withdraw(0));
      await rejects(() => funding.connect(stranger).withdraw(1));
      await rejects(() => funding.connect(sender).reserveFunds(42, senderAddress, recipientAddress, one));
      await rejects(() => funding.releaseFunds(42));
      await rejects(() => funding.unlockFunds(42));
      assert.equal(await funding.availableBalance(senderAddress), one * 3n);
      await accounting();
    });

    await group('create is atomic; reservations cannot be withdrawn', async () => {
      await rejects(() => remittance.connect(sender).transfer(senderAddress, one));
      await rejects(() => remittance.connect(sender).transfer(ethers.ZeroAddress, one));
      await rejects(() => remittance.connect(sender).transfer(strangerAddress, one));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, 0));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, one * 4n));
      assert.equal(await remittance.remittanceCount(), 0n);
      assert.equal(await funding.totalReserved(), 0n);
      await tx(remittance.connect(sender).transfer(recipientAddress, one));
      await tx(remittance.connect(sender).transfer(recipientAddress, one));
      assert.equal(await remittance.remittanceCount(), 2n);
      assert.equal((await remittance.transaction(1)).sender, senderAddress);
      assert.equal((await funding.reservations(1)).recipient, recipientAddress);
      assert.equal(await funding.availableBalance(senderAddress), one);
      assert.equal(await funding.reservedBalance(senderAddress), one * 2n);
      await rejects(() => funding.connect(sender).withdraw(one + 1n));
      await accounting();
    });

    await group('full pause blocks all five actions; reads and role changes remain available', async () => {
      await rejects(() => roles.connect(stranger).pause());
      await tx(roles.pause());
      await rejects(() => roles.pause());
      await rejects(() => funding.connect(sender).deposit({ value: 1 }));
      await rejects(() => funding.connect(sender).withdraw(1));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, 1));
      await rejects(() => remittance.connect(recipient).claim(1));
      await rejects(() => remittance.connect(sender).cancel(2));
      await tx(roles.authorizeSender(strangerAddress));
      await tx(roles.authorizeRecipient(strangerAddress));
      await tx(roles.revokeRole(strangerAddress, 0));
      await tx(roles.revokeRole(strangerAddress, 1));
      assert.equal((await remittance.transaction(1)).status, 0n);
      assert.equal((await funding.reservations(1)).active, true);
      const balances = await funding.connect(sender).deposit_view();
      assert.equal(balances[0], one);
      assert.equal(balances[1], one * 2n);
      await rejects(() => roles.connect(stranger).unpause());
      await tx(roles.unpause());
      await rejects(() => roles.unpause());
      await accounting();
    });

    await group('revocation blocks new activity but preserves claim, cancel and withdrawal', async () => {
      await tx(roles.revokeRole(senderAddress, 0));
      await tx(roles.revokeRole(recipientAddress, 1));
      await rejects(() => funding.connect(sender).deposit({ value: 1 }));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, 1));
      await rejects(() => remittance.connect(stranger).claim(1));
      await rejects(() => remittance.connect(recipient).cancel(2));
      const recipientBefore = BigInt(await rpc.request({ method: 'eth_getBalance', params: [recipientAddress, 'latest'] }));
      const receipt = await tx(remittance.connect(recipient).claim(1));
      const recipientAfter = BigInt(await rpc.request({ method: 'eth_getBalance', params: [recipientAddress, 'latest'] }));
      assert.equal(recipientAfter + receipt.fee - recipientBefore, one);
      await tx(remittance.connect(sender).cancel(2));
      assert.equal((await remittance.transaction(1)).status, 1n);
      assert.equal((await remittance.transaction(2)).status, 2n);
      assert.equal(await funding.availableBalance(senderAddress), one * 2n);
      await tx(funding.connect(sender).withdraw(half));
      await accounting();
    });

    await group('terminal/unknown remittances cannot transition or pay twice', async () => {
      for (const id of [0, 1, 2, 999]) {
        await rejects(() => remittance.connect(recipient).claim(id));
        await rejects(() => remittance.connect(sender).cancel(id));
      }
      assert.equal(await funding.totalReserved(), 0n);
      assert.equal((await funding.reservations(1)).active, false);
      assert.equal((await funding.reservations(2)).active, false);
      await accounting();
    });

    const receiver = await deploy('SanityReceiver', [], output.contracts['sanity/Receiver.sol'].SanityReceiver);
    await group('failed recipient payout rolls back status and reservation', async () => {
      await tx(roles.authorizeSender(senderAddress));
      await rejects(() => remittance.connect(sender).transfer(recipientAddress, half));
      await tx(roles.authorizeRecipient(receiver.target));
      await tx(remittance.connect(sender).transfer(receiver.target, half));
      await tx(receiver.configure(true, ethers.ZeroAddress, '0x'));
      await rejects(() => receiver.execute(remittance.target, remittance.interface.encodeFunctionData('claim', [3])));
      assert.equal((await remittance.transaction(3)).status, 0n);
      assert.equal((await funding.reservations(3)).active, true);
      await accounting();
    });

    await group('recipient callback cannot reenter remittance claim', async () => {
      await tx(receiver.configure(false, remittance.target, remittance.interface.encodeFunctionData('claim', [3])));
      await tx(receiver.execute(remittance.target, remittance.interface.encodeFunctionData('claim', [3])));
      assert.equal(await receiver.attempted(), true);
      assert.equal(await receiver.nestedSucceeded(), false);
      assert.equal((await remittance.transaction(3)).status, 1n);
      await accounting();
    });

    await group('withdrawal rejection rolls back and callback cannot reenter funding', async () => {
      await tx(roles.authorizeSender(receiver.target));
      await tx(receiver.execute(funding.target, funding.interface.encodeFunctionData('deposit'), { value: half }));
      await tx(receiver.configure(true, ethers.ZeroAddress, '0x'));
      await rejects(() => receiver.execute(funding.target, funding.interface.encodeFunctionData('withdraw', [half])));
      assert.equal(await funding.availableBalance(receiver.target), half);
      await tx(receiver.configure(false, funding.target, funding.interface.encodeFunctionData('withdraw', [1])));
      await tx(receiver.execute(funding.target, funding.interface.encodeFunctionData('withdraw', [half])));
      assert.equal(await receiver.attempted(), true);
      assert.equal(await receiver.nestedSucceeded(), false);
      assert.equal(await funding.availableBalance(receiver.target), 0n);
      await accounting();
    });

    console.log(`10 focused sanity groups passed; ${checks} expected rejection checks passed.`);
  } finally { await rpc.disconnect(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
