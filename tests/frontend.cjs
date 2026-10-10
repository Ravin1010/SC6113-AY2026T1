/* Focused real-browser checks, isolated Flask/SQLite and controlled EIP-1193 wallet. */
const assert = require('node:assert/strict');
const {test, before, after} = require('node:test');
const {spawn, spawnSync} = require('node:child_process');
const {mkdtempSync, rmSync, readFileSync, readdirSync} = require('node:fs');
const {tmpdir} = require('node:os');
const {resolve, join} = require('node:path');
const net = require('node:net');
const {chromium} = require('playwright');
const repo = resolve(__dirname, '..');
const python = process.env.PYTHON || 'python';
const temporary = mkdtempSync(join(tmpdir(), 'sc6113-ui-'));
const database = join(temporary, 'ui.db');
let server, browser, origin, account;
const browserErrors = [], methods = [];

function helper(value) {
  const result = spawnSync(python, [join(__dirname, 'ui_test_helper.py')], {cwd: repo, input: JSON.stringify(value), encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(predicate, message) {
  for (let count = 0; count < 100; count++) { if (await predicate()) return; await pause(50); }
  assert.fail(message || 'UI state did not settle');
}

async function pageWithWallet(mode = 'normal', width = 1280) {
  const context = await browser.newContext({viewport: {width, height: 900}});
  const page = await context.newPage();
  page.on('pageerror', error => browserErrors.push(error.message));
  await page.exposeFunction('__testSign', messageHex => helper({operation: 'sign', key: account.key, messageHex}));
  await page.exposeFunction('__testMethod', method => { methods.push(method); });
  if (mode !== 'absent') await page.addInitScript(({address, mode}) => {
    const handlers = {};
    window.__walletMode = mode;
    window.__walletAddress = address;
    window.__emitWallet = (event, value) => (handlers[event] || []).forEach(fn => fn(value));
    window.ethereum = {
      on(event, callback) { (handlers[event] ||= []).push(callback); },
      async request({method, params}) {
        await window.__testMethod(method);
        if (window.__walletMode === 'reject-connect' && method === 'eth_requestAccounts') throw {code: 4001};
        if (method === 'eth_requestAccounts' || method === 'eth_accounts') return [window.__walletAddress];
        if (method === 'eth_chainId') return window.__walletChain || '0xaa36a7';
        if (method === 'eth_sendTransaction' && window.__walletMode === 'live-test') {window.__sent= params[0]; return '0x'+'f'.repeat(64);}
        if (method === 'eth_sendTransaction' && window.__walletMode === 'reject-tx') throw {code:4001};
        if (method === 'personal_sign') {
          if (window.__walletMode === 'reject-sign') throw {code: 4001};
          if (window.__walletMode === 'change-wallet') { window.__walletAddress = '0x'+'d'.repeat(40); }
          return window.__testSign(params[0]);
        }
        throw new Error('Unexpected wallet method: '+method);
      }
    };
  }, {address: account.address, mode});
  return {page, context};
}
async function guest(page, route = '/main') {
  await page.goto(origin+route);
  await waitFor(() => page.locator('#login').isVisible(), 'Login should be visible');
  // Let initial /auth/session finish before initiating a controlled flow.
  await page.waitForLoadState('networkidle');
}
async function login(page) {
  await page.locator('#login').click();
  await waitFor(() => page.locator('#logout').evaluate(element => !element.hidden), 'Authenticated logout should be available');
  if (await page.locator('#history-status').count()) await waitFor(async () => !(await page.locator('#history-status').textContent()).includes('Loading'), 'History should settle');
  await waitFor(() => page.locator('#logout').isEnabled(), 'Login should complete');
}
async function assertDisabled(page) {
  assert.ok(await page.locator('[data-blockchain-action]').count());
  assert.equal(await page.locator('[data-blockchain-action]:not(:disabled)').count(), 0);
}

before(async () => {
  const socket = net.createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  origin = `http://127.0.0.1:${port}`;
  account = helper({operation: 'account'});
  server = spawn(python, [join(__dirname, 'ui_test_helper.py'), 'server'], {cwd: repo, env: {...process.env, UI_TEST_PORT: String(port), UI_TEST_DB: database, PYTHONPATH: repo}, stdio: ['ignore','ignore','pipe']});
  let errors = ''; server.stderr.on('data', chunk => { errors += chunk; });
  await waitFor(async () => { try { return (await fetch(origin+'/main')).ok; } catch { return false; } }, 'Flask server failed: '+errors);
  browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_EXECUTABLE_PATH ? {executablePath:process.env.CHROMIUM_EXECUTABLE_PATH} : {}), args: ['--no-sandbox']});
});
after(async () => {
  await browser?.close();
  server?.kill();
  rmSync(temporary, {recursive: true, force: true});
});

