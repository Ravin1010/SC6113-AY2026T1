/* Verified reads and user-clicked MetaMask writes. No keys, signing library or ABI encoder. */
import {requestAPI, postJSON, friendlyError} from './api.js';
import {validationMessage} from './forms.js';
import {viewRead} from './cache.js';
const chain = '0xaa36a7';
const confirmationsRequired=1;
const adminActions = ['authorizeSender','authorizeRecipient','revokeRole','pause','unpause'];
const contractFor = {authorizeSender:'RoleRegistry',authorizeRecipient:'RoleRegistry',revokeRole:'RoleRegistry',pause:'RoleRegistry',unpause:'RoleRegistry',deposit:'deposit_money',withdraw:'deposit_money',transfer:'paynow',claim:'paynow',cancel:'paynow'};
const text = (id,value) => { const element=document.getElementById(id); if(element) element.textContent=value; };
export const toWei = value => {const [whole,decimal='']=value.trim().split('.');return (BigInt(whole)*10n**18n+BigInt(decimal.padEnd(18,'0'))).toString();};

export function setupLive(getSession, onError, refresh) {
  let state=null, revision=0, sending=false, pending=null, verifying=false;
  const terminalIds=new Set(); // Presentation only; backend prepare always rechecks.
  const pendingKey=(wallet,deployment)=>`sc6113-pending:${wallet.toLowerCase()}:${chain}:${deployment}`;
  function savePending(){try{sessionStorage.setItem(pendingKey(pending.wallet,pending.deployment),JSON.stringify(pending));}catch{}}
  function reportPending(message,retry=false){
    if(!pending||getSession()?.wallet.toLowerCase()!==pending.wallet)return;
    const button=buttons().find(button=>button.dataset.blockchainAction===pending.action);
    const output=button?.closest('form')?.querySelector('.form-result')||document.getElementById('transaction-status')||document.querySelector('.form-result');
    if(!output)return;
    output.textContent=`${message} ${pending.hash}`;
    const link=document.createElement('a');link.href=`https://sepolia.etherscan.io/tx/${pending.hash}`;link.target='_blank';link.rel='noopener';link.textContent='View Sepolia transaction';output.append(' ',link);
    if(retry){const check=document.createElement('button');check.type='button';check.dataset.verifyTransaction='';check.textContent='Check transaction';check.addEventListener('click',()=>verifyPending());output.append(' ',check);}
  }
  function completePending(){
    try{sessionStorage.removeItem(pendingKey(pending.wallet,pending.deployment));}catch{}
    pending=null;sending=false;
  }
  async function verifyPending(){
    if(verifying||!pending||getSession()?.wallet.toLowerCase()!==pending.wallet)return;
    verifying=true;sending=true;disable();const operation=pending,session=getSession();
    reportPending('Transaction submitted. Checking authoritative confirmation:');
    try{
      for(let count=0;count<20;count++){
        if(pending!==operation||getSession()!==session)return;
        if(count)await new Promise(resolve=>setTimeout(resolve,1000));
        let receipt;
        try{receipt=await requestAPI(`/api/transactions/${operation.hash}/receipt?index=deferred`);}
        catch(error){
          reportPending('Transaction submitted. Verification temporarily unavailable; retrying/checking authoritative state.',true);
          if(error.code==='AUTH_REQUIRED')onError(error);
          return;
        }
        if(pending!==operation||getSession()!==session)return;
        if(receipt.canonical===true&&receipt.confirmations>=confirmationsRequired){
          if(receipt.status==='FAILED'){
            reportPending('Transaction reverted:');completePending();await evaluate();return;
          }
          if(receipt.status==='CONFIRMED'){
            // Keep the lock until BOTH confirmation and the post-state refresh succeed.
            await refreshAffected(operation.action,operation.args,session);
            if(pending!==operation||getSession()!==session)return;
            if(!basic())throw new Error('Authoritative post-transaction state is temporarily unavailable.');
            if(operation.action==='transfer'){
              const events=(receipt.deployment_logs||[]).filter(log=>log.contract==='paynow'&&log.event==='RemittanceCreated'&&log.args?.sender?.toLowerCase()===operation.wallet&&log.args?.recipient?.toLowerCase()===operation.args.wallet.toLowerCase()&&String(log.args.amount)===String(operation.args.amount_wei));
              if(events.length!==1||!/^[1-9][0-9]*$/.test(String(events[0].args.remittanceId)))throw new Error('Verified creation event unavailable.');
              const id=String(events[0].args.remittanceId);
              const item=await requestAPI('/api/remittances/'+encodeURIComponent(id));
              if(item.source!=='verified_contract'||item.authoritative!==true||String(item.id)!==id||item.sender.toLowerCase()!==operation.wallet||item.recipient.toLowerCase()!==operation.args.wallet.toLowerCase()||String(item.amount.wei)!==String(operation.args.amount_wei)||!['PENDING','COMPLETED','CANCELLED'].includes(item.status)||item.reservation_active!==(item.status==='PENDING'))throw new Error('Created remittance post-state unavailable.');
              if(pending!==operation||getSession()!==session)return;
              reportPending(`Confirmed (${receipt.confirmations} ${receipt.confirmations===1?'confirmation':'confirmations'}). Transaction hash:`);
              const output=buttons().find(button=>button.dataset.blockchainAction==='transfer')?.closest('form')?.querySelector('.form-result');
              if(output){const heading=document.createElement('strong');heading.textContent=`Remittance created — ID #${id}`;output.prepend(heading,document.createElement('br'));}
            }else reportPending(`Confirmed (${receipt.confirmations} ${receipt.confirmations===1?'confirmation':'confirmations'}):`);
            completePending();await evaluate();
            // Presentation/index work must never gate confirmed authoritative outcome.
            void refresh({presentation:true,action:operation.action,hash:operation.hash}).catch(()=>{});return;
          }
        }
        reportPending(`Transaction submitted. Confirmation pending (${receipt.confirmations||0}/${confirmationsRequired}):`,true);
      }
      reportPending('Transaction submitted. Verification is still pending; check authoritative state again.',true);
    }catch(error){
      if(pending===operation){reportPending('Transaction submitted. Verification temporarily unavailable; retrying/checking authoritative state.',true);if(error.code==='AUTH_REQUIRED')onError(error);}
    }finally{verifying=false;}
  }
  const buttons=()=>Array.from(document.querySelectorAll('[data-blockchain-action]'));
  const disable=()=>{buttons().forEach(button=>button.disabled=true);const audit=document.getElementById('audit-refresh');if(audit)audit.disabled=true;};
  function invalidate(){terminalIds.clear();state=null;revision++;disable();text('audit-records','');text('available-balance','Unavailable');text('reserved-balance','Unavailable');text('live-remittances','Live remittance state unavailable.');}
  function basic(){const session=getSession();return Boolean(state && session && state.deployment.deployment_verified===true && state.deployment.wired===true && state.connection.chainId===chain && state.connection.address.toLowerCase()===session.wallet.toLowerCase());}
  async function check(button,ticket) {
    button.disabled=true;
    const action=button.dataset.blockchainAction, form=button.closest('form');
    if(!basic() || sending || !contractFor[action]) return;
    let enabled=adminActions.includes(action) ? state.roles.admin===true : !state.deployment.paused;
    if(!enabled) return;
    if(action==='pause') enabled=!state.deployment.paused;
    if(action==='unpause') enabled=state.deployment.paused;
    const input=form?.querySelector('[data-rule="amount"]');
    if(['deposit','withdraw','transfer'].includes(action)) {
      if(!input || validationMessage('amount',input.value)) return;
      const amount=BigInt(toWei(input.value));
      if(action!=='withdraw' && !state.roles.sender) return;
      if(action!=='deposit' && amount>BigInt(state.balances.available.wei)) return;
    }
    if(['authorizeSender','authorizeRecipient','revokeRole','transfer'].includes(action)) {
      const target=form?.querySelector('[name="wallet"]');
      if(!target || validationMessage(action==='transfer'?'recipient':'address',target.value,getSession().wallet)) return;
    }
    if(action==='claim'||action==='cancel') {
      const id=form?.querySelector('[data-rule="id"]');
      if(!id || validationMessage('id',id.value)) return;
      if(terminalIds.has(id.value.trim()))enabled=false;
    }
    if(ticket===revision && basic() && !sending){button.disabled=!enabled;button.title='Current on-chain permission and state are checked before MetaMask opens.';}
  }
  async function evaluate(){const ticket=++revision;disable();const audit=document.getElementById('audit-refresh');if(audit)audit.disabled=!(basic()&&state.roles.admin&&!sending);await Promise.all(buttons().map(async button=>{try{await check(button,ticket);}catch(error){if(ticket===revision && error.code==='AUTH_REQUIRED')onError(error);}}));}
  async function set(account,balances,connection,{list=true}={}){
    const deployment=balances?.deployment;
    if(!deployment?.deployment_verified || account.roles?.available!==true || account.roles.source!=='verified_contract' || balances.source!=='verified_contract' || balances.authoritative!==true){invalidate();return;}
    state={roles:account.roles,balances,connection,deployment};
    if(!pending || pending.wallet!==getSession()?.wallet.toLowerCase() || pending.deployment!==deployment.deployment_id){
      pending=null;
      try{const saved=JSON.parse(sessionStorage.getItem(pendingKey(getSession().wallet,deployment.deployment_id)));
        if(saved?.wallet===getSession().wallet.toLowerCase()&&saved.deployment===deployment.deployment_id&&/^0x[0-9a-f]{64}$/i.test(saved.hash)&&contractFor[saved.action])pending=saved;
      }catch{}
      sending=Boolean(pending);
    }
    if(pending)reportPending('Transaction submitted. Verification pending; check authoritative state.',!verifying);

    text('role-status', [account.roles.sender?'Sender':null,account.roles.recipient?'Recipient':null,account.roles.admin?'Admin / Auditor':null].filter(Boolean).join(', ') || 'No ordinary role authorized');
    document.querySelectorAll('[data-deployment-status]').forEach(el=>el.textContent=`Verified Sepolia deployment · ${deployment.wired?'Permanently wired':'Not wired — actions disabled'} · ${deployment.paused?'Paused':'Unpaused'}`);
    text('deployment-detail',`Deployment ${deployment.deployment_id} · verified at block ${deployment.block_number} · Admin ${deployment.admin}`);
    text('available-balance',`${balances.available.test_eth} test ETH (${balances.available.wei} wei)`);
    text('reserved-balance',`${balances.reserved.test_eth} test ETH (${balances.reserved.wei} wei)`);
    text('remittance-detail','Enter a remittance ID. Current status and participant permission will be checked when you click Claim or Cancel.');
    await evaluate();
    if(list)await refreshList();
  }
  async function refreshList(){
    if(state && document.getElementById('live-remittances')) {
      const ticket=revision;
      try{const data=await viewRead('/api/remittances?limit=20&offset=0',requestAPI);if(ticket!==revision||!state)return;
        if(data.source!=='verified_contract'||data.authoritative!==true)throw new Error('Remittance provenance unavailable.');
        const target=document.getElementById('live-remittances');target.replaceChildren();
        const summary=document.createElement('p');summary.textContent='Discovery: direct verified contract scan, newest first. History indexing is independent.';target.append(summary);
        if(!data.items.length){const p=document.createElement('p');p.textContent='No remittances for this wallet in the verified contract snapshot.';target.append(p);}
        for(const item of data.items){const p=document.createElement('p');p.className='identifier';p.textContent=`#${item.id} · ${item.status} · ${item.amount.test_eth} test ETH · ${item.sender} → ${item.recipient}`;target.append(p);}
      }catch(error){if(ticket===revision){text('live-remittances',`Live remittance list unavailable. ${friendlyError(error)}`);if(error.code==='AUTH_REQUIRED')onError(error);}}
    }
  }
  async function refreshAffected(action,args,expected){
    if(getSession()!==expected)return;
    // One confirmed transaction => one invalidation and one shared fresh load.
    // ID/role lookups are reevaluated against the new snapshot, including exits.
    await refresh({confirmed:true,action,args});
    if(getSession()===expected && ['claim','cancel'].includes(action)){
      const item=await requestAPI('/api/remittances/'+encodeURIComponent(args.remittance_id));
      if(item.source!=='verified_contract'||item.authoritative!==true||String(item.id)!==String(args.remittance_id)||item.status!==(action==='claim'?'COMPLETED':'CANCELLED')||item.reservation_active!==false||item[action==='claim'?'recipient':'sender'].toLowerCase()!==expected.wallet.toLowerCase())throw new Error('Authoritative remittance completion is not verified yet.');
      text('remittance-detail',`#${item.id}: ${item.status} · ${item.amount.test_eth} test ETH · ${item.sender} → ${item.recipient}`);
      terminalIds.add(String(item.id));
    }
    if(getSession()===expected && ['authorizeSender','authorizeRecipient','revokeRole'].includes(action)){
      const roles=await requestAPI('/api/users/roles/'+encodeURIComponent(args.wallet.toLowerCase()));
      const role=action==='authorizeSender'?'sender':action==='authorizeRecipient'?'recipient':args.role===0?'sender':'recipient';
      if(roles.available!==true||roles.source!=='verified_contract'||roles[role]!== (action!=='revokeRole'))throw new Error('Authoritative resulting role unavailable.');
    }
    if(getSession()===expected && ['pause','unpause'].includes(action) && state?.deployment.paused!==(action==='pause'))throw new Error('Authoritative resulting pause state unavailable.');
  }
  function argumentsFor(action,form){
    const args={};
    if(['authorizeSender','authorizeRecipient','revokeRole','transfer'].includes(action))args.wallet=form.querySelector('[name="wallet"]').value.trim();
    if(action==='revokeRole')args.role=document.getElementById('ordinary-role').value==='sender'?0:1;
    if(['deposit','withdraw','transfer'].includes(action))args.amount_wei=toWei(form.querySelector('[data-rule="amount"]').value);
    if(action==='claim'||action==='cancel')args.remittance_id=form.querySelector('[data-rule="id"]').value.trim();
    return args;
  }
  async function submit(button){
    if(button.disabled||sending||!basic())return;
    const action=button.dataset.blockchainAction,form=button.closest('form'),session=getSession(),snapshot=state,ticket=revision;
    const output=form?.querySelector('.form-result')||document.getElementById('transaction-status');
    let submittedHash=null;
    const args=argumentsFor(action,form);
    const report=value=>{if(output){output.textContent=value;if(submittedHash){const link=document.createElement('a');link.href=`https://sepolia.etherscan.io/tx/${submittedHash}`;link.target='_blank';link.rel='noopener';link.textContent='View Sepolia transaction';output.append(' ',link);}}};
    sending=true;disable();
    report('Checking current on-chain permissions and state; preparing unsigned transaction…');
    try{
      const prepared=await postJSON('/api/transactions/prepare',{action,arguments:args},session.csrf_token);
      const tx=prepared.transaction;
      if(ticket!==revision||getSession()!==session||!basic()||prepared.unsigned!==true||prepared.action!==action||prepared.deployment?.wired!==true||prepared.deployment?.deployment_verified!==true||prepared.deployment.deployment_id!==snapshot.deployment.deployment_id||tx?.chainId!==chain||tx.from.toLowerCase()!==session.wallet.toLowerCase()||tx.to.toLowerCase()!==snapshot.deployment.addresses[contractFor[action]].toLowerCase()||!/^0x[0-9a-f]+$/i.test(tx.data)||!/^0x[0-9a-f]+$/i.test(tx.value))throw new Error('Unsigned transaction verification failed. Nothing was submitted.');
      const accounts=await window.ethereum.request({method:'eth_accounts'}),currentChain=await window.ethereum.request({method:'eth_chainId'});
      if(ticket!==revision||!basic()||accounts[0]?.toLowerCase()!==session.wallet.toLowerCase()||currentChain!==chain)throw new Error('Wallet or network changed. Nothing was submitted.');
      report(`Review ${action} in MetaMask. Estimated gas: ${prepared.gas_estimate}.`);
      const hash=await window.ethereum.request({method:'eth_sendTransaction',params:[tx]});
      if(!/^0x[0-9a-f]{64}$/i.test(hash))throw new Error('Wallet returned an invalid transaction hash. Check MetaMask before retrying.');
      submittedHash=hash;
      pending={hash,action,args,wallet:session.wallet.toLowerCase(),deployment:snapshot.deployment.deployment_id};savePending();
      await verifyPending();
    }catch(error){
      if(submittedHash){reportPending('Transaction submitted. Verification temporarily unavailable; check authoritative state.',true);}
      else{report(error.code===4001?'MetaMask request cancelled. No transaction was submitted.':friendlyError(error));if(error.code==='AUTH_REQUIRED')onError(error);}
    }finally{
      // A submitted, unresolved transaction must never return to submit eligibility.
      if(!pending){sending=false;await evaluate();}
    }
  }

  buttons().forEach(button=>button.addEventListener('click',()=>submit(button)));
  document.querySelectorAll('form[data-preview]').forEach(form=>form.addEventListener('input',()=>{revision++;disable();void evaluate();}));
  document.getElementById('switch-sepolia')?.addEventListener('click',async()=>{try{await window.ethereum?.request({method:'wallet_switchEthereumChain',params:[{chainId:chain}]});if(state && state.connection.chainId!==chain)await refresh();}catch(error){onError(error);}});
  document.getElementById('audit-refresh')?.addEventListener('click',async()=>{
    if(!basic()||!state.roles.admin)return;
    const ticket=revision;
    try{const data=await requestAPI('/api/transactions/audit?limit=20&offset=0');if(ticket!==revision)return;
      if(data.source!=='sqlite_index'||data.authoritative!==false||data.live_blockchain_checked!==true)throw new Error('Audit provenance unavailable.');
      const output=document.getElementById('audit-records');output.replaceChildren();
      const label=document.createElement('p');label.textContent='Confirmed event index · not financial authority · live chain checked';output.append(label);
      for(const item of data.items){const row=document.createElement('p');row.textContent=`${item.tx_hash} · block ${item.block_number} · ${(item.events||[]).map(event=>event.event_type).join(', ')}`;output.append(row);}
      if(!data.items.length)text('audit-records','No indexed audit transactions available yet.');
    }catch(error){if(ticket===revision){text('audit-records',friendlyError(error));if(error.code==='AUTH_REQUIRED')onError(error);}}
  });
  return {set,invalidate,refreshList,isSending:()=>sending};
}
