// Reproduce observed Remix source paths without changing accepted source contents/settings.
const fs=require('node:fs'),path=require('node:path'),solc=require('solc'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),base=JSON.parse(fs.readFileSync(path.join(root,'deployment/compiler-input.json')));
const input={...base,sources:Object.fromEntries(Object.entries(base.sources).map(([key,value])=>['contracts/'+key,value]))};
const output=JSON.parse(solc.compile(JSON.stringify(input)));
if((output.errors||[]).some(e=>e.severity==='error'))throw new Error(JSON.stringify(output.errors));
const contracts={};
for(const [source,name] of [['contracts/RoleRegistry.sol','RoleRegistry'],['contracts/deposit_money.sol','deposit_money'],['contracts/transfer_money.sol','paynow']]){
 const evidence=JSON.parse(fs.readFileSync(path.join(root,'deployment',name+'-sourcify-evidence.json')));
 if(evidence.runtimeMatch!=='exact_match'||evidence.creationMatch!=='exact_match'||evidence.compilation.compilerVersion!=='0.8.34+commit.80d5c536'||evidence.compilation.compilerSettings.evmVersion!=='shanghai'||evidence.compilation.compilerSettings.optimizer.runs!==200||evidence.compilation.compilerSettings.optimizer.enabled!==true)throw new Error('Source verification/compiler evidence mismatch');
 for(const [observed,value] of Object.entries(evidence.sources)){
  if(!input.sources[observed]||value.content!==input.sources[observed].content)throw new Error('Published source differs from accepted source');
 }
 const artifact=output.contracts['contracts/'+source][name];
 const accepted=JSON.parse(fs.readFileSync(path.join(root,'static/abi',name+'.json')));
 if(JSON.stringify(artifact.abi)!==JSON.stringify(accepted))throw new Error('ABI changed');
 contracts[name]={source:'contracts/'+source,abi:artifact.abi,creationBytecode:artifact.evm.bytecode.object,runtimeBytecode:artifact.evm.deployedBytecode.object,immutableReferences:artifact.evm.deployedBytecode.immutableReferences};
}
const build={compiler:solc.version(),optimizer:input.settings.optimizer,evmVersion:input.settings.evmVersion,sourcePathPrefix:'contracts/',sources:Object.fromEntries(Object.entries(base.sources).map(([key,value])=>[key,crypto.createHash('sha256').update(value.content).digest('hex')])),contracts};
fs.writeFileSync(path.join(root,'deployment/remix-compiler-input.json'),JSON.stringify(input,null,2)+'\n');
fs.writeFileSync(path.join(root,'deployment/remix-build.json'),JSON.stringify(build,null,2)+'\n');
console.log('Reproduced all 3 unchanged contracts at verified Remix virtual paths; original settings and ABIs preserved.');
