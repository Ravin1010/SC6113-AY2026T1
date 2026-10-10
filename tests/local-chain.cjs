/* Ephemeral local EVM only. Never contacts Sepolia or uses a user wallet. */
const ganache=require('ganache'),{ethers}=require('ethers'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawn}=require('node:child_process');
(async()=>{
 const server=ganache.server({logging:{quiet:true},chain:{chainId:11155111,hardfork:'shanghai'},wallet:{totalAccounts:3}}),temp=fs.mkdtempSync(path.join(os.tmpdir(),'sc6113-local-chain-'));
 try{
  await server.listen(0,'127.0.0.1');const url=`http://127.0.0.1:${server.address().port}`,provider=new ethers.JsonRpcProvider(url),admin=await provider.getSigner(0),sender=await provider.getSigner(1),recipient=await provider.getSigner(2);
  const build=JSON.parse(fs.readFileSync(path.join(__dirname,'../deployment/accepted-build.json'))),contracts={},evidence={};
  for(const name of ['RoleRegistry','deposit_money','paynow']){
   const artifact=build.contracts[name],args=name==='RoleRegistry'?[]:name==='deposit_money'?[await contracts.RoleRegistry.getAddress()]:[await contracts.RoleRegistry.getAddress(),await contracts.deposit_money.getAddress()];
   const contract=await new ethers.ContractFactory(artifact.abi,'0x'+artifact.creationBytecode,admin).deploy(...args);await contract.waitForDeployment();const receipt=await contract.deploymentTransaction().wait();contracts[name]=contract;
   evidence[name]={address:await contract.getAddress(),transactionHash:receipt.hash,blockNumber:receipt.blockNumber};
  }
  const manifest={chainId:11155111,deploymentId:'ephemeral-local-test',admin:await admin.getAddress(),contracts:evidence};fs.writeFileSync(path.join(temp,'manifest.json'),JSON.stringify(manifest));
  await (await contracts.deposit_money.setRemittanceContract(await contracts.paynow.getAddress())).wait();
  await (await contracts.RoleRegistry.authorizeSender(await sender.getAddress())).wait();await(await contracts.RoleRegistry.authorizeRecipient(await recipient.getAddress())).wait();
  await(await contracts.deposit_money.connect(sender).deposit({value:ethers.parseEther('0.003')})).wait();
  await(await contracts.paynow.connect(sender).transfer(await recipient.getAddress(),ethers.parseEther('0.001'))).wait();
  await(await contracts.paynow.connect(recipient).claim(1)).wait();
  await(await contracts.paynow.connect(sender).transfer(await recipient.getAddress(),ethers.parseEther('0.001'))).wait();
  await(await contracts.paynow.connect(sender).cancel(2)).wait();
  for(let n=0;n<6;n++)await provider.send('evm_mine',[]);
  const config={rpc:url,manifest:path.join(temp,'manifest.json'),database:path.join(temp,'test.db'),sender:await sender.getAddress(),recipient:await recipient.getAddress()};
  const child=spawn(process.env.PYTHON||'python',[path.join(__dirname,'verify_local_chain.py')],{cwd:path.join(__dirname,'..'),stdio:['pipe','inherit','inherit']});child.stdin.end(JSON.stringify(config));const code=await new Promise(resolve=>child.on('exit',resolve));if(code!==0)throw new Error('Local HTTP integration failed');
 }finally{await server.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1});