test('guest dashboard and MetaMask unavailable', async () => {
  const {page, context} = await pageWithWallet('absent');
  await guest(page);
  assert.equal(await page.locator('#session-content').isVisible(), false);
  await page.locator('#login').click();
  await waitFor(async () => (await page.locator('#notice').textContent()).includes('MetaMask is unavailable'));
  await assertDisabled(page);
  await context.close();
});

test('real nonce/signature/API session, wallet display and logout', async () => {
  const {page, context} = await pageWithWallet();
  await guest(page); await login(page);
  assert.equal(await page.locator('#wallet-address').textContent(), account.address);
  assert.match(await page.locator('#role-status').textContent(), /unavailable/);
  assert.match(await page.locator('[data-deployment-status]').textContent(), /not configured/);
  assert.match(await page.locator('#history-status').textContent(), /No indexed transactions available/);
  assert.match(await page.locator('#history-provenance').textContent(), /Not authoritative.*not checked/);
  await assertDisabled(page);
  await page.reload(); await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#wallet-address').textContent(), account.address);
  await page.locator('#logout').click();
  await waitFor(() => page.locator('#login').isVisible());
  assert.equal(await page.locator('#session-content').isVisible(), false);
  assert.equal((await context.request.get(origin+'/api/auth/session')).status(), 401);
  await context.close();
});

for (const mode of ['reject-connect','reject-sign','change-wallet']) test(`wallet error: ${mode}`, async () => {
  const {page, context} = await pageWithWallet(mode); await guest(page);
  await page.locator('#login').click();
  await waitFor(async () => (await page.locator('#notice').textContent()).match(/cancelled|selected wallet changed/));
  assert.equal(await page.locator('#session-content').isVisible(), false);
  await assertDisabled(page); await context.close();
});

for (const [code, message] of [['NONCE_EXPIRED','expired'],['NONCE_USED','already used'],['SIGNER_MISMATCH','does not match']]) test(`login backend error: ${code}`, async () => {
  const {page, context} = await pageWithWallet();
  await page.route('**/api/auth/verify', route => route.fulfill({status:code==='NONCE_EXPIRED'?410:code==='NONCE_USED'?409:401, json:{error:{code,message:'Controlled API error'}}}));
  await guest(page); await page.locator('#login').click();
  await waitFor(async () => (await page.locator('#notice').textContent()).includes(message));
  assert.equal(await page.locator('#logout').isVisible(), false); await context.close();
});

test('actual expired server session returns UI to login', async () => {
  const {page, context} = await pageWithWallet(); await guest(page); await login(page);
  helper({operation:'expire_session', database});
  await page.locator('#refresh').click();
  await waitFor(() => page.locator('#login').isVisible());
  assert.match(await page.locator('#notice').textContent(), /session ended/);
  await context.close();
});

test('account-change event clears UI and revokes existing session', async () => {
  const {page, context} = await pageWithWallet(); await guest(page); await login(page);
  await page.evaluate(() => { window.__walletAddress='0x'+'d'.repeat(40); window.__emitWallet('accountsChanged',[window.__walletAddress]); });
  await waitFor(() => page.locator('#login').isVisible());
  await waitFor(async () => (await context.request.get(origin+'/api/auth/session')).status()===401);
  assert.match(await page.locator('#notice').textContent(), /selected wallet changed/); await context.close();
});

for (const [code, text] of [['BLOCKCHAIN_NOT_CONFIGURED','not configured'],['BLOCKCHAIN_DEPLOYMENT_UNVERIFIED','verification is pending'],['BLOCKCHAIN_READER_UNAVAILABLE','reads are not available']]) test(`deployment state: ${code}`, async () => {
  const {page, context} = await pageWithWallet();
  await page.route('**/api/users/me/balances', route => route.fulfill({status:503,json:{error:{code,message:'Controlled deployment boundary'}}}));
  await guest(page); await login(page);
  await waitFor(async () => (await page.locator('[data-deployment-status]').textContent()).includes(text));
  await assertDisabled(page); await context.close();
});

