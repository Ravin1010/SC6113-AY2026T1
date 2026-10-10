const fs = require('node:fs');
const path = require('node:path');
const solc = require('solc');

const root = path.resolve(__dirname, '..');
const productionFiles = ['RoleRegistry.sol', 'deposit_money.sol', 'transfer_money.sol'];

function compile(extraSources = {}) {
  const sources = Object.fromEntries(productionFiles.map(file => [
    `contracts/${file}`, { content: fs.readFileSync(path.join(root, 'contracts', file), 'utf8') }
  ]));
  const input = {
    language: 'Solidity',
    sources: { ...sources, ...extraSources },
    settings: {
      optimizer: { enabled: true, runs: 200 },
      evmVersion: 'shanghai',
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object', 'evm.deployedBytecode.immutableReferences'] } }
    }
  };
  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  const diagnostics = output.errors || [];
  for (const item of diagnostics) process.stderr.write(item.formattedMessage);
  if (diagnostics.some(item => item.severity === 'error')) throw new Error('Solidity compilation failed');
  return { input, output, warnings: diagnostics.filter(item => item.severity === 'warning') };
}

if (require.main === module) {
  const { input, output, warnings } = compile();
  const destination = path.join(root, 'build', 'contracts');
  fs.mkdirSync(destination, { recursive: true });
  const names = [];
  for (const [source, contracts] of Object.entries(output.contracts)) {
    for (const [name, artifact] of Object.entries(contracts)) {
      if (!artifact.evm.bytecode.object) continue; // Read-only configuration interface.
      names.push(name);
      fs.writeFileSync(path.join(destination, `${name}.json`), JSON.stringify({
        contractName: name, source, compiler: solc.version(), settings: input.settings, ...artifact
      }, null, 2) + '\n');
    }
  }
  fs.writeFileSync(path.join(destination, 'compiler-input.json'), JSON.stringify(input, null, 2) + '\n');
  console.log(`Compiler: ${solc.version()}`);
  console.log(`Compiled ${names.length} deployable contracts: ${names.join(', ')}`);
  console.log(`Warnings: ${warnings.length}. EVM: shanghai; optimizer: 200 runs.`);
}

module.exports = { compile };
