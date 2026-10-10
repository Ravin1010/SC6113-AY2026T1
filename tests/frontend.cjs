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
        if (method === 'eth_chainId') return '0xaa36a7';
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
  const {page, context} = await pageWithWallet('absent'); await guest(page,'/');
  await page.getByText('Classroom name log',{exact:true}).click();
  await page.locator('#classroom-name').fill('UI test classroom user');
  await page.getByText('Save name & open dashboard',{exact:true}).click();
  await page.goto(origin+'/viewUser');
  assert.match(await page.locator('.legacy-log').textContent(),/UI test classroom user/);
  await page.getByText('Delete user log',{exact:true}).click();
  assert.equal(await page.locator('h1').textContent(),'User log deleted'); await context.close();
});

test('no historical contract code, wallet transactions or browser exceptions', () => {
  function files(directory) {return readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?files(join(directory,entry.name)):[join(directory,entry.name)]);}
  for (const path of [...files(join(repo,'templates')),...files(join(repo,'static'))]) {
    if(!/\.(html|js|css)$/.test(path))continue;
    const text=readFileSync(path,'utf8');
    assert.doesNotMatch(text,/0x1b6fc422422447D20aF3d26aEd82AB79E5520f48|0x91C798dEc35104fd1610D38a84aE89F2B94F0351/i);
    assert.doesNotMatch(text,/eth_sendTransaction|eth_sendRawTransaction|wallet_sendCalls|new Web3|\.methods\./);
  }
  assert.ok(methods.includes('personal_sign'));
  assert.ok(methods.every(method=>['eth_requestAccounts','eth_accounts','eth_chainId','personal_sign'].includes(method)));
  assert.deepEqual(browserErrors,[]);
});