test('cached history is scoped, labelled and rendered as text, with error recovery', async () => {
  const {page, context} = await pageWithWallet();
  await guest(page); await login(page);
  helper({operation:'seed_cache', database, address:account.address});
  // The isolated test server uses the deployment identifier only for this cache fixture.
  // UI response interception here exercises cache rendering without altering production configuration.
  await page.route('**/api/transactions?*', route => route.fulfill({json:{source:'sqlite_index', authoritative:false, live_blockchain_checked:false,indexing_available:false,items:[{tx_hash:'0x'+'a'.repeat(64), sender_wallet:account.address,recipient_wallet:'<img src=x onerror=alert(1)>',block_number:12,receipt_status:1,deployment_id:'isolated-ui-fixture',chain_id:11155111}]}}));
  await page.locator('#refresh').click();
  await waitFor(() => page.locator('.history-record').count());
  assert.equal(await page.locator('.history-record img').count(),0);
  assert.match(await page.locator('.history-record').textContent(), /<img src=x/);
  assert.match(await page.locator('#history-provenance').textContent(), /cached SQLite index/);
  await page.unroute('**/api/transactions?*');
  await page.route('**/api/transactions?*',route=>route.fulfill({status:503,json:{error:{code:'STORAGE_UNAVAILABLE',message:'Application storage is unavailable.'}}}));
  await page.locator('#refresh').click();
  await waitFor(async () => (await page.locator('#history-status').textContent()).includes('Indexed history unavailable'));
  assert.equal(await page.locator('.history-record').count(),0); await context.close();
});

test('form validation never submits a transaction', async () => {
  const {page, context} = await pageWithWallet(); await guest(page,'/transferMoney');
  await page.locator('#recipient-wallet').fill('bad'); await page.locator('#remittance-amount').fill('0');
  await page.locator('form[data-preview]').first().getByText('Check inputs').click();
  assert.match(await page.locator('#create-result').textContent(),/nonzero Ethereum address/);
  await page.locator('#recipient-wallet').fill('0x'+'b'.repeat(40));
  await page.locator('form[data-preview]').first().getByText('Check inputs').click();
  assert.match(await page.locator('#create-result').textContent(),/positive/);
  await page.locator('#remittance-amount').fill('0.000000000000000001');
  await page.locator('form[data-preview]').first().getByText('Check inputs').click();
  assert.match(await page.locator('#create-result').textContent(),/No transaction was submitted/);
  await page.locator('#remittance-id').fill('1.5');
  await page.locator('form[data-preview]').last().getByText('Check inputs').click();
  assert.match(await page.locator('#manage-result').textContent(),/whole-number/);
  await page.locator('#remittance-id').fill('1');
  await page.locator('form[data-preview]').last().getByText('Check inputs').click();
  assert.match(await page.locator('#manage-result').textContent(),/No transaction was submitted/);
  await assertDisabled(page);
  await page.goto(origin+'/depositMoney'); await page.waitForLoadState('networkidle');
  await page.locator('#deposit-amount').fill('1e2');
  await page.locator('form[data-preview]').first().getByText('Check inputs').click();
  assert.match(await page.locator('#deposit-result').textContent(),/no exponent/);
  await assertDisabled(page); await context.close();
});

for (const width of [360,768,1280]) test(`responsive pages, controls, navigation and long identifiers at ${width}px`, async () => {
  const {page, context} = await pageWithWallet('normal',width); await guest(page); await login(page);
  const paths = ['/main','/depositMoney','/transferMoney','/','/viewUser'];
  for (const path of paths) {
    await page.goto(origin+path); await page.waitForLoadState('networkidle');
    assert.equal(await page.locator('meta[name="viewport"]').getAttribute('content'),'width=device-width, initial-scale=1');
    const geometry = await page.evaluate(() => ({width:innerWidth, document:document.documentElement.scrollWidth,
      forms:Array.from(document.querySelectorAll('input,select')).map(input=>({left:input.getBoundingClientRect().left,right:input.getBoundingClientRect().right,font:parseFloat(getComputedStyle(input).fontSize)}))}));
    assert.ok(geometry.document<=geometry.width+1, `${path} overflows at ${width}: ${geometry.document}`);
    geometry.forms.forEach(rect=>{assert.ok(rect.left>=0&&rect.right<=width+1);assert.ok(rect.font>=16)});
    if(width<1100) {
      await page.locator('#menu-toggle').click();
      assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'),'true');
      assert.equal(await page.locator('#site-nav').isVisible(),true);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.locator('#site-nav a').first().click(); await page.waitForLoadState('networkidle');
      assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'),'false');
      await page.locator('#menu-toggle').focus(); await page.keyboard.press('Enter');
      await page.locator('#site-nav a').first().focus(); await page.keyboard.press('Escape');
      assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'),'false');
    } else assert.equal(await page.locator('#site-nav').isVisible(),true);
  }
  await page.goto(origin+'/main'); await page.waitForLoadState('networkidle');
  await page.evaluate(()=>{document.getElementById('wallet-address').textContent='0x'+'a'.repeat(64);});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await assertDisabled(page);
  if(process.env.UI_SCREENSHOT_DIR) await page.screenshot({path:join(process.env.UI_SCREENSHOT_DIR,`dashboard-${width}.png`),fullPage:true});
  await context.close();
});

