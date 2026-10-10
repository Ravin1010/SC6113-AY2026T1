// Reproducible public artifacts only. Never deploys or configures a contract.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const solc = require('solc');
const {compile} = require('./compile-contracts.cjs');
const root = path.resolve(__dirname, '..');
const {input, output, warnings} = compile();
const destination = path.join(root, 'deployment');
const abiDestination = path.join(root, 'static', 'abi');
fs.mkdirSync(destination, {recursive:true}); fs.mkdirSync(abiDestination, {recursive:true});
fs.writeFileSync(path.join(destination, 'compiler-input.json'), JSON.stringify(input, null, 2)+'\n');
const contracts = {};
for (const [source, name] of [['contracts/RoleRegistry.sol','RoleRegistry'],['contracts/deposit_money.sol','deposit_money'],['contracts/transfer_money.sol','paynow']]) {
 const artifact = output.contracts[source][name];
 contracts[name] = {source, abi:artifact.abi, creationBytecode:artifact.evm.bytecode.object, runtimeBytecode:artifact.evm.deployedBytecode.object, immutableReferences:artifact.evm.deployedBytecode.immutableReferences};
 fs.writeFileSync(path.join(abiDestination, name+'.json'), JSON.stringify(artifact.abi,null,2)+'\n');
}
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
fs.writeFileSync(path.join(destination,'accepted-build.json'),JSON.stringify({compiler:solc.version(),optimizer:input.settings.optimizer,evmVersion:input.settings.evmVersion,sources:Object.fromEntries(Object.entries(input.sources).map(([key,value])=>[key,sha256(value.content)])),contracts},null,2)+'\n');
console.log(`Prepared 3 ABIs and immutable-aware verification build. ${solc.version()}; Shanghai; optimizer 200. Warnings: ${warnings.length}`);
