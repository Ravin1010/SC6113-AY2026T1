// Local generic CALL-wrapper characterization, NOT a MetaMask/EIP-7702 reproduction.
const assert=require('node:assert/strict');
const ganache=require('ganache');const {ethers}=require('ethers');
const {compile}=require('./compile-contracts.cjs');
(async()=>{
 const extra={'test/Wrapper.sol':{content:`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;
contract Wrapper { function execute(address target,bytes calldata data) external payable { (bool ok,)=target.call{value:msg.value}(data);require(ok,"wrapped call failed"); } }`}};
 const {output}=compile(extra);const rpc=ganache.provider({logging:{quiet:true},chain:{hardfork:'shanghai'},wallet:{deterministic:true}});
 try{
 const provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});provider.pollingInterval=10;
 const admin=await provider.getSigner(0),sender=await provider.getSigner(1),recipient=await provider.getSigner(2);
 const deploy=async(file,name,args=[])=>{const a=output.contracts[file][name];const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,admin).deploy(...args);await c.waitForDeployment();return c;};
 const roles=await deploy('contracts/RoleRegistry.sol','RoleRegistry');
 const funding=await deploy('contracts/deposit_money.sol','deposit_money',[roles.target]);
 const pay=await deploy('contracts/transfer_money.sol','paynow',[roles.target,funding.target]);
 const wrap=await deploy('test/Wrapper.sol','Wrapper');
 await(await funding.setRemittanceContract(pay.target)).wait();
 await(await roles.authorizeSender(await sender.getAddress())).wait();await(await roles.authorizeRecipient(await recipient.getAddress())).wait();
 await(await funding.connect(sender).deposit({value:100n})).wait();
 await(await pay.connect(sender).transfer(await recipient.getAddress(),10n)).wait();assert.equal(await pay.remittanceCount(),1n);
 await assert.rejects(wrap.connect(sender).execute.staticCall(pay.target,pay.interface.encodeFunctionData('transfer',[await recipient.getAddress(),10n])));
 assert.equal(await pay.remittanceCount(),1n);assert.equal(await funding.availableBalance(await sender.getAddress()),90n);
 console.log('PASS: 4 checks — ordinary create; generic wrapper rejected (unapproved msg.sender); count/accounting unchanged. Not proof of a same-address EIP-7702 failure.');
 }finally{await rpc.disconnect();}
})().catch(e=>{console.error(e);process.exitCode=1;});