test('legacy classroom log remains usable', async () => {
  const {page, context} = await pageWithWallet('absent'); await page.goto(origin+'/');
  await page.locator('#classroom-name').fill('UI test classroom user');
  await page.getByText('Save Name & Continue',{exact:true}).click();
  await page.goto(origin+'/viewUser');
  assert.match(await page.locator('.user-log-table').textContent(),/UI test classroom user/);
  await page.getByText('Delete All User Logs',{exact:true}).click();
  assert.equal(await page.locator('h1').textContent(),'User Log deleted'); await context.close();
});

test('no historical contract code, wallet transactions or browser exceptions', () => {
  function files(directory) {return readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?files(join(directory,entry.name)):[join(directory,entry.name)]);}
  for (const path of [...files(join(repo,'templates')),...files(join(repo,'static'))]) {
    if(!/\.(html|js|css)$/.test(path))continue;
    const text=readFileSync(path,'utf8');
    assert.doesNotMatch(text,/0x1b6fc422422447D20aF3d26aEd82AB79E5520f48|0x91C798dEc35104fd1610D38a84aE89F2B94F0351/i);
    assert.doesNotMatch(text,/eth_sendRawTransaction|wallet_sendCalls|new Web3|\.methods\./);
    if(!path.endsWith('/live.js')) assert.doesNotMatch(text,/eth_sendTransaction/);
  }
  assert.ok(methods.includes('personal_sign'));
  assert.ok(methods.every(method=>['eth_requestAccounts','eth_accounts','eth_chainId','personal_sign'].includes(method)));
  assert.deepEqual(browserErrors,[]);
});

