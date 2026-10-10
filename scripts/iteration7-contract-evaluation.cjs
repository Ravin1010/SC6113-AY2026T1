// Verification/gas only: deterministic in-memory chain, no external RPC or live keys.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ganache = require('ganache');
const { ethers } = require('ethers');
const { compile } = require('./compile-contracts.cjs');

(async () => {
  const { output, warnings } = compile();
  assert.equal(warnings.length, 0);
  const rpc = ganache.provider({ logging: { quiet: true },
    chain: { chainId: 31337, hardfork: 'shanghai' }, wallet: { deterministic: true, totalAccounts: 8 } });
  const cases = [], gas = []; let assertions = 0, rejections = 0;
  const eq = (a,b) => { assert.deepEqual(a,b); assertions++; };
  try {
    const provider = new ethers.BrowserProvider(rpc, undefined, { cacheTimeout: -1 });
    provider.pollingInterval = 10;
    const signers = await Promise.all(Array.from({length:8}, (_,i)=>provider.getSigner(i)));
    const [admin,sender,recipient,otherSender,otherRecipient,stranger] = signers;
    const [A,S,R,T,U,X] = await Promise.all(signers.map(s=>s.getAddress()));
    const artifact = name => Object.values(output.contracts).map(c=>c[name]).find(Boolean);
    const deploy = async (name,args=[]) => {
      const a=artifact(name); const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,admin).deploy(...args);
      await c.waitForDeployment(); return c;
    };
    const roles=await deploy('RoleRegistry'), funding=await deploy('deposit_money',[roles.target]);
    const remittance=await deploy('paynow',[roles.target,funding.target]);
    const contracts={RoleRegistry:roles,deposit_money:funding,paynow:remittance};
    const tx=async p=>(await p).wait();
    async function rejected(name, fn) {
      await assert.rejects(async()=>{const r=await fn();if(r?.wait)await r.wait();});
      rejections++;cases.push({name,outcome:'REJECTED_AS_EXPECTED'});
    }
    function events(receipt) {
      return receipt.logs.flatMap(log=>Object.entries(contracts).flatMap(([name,c])=>{
        if(log.address.toLowerCase()!==c.target.toLowerCase())return [];
        const parsed=c.interface.parseLog(log);return [{contract:name,event:parsed.name,args:parsed.args}];
      }));
    }
    async function measured(action, contract, scenario, valueTransfer, p, expected) {
      const receipt=await tx(p);eq(receipt.status,1);
      const decoded=events(receipt);
      eq(decoded.map(e=>e.event),expected);
      const last=decoded.at(-1).args, unit=ethers.parseEther('0.001');
      if(action==='authorizeSender'||action==='authorizeRecipient')
        eq([last.wallet,last.role,last.admin],[action==='authorizeSender'?S:R,action==='authorizeSender'?0n:1n,A]);
      else if(action==='revokeRole')eq([last.wallet,last.role,last.admin],[S,1n,A]);
      else if(action==='pause'||action==='unpause')eq(last.admin,A);
      else if(action==='deposit')eq([last.sender,last.amount],[S,unit*5n]);
      else if(action==='withdraw')eq([last.owner,last.amount],[S,unit]);
      else {
        const id=action==='cancel'?2n:1n, status=action==='transfer'?0n:action==='claim'?1n:2n;
        eq([last.remittanceId,last.sender,last.recipient,last.amount,last.status],[id,S,R,unit,status]);
        const coordinated=decoded[0].args;
        eq([coordinated.remittanceId,coordinated.sender,coordinated.amount],[id,S,unit]);
        if(action!=='cancel')eq(coordinated.recipient,R);
      }
      gas.push({action,contract,scenario,gas_used:Number(receipt.gasUsed),eth_value_transfer:valueTransfer,
        source:'deterministic_local_chain',chain_id:31337,transaction_hash:receipt.hash});
      cases.push({name:`${action}: success and event sequence`,outcome:'PASS'});return receipt;
    }
    // Same fresh deployment/settings for all ten representative measurements.
    await measured('authorizeSender','RoleRegistry','First grant to ordinary Sender',false,roles.authorizeSender(S),['RoleAuthorized']);
    await measured('authorizeRecipient','RoleRegistry','First grant to ordinary Recipient',false,roles.authorizeRecipient(R),['RoleAuthorized']);
    for(const signer of [sender,recipient,stranger]) {
      await rejected('non-Admin cannot authorize Sender',()=>roles.connect(signer).authorizeSender(X));
      await rejected('non-Admin cannot authorize Recipient',()=>roles.connect(signer).authorizeRecipient(X));
      await rejected('non-Admin cannot revoke',()=>roles.connect(signer).revokeRole(S,0));
      await rejected('non-Admin cannot pause',()=>roles.connect(signer).pause());
      await rejected('non-Admin cannot unpause',()=>roles.connect(signer).unpause());
    }
    await rejected('zero Sender wallet',()=>roles.authorizeSender(ethers.ZeroAddress));
    await rejected('zero Recipient wallet',()=>roles.authorizeRecipient(ethers.ZeroAddress));
    await rejected('duplicate Sender',()=>roles.authorizeSender(S));
    await rejected('duplicate Recipient',()=>roles.authorizeRecipient(R));
    await rejected('Admin enum not an ordinary role',()=>roles.revokeRole(A,2));
    await tx(roles.authorizeRecipient(S));
    await measured('revokeRole','RoleRegistry','Revoke Sender wallet Recipient permission; Sender remains',false,roles.revokeRole(S,1),['RoleRevoked']);
    eq(await roles.isSender(S),true);eq(await roles.isRecipient(S),false);eq(await roles.admin(),A);
    eq(roles.interface.fragments.some(f=>f.type==='function' && /transferAdmin|setAdmin/.test(f.name)),false);
    await rejected('revoke missing role',()=>roles.revokeRole(S,1));
    await rejected('zero revoke target',()=>roles.revokeRole(ethers.ZeroAddress,0));
    await rejected('wiring non-Admin',()=>funding.connect(sender).setRemittanceContract(remittance.target));
    await tx(funding.setRemittanceContract(remittance.target));
    await rejected('wiring permanently locked',()=>funding.setRemittanceContract(remittance.target));
    for(const fn of [()=>funding.reserveFunds(1,S,R,1),()=>funding.releaseFunds(1),()=>funding.unlockFunds(1)])
      await rejected('untrusted reservation operation',fn);
    const amount=ethers.parseEther('0.001');
    await measured('deposit','deposit_money','First deposit, 0.005 ETH, zero prior balance',true,funding.connect(sender).deposit({value:amount*5n}),['FundsDeposited']);
    await rejected('zero deposit',()=>funding.connect(sender).deposit());
    await rejected('unauthorized deposit',()=>funding.connect(stranger).deposit({value:1}));
    await rejected('plain ETH is not a deposit',()=>sender.sendTransaction({to:funding.target,value:1}));
    await rejected('zero withdrawal',()=>funding.connect(sender).withdraw(0));
    await rejected('withdraw above available',()=>funding.connect(sender).withdraw(amount*6n));
    await rejected('other wallet has no withdraw credit',()=>funding.connect(stranger).withdraw(1));
    await measured('withdraw','deposit_money','Partial withdrawal 0.001 ETH; remaining availability',true,funding.connect(sender).withdraw(amount),['FundsWithdrawn']);
    await rejected('unauthorized create',()=>remittance.connect(stranger).transfer(R,1));
    await rejected('zero recipient',()=>remittance.connect(sender).transfer(ethers.ZeroAddress,1));
    await rejected('self remittance',()=>remittance.connect(sender).transfer(S,1));
    await rejected('recipient permission required',()=>remittance.connect(sender).transfer(X,1));
    await rejected('zero create',()=>remittance.connect(sender).transfer(R,0));
    await rejected('create exceeds available',()=>remittance.connect(sender).transfer(R,amount*5n));
    eq(await remittance.remittanceCount(),0n);
    await measured('transfer','paynow','First remittance ID, 0.001 ETH, new reservation storage',false,remittance.connect(sender).transfer(R,amount),['FundsReserved','RemittanceCreated']);
    const first=await remittance.transaction(1);eq([first.sender,first.recipient,first.amount,first.status],[S,R,amount,0n]);
    const reservation=await funding.reservations(1);eq([reservation.sender,reservation.recipient,reservation.amount,reservation.active],[S,R,amount,true]);
    const created=events(await provider.getTransactionReceipt(gas.find(x=>x.action==='transfer').transaction_hash));
    for(const e of created)eq([e.args.remittanceId,e.args.sender,e.args.recipient,e.args.amount],[1n,S,R,amount]);
    eq(await funding.availableBalance(S),amount*3n);eq(await funding.reservedBalance(S),amount);
    await rejected('reserved funds cannot be withdrawn',()=>funding.connect(sender).withdraw(amount*3n+1n));
    await measured('pause','RoleRegistry','False to true',false,roles.pause(),['SystemPaused']);
    for(const fn of [()=>funding.connect(sender).deposit({value:1}),()=>funding.connect(sender).withdraw(1),
      ()=>remittance.connect(sender).transfer(R,1),()=>remittance.connect(recipient).claim(1),()=>remittance.connect(sender).cancel(1)])
      await rejected('full pause blocks financial action',fn);
    eq((await remittance.transaction(1)).status,0n);eq((await funding.reservations(1)).active,true);
    eq((await funding.connect(sender).deposit_view())[0],amount*3n);
    await tx(roles.authorizeSender(T));await tx(roles.authorizeRecipient(U));
    await tx(roles.revokeRole(U,1));await tx(roles.authorizeRecipient(U));
    await rejected('already paused',()=>roles.pause());
    await measured('unpause','RoleRegistry','True to false',false,roles.unpause(),['SystemUnpaused']);
    await rejected('already unpaused',()=>roles.unpause());
    await rejected('wrong claimant',()=>remittance.connect(sender).claim(1));
    await rejected('unrelated claimant',()=>remittance.connect(stranger).claim(1));
    await tx(roles.revokeRole(R,1));
    const beforeR=BigInt(await rpc.request({method:'eth_getBalance',params:[R,'latest']}));
    const claim=await measured('claim','paynow','Claim 0.001 ETH after Recipient revocation',true,remittance.connect(recipient).claim(1),['ReservedFundsReleased','RemittanceClaimed']);
    const afterR=BigInt(await rpc.request({method:'eth_getBalance',params:[R,'latest']}));
    eq(afterR+claim.fee-beforeR,amount);
    eq((await remittance.transaction(1)).status,1n);eq((await funding.reservations(1)).active,false);
    await rejected('double claim',()=>remittance.connect(recipient).claim(1));
    await rejected('cancel completed',()=>remittance.connect(sender).cancel(1));
    await tx(roles.authorizeRecipient(R));await tx(remittance.connect(sender).transfer(R,amount));
    await rejected('other authorized Sender cannot cancel',()=>remittance.connect(otherSender).cancel(2));
    await rejected('Recipient cannot cancel',()=>remittance.connect(recipient).cancel(2));
    await tx(roles.revokeRole(S,0));
    await rejected('revoked Sender cannot deposit',()=>funding.connect(sender).deposit({value:1}));
    await rejected('revoked Sender cannot create',()=>remittance.connect(sender).transfer(R,1));
    const available=await funding.availableBalance(S);
    await measured('cancel','paynow','Cancel pending 0.001 ETH after Sender revocation; available nonzero',false,remittance.connect(sender).cancel(2),['ReservedFundsUnlocked','RemittanceCancelled']);
    eq(await funding.availableBalance(S),available+amount);eq(await funding.reservedBalance(S),0n);
    eq((await remittance.transaction(2)).status,2n);eq((await funding.reservations(2)).active,false);
    await rejected('double cancel',()=>remittance.connect(sender).cancel(2));
    await rejected('claim cancelled',()=>remittance.connect(recipient).claim(2));
    await tx(funding.connect(sender).withdraw(1)); // Preserved withdrawal after revocation.
    await tx(roles.authorizeSender(S));
    for(const id of [0,999]) {
      await rejected('unknown claim',()=>remittance.connect(recipient).claim(id));
      await rejected('unknown cancel',()=>remittance.connect(sender).cancel(id));
    }
    // Seeded model-based multi-owner interleaving; assert all liabilities and records after every operation.
    const owners=[S,T], receivers=[R,U], ownerSigners=[sender,otherSender], receiverSigners=[recipient,otherRecipient];
    const model=new Map([[S,await funding.availableBalance(S)],[T,0n]]), records=new Map();
    let seed=6113, transitions=0;
    const rnd=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;};
    async function accounting() {
      let available=0n,reserved=0n;
      for(const owner of owners) {
        eq(await funding.availableBalance(owner),model.get(owner));available+=model.get(owner);
        const locked=[...records.values()].filter(r=>r.sender===owner&&r.status===0).reduce((s,r)=>s+r.amount,0n);
        eq(await funding.reservedBalance(owner),locked);reserved+=locked;
      }
      eq(await funding.totalAvailable(),available);eq(await funding.totalReserved(),reserved);
      eq(BigInt(await rpc.request({method:'eth_getBalance',params:[funding.target,'latest']})),available+reserved);
      for(const [id,r] of records) {
        const actual=await remittance.transaction(id),locked=await funding.reservations(id);
        eq([actual.sender,actual.recipient,actual.amount,Number(actual.status)],[r.sender,r.recipient,r.amount,r.status]);
        eq(locked.active,r.status===0);
      }
    }
    for(let i=0;i<48;i++) {
      const who=rnd()%2, op=rnd()%5, value=BigInt(1+rnd()%10000);
      if(op===0 || model.get(owners[who])===0n) {
        await tx(funding.connect(ownerSigners[who]).deposit({value}));model.set(owners[who],model.get(owners[who])+value);
      } else if(op===1) {
        const v=value<=model.get(owners[who])?value:model.get(owners[who]),to=rnd()%2;
        await tx(remittance.connect(ownerSigners[who]).transfer(receivers[to],v));
        const id=Number(await remittance.remittanceCount());records.set(id,{sender:owners[who],recipient:receivers[to],amount:v,status:0});
        model.set(owners[who],model.get(owners[who])-v);
      } else if(op===2) {
        const v=value<=model.get(owners[who])?value:model.get(owners[who]);
        await tx(funding.connect(ownerSigners[who]).withdraw(v));model.set(owners[who],model.get(owners[who])-v);
      } else {
        const pending=[...records].find(([,r])=>r.status===0);
        if(pending) {
          const [id,r]=pending;
          if(op===3) {await tx(remittance.connect(receiverSigners[receivers.indexOf(r.recipient)]).claim(id));r.status=1;}
          else {await tx(remittance.connect(ownerSigners[owners.indexOf(r.sender)]).cancel(id));r.status=2;model.set(r.sender,model.get(r.sender)+r.amount);}
        } else {await tx(funding.connect(ownerSigners[who]).deposit({value}));model.set(owners[who],model.get(owners[who])+value);}
      }
      transitions++;await accounting();
    }
    eq(gas.length,10);eq(new Set(gas.map(x=>x.action)).size,10);
    const order=['authorizeSender','authorizeRecipient','revokeRole','pause','unpause','deposit','withdraw','transfer','claim','cancel'];
    gas.sort((a,b)=>order.indexOf(a.action)-order.indexOf(b.action));
    fs.mkdirSync('results',{recursive:true});
    const fields=['action','contract','scenario','gas_used','eth_value_transfer','source','chain_id','transaction_hash'];
    const csv=v=>'"'+String(v).replaceAll('"','""')+'"';
    fs.writeFileSync('results/iteration7_gas.csv',fields.join(',')+'\n'+gas.map(r=>fields.map(f=>csv(r[f])).join(',')).join('\n')+'\n');
    fs.writeFileSync('results/iteration7_contract_evaluation.json',JSON.stringify({baseline:'8c99477be903ed3885249ad91be17b103f5ab4bc',compiler:require('solc').version(),ganache:require('ganache/package.json').version,node:process.version,evm:'shanghai',optimizer_runs:200,chain_id:31337,seed:6113,model_transitions:transitions,assertions,expected_rejections:rejections,scenario_checks:cases.length,external_rpc:false,sepolia_writes:0,cases,gas},null,2)+'\n');
    console.log(`PASS: ${cases.length} scenario checks, ${rejections} expected rejections, ${assertions} explicit assertions, ${transitions} seeded model transitions; ten gas measurements.`);
    console.table(gas.map(({action,gas_used})=>({action,gas_used})));
  } finally {await rpc.disconnect();}
})().catch(error=>{console.error(error);process.exitCode=1;});
