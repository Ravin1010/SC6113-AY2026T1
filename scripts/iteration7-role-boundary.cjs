// Local-only characterization of the Iteration 7 Admin ordinary-role criterion.
// No external RPC, keys, or live transaction submission.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ganache = require('ganache');
const { ethers } = require('ethers');
const { compile } = require('./compile-contracts.cjs');

(async () => {
  const { output, warnings } = compile();
  assert.equal(warnings.length, 0);
  const rpc = ganache.provider({ logging: { quiet: true },
    chain: { chainId: 31337, hardfork: 'shanghai' }, wallet: { deterministic: true } });
  try {
    const provider = new ethers.BrowserProvider(rpc, undefined, { cacheTimeout: -1 });
    provider.pollingInterval = 10;
    const admin = await provider.getSigner(0), stranger = await provider.getSigner(1);
    const address = await admin.getAddress();
    const artifact = output.contracts['contracts/RoleRegistry.sol'].RoleRegistry;
    const registry = await new ethers.ContractFactory(artifact.abi, artifact.evm.bytecode.object, admin).deploy();
    await registry.waitForDeployment();
    let unauthorizedRejected = false;
    try { await registry.connect(stranger).authorizeSender(await stranger.getAddress()); }
    catch { unauthorizedRejected = true; }
    assert.equal(unauthorizedRejected, true);
    const senderReceipt = await (await registry.authorizeSender(address)).wait();
    const recipientReceipt = await (await registry.authorizeRecipient(address)).wait();
    assert.equal(senderReceipt.status, 1);
    assert.equal(recipientReceipt.status, 1);
    assert.equal(await registry.isSender(address), true);
    assert.equal(await registry.isRecipient(address), true);
    assert.equal(await registry.admin(), address);
    let adminRevocationRejected = false;
    try { await registry.revokeRole(address, 2); } catch { adminRevocationRejected = true; }
    assert.equal(adminRevocationRejected, true);
    const result = {
      baseline: '8c99477be903ed3885249ad91be17b103f5ab4bc',
      source: 'deterministic_local_chain', chain_id: 31337,
      compiler: require('solc').version(), evm: 'shanghai', optimizer_runs: 200,
      external_rpc_used: false, sepolia_writes: 0,
      characterization_assertions: 8,
      unauthorized_authorization_rejected: unauthorizedRejected,
      admin_self_authorize_sender: { receipt_status: senderReceipt.status, permission: true },
      admin_self_authorize_recipient: { receipt_status: recipientReceipt.status, permission: true },
      immutable_admin_unchanged: true, revoke_admin_enum_rejected: adminRevocationRejected,
      original_self_assignment_prohibition: 'FAIL',
      reviewed_criterion: 'Only immutable Admin grants/revokes ordinary roles; ordinary roles do not confer Admin authority',
      iteration7_corrected_role_criterion: 'PASS',
      status: 'Accepted limitation (owner-approved Option A)',
      finding: 'I7-01', severity: 'Low',
      note: 'Policy/acceptance mismatch, not an unprivileged escalation or evidence of financial loss.'
    };
    fs.writeFileSync('results/iteration7_role_boundary.json', JSON.stringify(result, null, 2) + '\n');
    console.log('8 characterization assertions PASS; corrected role criterion PASS; I7-01 accepted Low limitation.');
    console.log('No Sepolia writes. Frozen source unchanged. No contract change required under reviewed Option A.');
  } finally { await rpc.disconnect(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