// Integration fixtures below are explicit mocks; no chain writes occur.
const {Interface} = require('ethers');
const fixtureAddresses={RoleRegistry:'0x'+'1'.repeat(40),deposit_money:'0x'+'2'.repeat(40),paynow:'0x'+'3'.repeat(40)};
async function verifiedRoutes(page,{admin=true,sender=true,paused=false,wired=true,targetSender=false,targetRecipient=true,claim=false}={}) {
  const deployment={deployment_verified:true,wired,paused,chain_id:11155111,deployment_id:'browser-fixture',addresses:fixtureAddresses,admin:account.address,block_number:20};
  await page.route('**/api/users/me',route=>route.fulfill({json:{wallet:account.address,roles:{available:true,source:'verified_contract',admin,sender,recipient:false},deployment}}));
  await page.route('**/api/users/me/balances',route=>route.fulfill({json:{source:'verified_contract',authoritative:true,available:{wei:'1000000000000000000',test_eth:'1'},reserved:{wei:'0',test_eth:'0'},deployment}}));
  await page.route('**/api/users/roles/**',route=>route.fulfill({json:{available:true,source:'verified_contract',sender:targetSender,recipient:targetRecipient}}));
  await page.route('**/api/remittances?*',route=>route.fulfill({json:{source:'verified_contract',authoritative:true,items:[],indexing:{caught_up:true}}}));
  await page.route('**/api/remittances/1',route=>route.fulfill({json:{source:'verified_contract',authoritative:true,id:'1',sender:claim?'0x'+'e'.repeat(40):account.address,recipient:claim?account.address:'0x'+'e'.repeat(40),amount:{wei:'1',test_eth:'0.000000000000000001'},status:'PENDING'}}));
  await page.route('**/api/transactions?*',route=>route.fulfill({json:{source:'sqlite_index',authoritative:false,live_blockchain_checked:true,indexing_available:true,items:[]}}));
  await page.route('**/api/transactions/*/receipt',route=>route.fulfill({json:{status:'CONFIRMED',canonical:true,confirmations:6,transaction_hash:'0x'+'f'.repeat(64)}}));
  await page.route('**/api/transactions/prepare',route=>{
    const {action,arguments:args}=route.request().postDataJSON();
    const name=['authorizeSender','authorizeRecipient','revokeRole','pause','unpause'].includes(action)?'RoleRegistry':['deposit','withdraw'].includes(action)?'deposit_money':'paynow';
    const iface=new Interface(JSON.parse(readFileSync(join(repo,'static/abi',name+'.json'))));
    const parameters=action==='revokeRole'?[args.wallet,args.role]:['authorizeSender','authorizeRecipient'].includes(action)?[args.wallet]:action==='withdraw'?[args.amount_wei]:action==='transfer'?[args.wallet,args.amount_wei]:['claim','cancel'].includes(action)?[args.remittance_id]:[];
    route.fulfill({json:{unsigned:true,action,deployment,gas_estimate:'50000',transaction:{from:account.address,to:fixtureAddresses[name],chainId:'0xaa36a7',data:iface.encodeFunctionData(action,parameters),value:action==='deposit'?'0x'+BigInt(args.amount_wei).toString(16):'0x0',gas:'0xc350'}}});
  });
}
for (const action of ['authorizeSender','authorizeRecipient','revokeRole','pause','unpause','deposit','withdraw','transfer','claim','cancel']) test(`verified UI prepares and wallet-submits ${action} (mock only)`,async()=>{
  const {page,context}=await pageWithWallet('live-test',360);
  await verifiedRoutes(page,{paused:action==='unpause',targetSender:action==='revokeRole',targetRecipient:action!=='authorizeRecipient',claim:action==='claim',sender:!['withdraw','cancel','claim'].includes(action)});
  const route=['deposit','withdraw'].includes(action)?'/depositMoney':['transfer','claim','cancel'].includes(action)?'/transferMoney':'/main';
  await guest(page,route);await login(page);
  if(['authorizeSender','authorizeRecipient','revokeRole'].includes(action))await page.locator('#admin-wallet').fill('0x'+'e'.repeat(40));
  if(action==='deposit')await page.locator('#deposit-amount').fill('0.001');
  if(action==='withdraw')await page.locator('#withdraw-amount').fill('0.001');
  if(action==='transfer'){await page.locator('#recipient-wallet').fill('0x'+'e'.repeat(40));await page.locator('#remittance-amount').fill('0.001');}
  if(action==='claim'||action==='cancel')await page.locator('#remittance-id').fill('1');
  const button=page.locator(`[data-blockchain-action="${action}"]`);
  await waitFor(()=>button.isEnabled(),`Action ${action} should be eligible`);await button.click();
  await waitFor(()=>page.evaluate(()=>Boolean(window.__sent)),`Action ${action} should request wallet submission`);
  const sent=await page.evaluate(()=>window.__sent);assert.equal(sent.chainId,'0xaa36a7');assert.equal(sent.from.toLowerCase(),account.address.toLowerCase());
  assert.equal(sent.value,action==='deposit'?'0x38d7ea4c68000':'0x0');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await waitFor(async()=> (await page.locator('.form-result,#transaction-status').allTextContents()).some(text=>text.includes('Confirmed (6 confirmations)')));
  await context.close();
});

test('verified controls fail closed for wrong chain, unwired deployment and paused financial state',async()=>{
  for(const condition of ['wrong-chain','unwired','paused']){
    const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page,{wired:condition!=='unwired',paused:condition==='paused'});
    if(condition==='wrong-chain')await page.addInitScript(()=>window.__walletChain='0x1');
    await guest(page,'/depositMoney');await login(page);await page.locator('#deposit-amount').fill('0.001');await pause(600);
    assert.equal(await page.locator('[data-blockchain-action="deposit"]').isEnabled(),false);assert.equal(await page.evaluate(()=>Boolean(window.__sent)),false);await context.close();
  }
});

test('ordinary wallet never gets Admin controls and chain change immediately disables writes',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page,{admin:false});await guest(page);await login(page);await page.locator('#admin-wallet').fill('0x'+'e'.repeat(40));await pause(500);
  await assertDisabled(page);await page.goto(origin+'/depositMoney');await page.waitForLoadState('networkidle');await page.locator('#deposit-amount').fill('0.001');
  await waitFor(()=>page.locator('[data-blockchain-action="deposit"]').isEnabled());
  await page.evaluate(()=>{window.__walletChain='0x1';window.__emitWallet('chainChanged','0x1');});
  await assertDisabled(page);assert.equal(await page.evaluate(()=>Boolean(window.__sent)),false);await context.close();
});

test('rejected blockchain signature is reported without fabricated success',async()=>{
  const {page,context}=await pageWithWallet('reject-tx');await verifiedRoutes(page);await guest(page,'/depositMoney');await login(page);await page.locator('#deposit-amount').fill('0.001');
  const button=page.locator('[data-blockchain-action="deposit"]');await waitFor(()=>button.isEnabled());await button.click();
  await waitFor(async()=> (await page.locator('#deposit-result').textContent()).includes('cancelled'));assert.equal(await page.evaluate(()=>Boolean(window.__sent)),false);await context.close();
});

test('live browser checks produced no uncaught exceptions',()=>assert.deepEqual(browserErrors,[]));

for(const action of ['claim','cancel'])test(`${action} refreshes terminal detail and balance with exactly one fresh shared snapshot`,async()=>{
  const {page,context}=await pageWithWallet('live-test');
  await verifiedRoutes(page,{claim:action==='claim',sender:false});
  let terminal=false,detailReads=0,balanceReads=0,identityReads=0;
  await page.route('**/api/users/me/balances',route=>route.fulfill({json:{source:'verified_contract',authoritative:true,available:{wei:terminal?'2':'1',test_eth:terminal?'0.000000000000000002':'0.000000000000000001'},reserved:{wei:terminal?'0':'1',test_eth:terminal?'0':'0.000000000000000001'},deployment:{deployment_verified:true,wired:true,paused:false,chain_id:11155111,deployment_id:'browser-fixture',addresses:fixtureAddresses,admin:account.address,block_number:20}}}));

  page.on('request',request=>{if(new URL(request.url()).pathname==='/api/users/me')identityReads++;});
  await page.route('**/api/remittances/1',route=>{
    detailReads++;
    return route.fulfill({json:{source:'verified_contract',authoritative:true,id:'1',sender:action==='claim'?'0x'+'e'.repeat(40):account.address,recipient:action==='claim'?account.address:'0x'+'e'.repeat(40),amount:{wei:'1',test_eth:'0.000000000000000001'},status:terminal?(action==='claim'?'COMPLETED':'CANCELLED'):'PENDING'}});
  });
  await page.route('**/api/transactions/*/receipt',route=>{terminal=true;return route.fulfill({json:{status:'CONFIRMED',canonical:true,confirmations:6}});});
  page.on('request',request=>{if(new URL(request.url()).pathname==='/api/users/me/balances')balanceReads++;});
  await guest(page,'/transferMoney');await login(page);await page.locator('#remittance-id').fill('1');
  const button=page.locator(`[data-blockchain-action="${action}"]`);await waitFor(()=>button.isEnabled());
  assert.equal(detailReads,1,'claim/cancel eligibility shares a single ID read');
  const beforeIdentity=identityReads,beforeBalance=balanceReads;
  await button.click();
  await waitFor(async()=> (await page.locator('#remittance-detail').textContent()).includes(action==='claim'?'COMPLETED':'CANCELLED'));
  assert.equal(detailReads,2);assert.equal(identityReads,beforeIdentity+1);assert.equal(balanceReads,beforeBalance+1);
  assert.ok(await page.locator('[data-blockchain-action="claim"]').isDisabled());
  assert.ok(await page.locator('[data-blockchain-action="cancel"]').isDisabled());
  await context.close();
});

test('ordinary clicks, section navigation and focus never reload full chain state; network changes do',async()=>{
  const {page,context}=await pageWithWallet('live-test',360);await verifiedRoutes(page);
  const counts={identity:0,balance:0,list:0};
  page.on('request',request=>{const path=new URL(request.url()).pathname;if(path==='/api/users/me')counts.identity++;if(path==='/api/users/me/balances')counts.balance++;if(path==='/api/remittances')counts.list++;});
  await guest(page);await login(page);await page.waitForLoadState('networkidle');
  const before={...counts};
  await page.locator('#menu-toggle').click();
  await page.evaluate(()=>{document.querySelector('#site-nav a[href*="#activity"]')?.click();window.dispatchEvent(new Event('focus'));window.dispatchEvent(new Event('focus'));});
  await page.waitForLoadState('networkidle');assert.deepEqual(counts,before);
  await page.evaluate(()=>{window.__walletChain='0x1';window.__emitWallet('chainChanged','0x1');});
  await waitFor(()=>counts.balance===before.balance+1);await page.waitForLoadState('networkidle');
  assert.equal(counts.identity,before.identity+1);await assertDisabled(page);
  await page.evaluate(()=>{window.__walletChain='0xaa36a7';window.__emitWallet('chainChanged','0xaa36a7');});
  await waitFor(()=>counts.balance===before.balance+2);
  await page.evaluate(()=>{window.__walletAddress='0x'+'d'.repeat(40);window.__emitWallet('accountsChanged',[window.__walletAddress]);});
  await waitFor(()=>page.locator('#login').isVisible());await assertDisabled(page);
  const afterChange={...counts};await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await pause(200);
  assert.deepEqual(counts,afterChange,'changed account must not reuse authenticated chain state');
  await context.close();
});

test('admin eligibility deduplicates target role reads across actions and ordinary inputs',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);let reads=0;
  page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/api/users/roles/'))reads++;});
  await guest(page);await login(page);await page.locator('#admin-wallet').fill('0x'+'e'.repeat(40));
  await waitFor(()=>page.locator('[data-blockchain-action="authorizeSender"]').isEnabled());
  assert.equal(reads,1);
  await page.locator('#ordinary-role').selectOption('recipient');await pause(450);assert.equal(reads,1);
  await context.close();
});

for(const action of ['pause','authorizeSender'])test(`${action} invalidates cache and refreshes authorization/pause state once`,async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page,{sender:false,targetRecipient:false});
  let applied=false,balanceReads=0,listReads=0;
  const deployment={deployment_verified:true,wired:true,paused:false,chain_id:11155111,deployment_id:'browser-fixture',addresses:fixtureAddresses,admin:account.address,block_number:20};
  await page.route('**/api/users/me',route=>route.fulfill({json:{wallet:account.address,roles:{available:true,source:'verified_contract',admin:true,sender:action==='authorizeSender'&&applied,recipient:false,paused:action==='pause'&&applied},deployment:{...deployment,paused:action==='pause'&&applied}}}));
  await page.route('**/api/users/me/balances',route=>route.fulfill({json:{source:'verified_contract',authoritative:true,available:{wei:'1000000000000000000',test_eth:'1'},reserved:{wei:'0',test_eth:'0'},deployment:{...deployment,paused:action==='pause'&&applied}}}));
  await page.route('**/api/users/roles/**',route=>route.fulfill({json:{available:true,source:'verified_contract',sender:applied,recipient:false}}));
  await page.route('**/api/transactions/*/receipt',route=>{applied=true;return route.fulfill({json:{status:'CONFIRMED',canonical:true,confirmations:6}});});
  page.on('request',request=>{const path=new URL(request.url()).pathname;if(path==='/api/users/me/balances')balanceReads++;if(path==='/api/remittances')listReads++;});
  await guest(page);await login(page);if(action==='authorizeSender')await page.locator('#admin-wallet').fill(account.address);
  const button=page.locator(`[data-blockchain-action="${action}"]`);await waitFor(()=>button.isEnabled());
  const before=[balanceReads,listReads];await button.click();
  await waitFor(async()=>action==='pause'?await page.locator('[data-blockchain-action="unpause"]').isEnabled():(await page.locator('#role-status').textContent()).includes('Sender'));
  await waitFor(()=>listReads===before[1]+1);await page.waitForLoadState('networkidle');assert.deepEqual([balanceReads,listReads],[before[0]+1,before[1]+1]);
  assert.ok(await button.isDisabled());await context.close();
});

function countReads(page){
  const counts={account:0,balance:0,list:0,history:0};
  page.on('request',request=>{const path=new URL(request.url()).pathname;const key={'/api/users/me':'account','/api/users/me/balances':'balance','/api/remittances':'list','/api/transactions':'history'}[path];if(key)counts[key]++;});
  return counts;
}
test('cross-route snapshot reuse and page-specific reads without a SPA',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);const counts=countReads(page);
  await guest(page);await login(page);await page.waitForLoadState('networkidle');
  assert.deepEqual(counts,{account:1,balance:1,list:1,history:1});
  for(const route of ['/depositMoney','/transferMoney','/viewUser','/main']){
    await page.goto(origin+route);await page.waitForLoadState('networkidle');
    assert.deepEqual(counts,{account:1,balance:1,list:1,history:1},route+' reused snapshot');
  }
  const saved=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('sc6113-view-v1')));
  assert.equal(saved.context.wallet,account.address.toLowerCase());assert.equal(saved.context.chain,'0xaa36a7');assert.equal(saved.context.deployment,'browser-fixture');
  assert.doesNotMatch(JSON.stringify(saved),/csrf_token|auth_token|nonce|signature|private|credential/i);
  await waitFor(async()=> (await page.locator('#role-status').textContent()).includes('Admin'));
  await page.locator('#refresh').click();await waitFor(()=>counts.balance===2);await page.waitForLoadState('networkidle');
  assert.deepEqual(counts,{account:2,balance:2,list:2,history:2});
  await context.close();
});
test('funding first load omits unrelated activity and loads dashboard sections only once',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);const counts=countReads(page);
  await guest(page,'/depositMoney');await login(page);await page.waitForLoadState('networkidle');
  assert.deepEqual(counts,{account:1,balance:1,list:0,history:0});
  await page.goto(origin+'/transferMoney');await page.waitForLoadState('networkidle');assert.deepEqual(counts,{account:1,balance:1,list:0,history:0});
  await page.goto(origin+'/main');await page.waitForLoadState('networkidle');assert.deepEqual(counts,{account:1,balance:1,list:1,history:1});await context.close();
});
for(const status of ['rejected','failed'])test(`${status} transaction preserves snapshot without fresh blockchain load`,async()=>{
  const {page,context}=await pageWithWallet(status==='rejected'?'reject-tx':'live-test');await verifiedRoutes(page);
  if(status==='failed')await page.route('**/api/transactions/*/receipt',route=>route.fulfill({json:{status:'FAILED',canonical:true,confirmations:6}}));
  const counts=countReads(page);await guest(page,'/depositMoney');await login(page);await page.locator('#deposit-amount').fill('0.001');
  const button=page.locator('[data-blockchain-action="deposit"]');await waitFor(()=>button.isEnabled());const before={...counts};
  const cacheBefore=await page.evaluate(()=>sessionStorage.getItem('sc6113-view-v1'));
  await button.click();await waitFor(async()=>{const value=await page.locator('#deposit-result').textContent();return value.includes(status==='rejected'?'cancelled':'reverted');});
  await page.waitForLoadState('networkidle');assert.deepEqual(counts,before);assert.equal(await page.evaluate(()=>sessionStorage.getItem('sc6113-view-v1')),cacheBefore);await context.close();
});
test('deployment ID change rejects the previous cached snapshot',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);const counts=countReads(page);
  await guest(page,'/depositMoney');await login(page);await page.waitForLoadState('networkidle');
  await page.evaluate(()=>{const saved=JSON.parse(sessionStorage.getItem('sc6113-view-v1'));saved.context.deployment='another-deployment';sessionStorage.setItem('sc6113-view-v1',JSON.stringify(saved));});
  await page.goto(origin+'/depositMoney');await page.waitForLoadState('networkidle');assert.equal(counts.account,2);assert.equal(counts.balance,2);await context.close();
});
for(const field of ['session_started_at','session_view_epoch'])test(`server ${field} change invalidates cached state on focus; identical session does not`,async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);const counts=countReads(page);
  await guest(page);await login(page);await page.waitForLoadState('networkidle');const before={...counts};
  await page.evaluate(()=>{window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'));});await page.waitForLoadState('networkidle');assert.deepEqual(counts,before);
  await page.route('**/api/auth/session',async route=>{const response=await route.fetch();const data=await response.json();data[field]=field==='session_started_at'?data[field]+1:data[field]+'-changed';await route.fulfill({json:data});});
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await waitFor(()=>counts.balance===before.balance+1);await page.waitForLoadState('networkidle');assert.equal(counts.account,before.account+1);await context.close();
});
test('logout/account change clears persisted snapshot; new login performs a fresh load',async()=>{
  const {page,context}=await pageWithWallet('live-test');await verifiedRoutes(page);const counts=countReads(page);
  await guest(page);await login(page);await page.waitForLoadState('networkidle');assert.ok(await page.evaluate(()=>sessionStorage.getItem('sc6113-view-v1')));
  await page.locator('#logout').click();await waitFor(()=>page.locator('#login').isVisible());assert.equal(await page.evaluate(()=>sessionStorage.getItem('sc6113-view-v1')),null);
  await login(page);await page.waitForLoadState('networkidle');assert.equal(counts.balance,2);
  await page.evaluate(()=>window.__emitWallet('accountsChanged',['0x'+'d'.repeat(40)]));await waitFor(()=>page.locator('#login').isVisible());assert.equal(await page.evaluate(()=>sessionStorage.getItem('sc6113-view-v1')),null);await context.close();
});
