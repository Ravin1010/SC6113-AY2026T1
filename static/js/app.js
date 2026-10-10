import {requestAPI, friendlyError, deploymentMessages} from './api.js';
import {walletLogin, readSession, endSession, walletConnection} from './auth.js';
import {setupForms} from './forms.js';

const byId = id => document.getElementById(id);
let session = null, generation = 0, busy = false, historyOffset = 0;
const historyLimit = 10;
const setText = (id, text) => { if (byId(id)) byId(id).textContent = text; };

function notice(message, error = false) {
  const element = byId('notice');
  element.textContent = message; element.hidden = !message; element.classList.toggle('error', error);
}

function displaySession(value) {
  session = value;
  byId('login-panel').hidden = Boolean(value);
  byId('logout').hidden = !value;
  if (byId('session-content')) byId('session-content').hidden = !value;
  setText('wallet-address', value?.wallet || 'Unavailable');
  setText('session-status', value ? 'Authenticated session' : 'Not authenticated');
  // No configuration, API response, role or form validation can enable blockchain writes in Iteration 5.
  document.querySelectorAll('[data-blockchain-action]').forEach(button => { button.disabled = true; });
  if (!value) {
    historyOffset = 0;
    byId('history-records')?.replaceChildren();
    setText('history-status', 'Sign in to view your indexed transaction history.');
  }
}

function handleError(error) {
  if (error.code === 'AUTH_REQUIRED') { generation++; displaySession(null); }
  notice(friendlyError(error), true);
}

function setBusy(value) {
  busy = value;
  byId('login').disabled = value; byId('logout').disabled = value;
  if (byId('refresh')) byId('refresh').disabled = value;
  byId('login').textContent = value && !session ? 'Check MetaMask…' : 'Connect & sign in';
}

function deployment(error) {
  const message = deploymentMessages[error.code] || 'Deployment status could not be checked. Blockchain actions remain unavailable.';
  document.querySelectorAll('[data-deployment-status]').forEach(element => { element.textContent = message; });
  const detail = error.details;
  setText('deployment-detail', [error.code, detail?.missing?.length ? `Missing: ${detail.missing.join(', ')}` : '', detail?.invalid?.length ? `Invalid: ${detail.invalid.join(', ')}` : ''].filter(Boolean).join(' · '));
}

async function loadDeployment(ticket) {
  try {
    await requestAPI('/api/users/me/balances');
    if (ticket === generation) deployment({code: 'BLOCKCHAIN_READER_UNAVAILABLE'});
  } catch (error) {
    if (ticket !== generation) return;
    if (error.code === 'AUTH_REQUIRED') throw error;
    deployment(error);
    if (!deploymentMessages[error.code]) notice(friendlyError(error), true);
  }
}

function historyCard(record) {
  const card = document.createElement('article'); card.className = 'history-record';
  const heading = document.createElement('h3'); heading.textContent = 'Indexed transaction'; card.append(heading);
  const data = document.createElement('dl'); card.append(data);
  const receipt = record.receipt_status === 1 ? 'Succeeded (cached receipt)' : record.receipt_status === 0 ? 'Failed (cached receipt)' : 'Not indexed';
  for (const [label, value] of [['Transaction hash', record.tx_hash], ['Sender', record.sender_wallet], ['Recipient', record.recipient_wallet || 'Not indexed'], ['Block', record.block_number ?? 'Not indexed'], ['Receipt', receipt], ['Deployment', record.deployment_id], ['Network chain ID', record.chain_id]]) {
    const term = document.createElement('dt'); term.textContent = label;
    const description = document.createElement('dd'); description.textContent = String(value ?? 'Not indexed'); description.className = 'identifier';
    data.append(term, description);
  }
  return card;
}

async function loadHistory(ticket) {
  if (!byId('history-records')) return;
  const previous = byId('previous-history'), next = byId('next-history');
  previous.disabled = true; next.disabled = true;
  setText('history-status', 'Loading indexed history…');
  byId('history-records').replaceChildren();
  try {
    const data = await requestAPI(`/api/transactions?limit=${historyLimit}&offset=${historyOffset}`);
    if (ticket !== generation || !session) return;
    if (data.source !== 'sqlite_index' || data.authoritative !== false || data.live_blockchain_checked !== false || !Array.isArray(data.items)) throw new Error('History provenance could not be confirmed. No records are displayed.');
    setText('history-provenance', `Source: cached SQLite index · Not authoritative · Live blockchain not checked · ${data.indexing_available ? 'Indexed data available' : 'Indexer not active'}.`);
    setText('history-status', data.items.length ? `${data.items.length} indexed record(s) on this page.` : historyOffset ? 'No indexed transactions on this page.' : 'No indexed transactions available yet. This does not establish that blockchain history is empty.');
    byId('history-records').replaceChildren(...data.items.map(historyCard));
    previous.disabled = historyOffset === 0; next.disabled = data.items.length < historyLimit;
  } catch (error) {
    if (ticket !== generation) return;
    setText('history-status', `Indexed history unavailable. ${friendlyError(error)}`);
    if (error.code === 'AUTH_REQUIRED') throw error;
    previous.disabled = historyOffset === 0;
  }
}

async function loadAccount(ticket) {
  const data = await requestAPI('/api/users/me');
  if (ticket !== generation || !session) return;
  if (data.wallet.toLowerCase() !== session.wallet.toLowerCase()) throw new Error('Wallet session changed. Reload and sign in again.');
  setText('role-status', 'Role information unavailable until verified Sepolia deployment.');
  // Iteration 5 deliberately cannot turn hypothetical future roles into enabled controls.
  const connection = await walletConnection();
  if (ticket !== generation) return;
  setText('connected-wallet', connection.address);
  setText('wallet-network', connection.network);
  if (/^0x/i.test(connection.address) && connection.address.toLowerCase() !== session.wallet.toLowerCase()) {
    notice('Your authenticated wallet differs from the connected wallet. Log out and sign in with the intended account.', true);
  }
  if (data.roles?.error) deployment(data.roles.error);
  await Promise.all([loadDeployment(ticket), loadHistory(ticket)]);
}

async function restore() {
  if (busy) return;
  const ticket = ++generation;
  try {
    const current = await readSession();
    if (ticket !== generation) return;
    displaySession(current);
    await loadAccount(ticket);
  } catch (error) {
    if (ticket !== generation) return;
    if (error.code === 'AUTH_REQUIRED') displaySession(null);
    else { displaySession(null); notice(friendlyError(error), true); }
  }
}

byId('login').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true); notice('Approve wallet access, then review and sign the login message in MetaMask.');
  const ticket = ++generation;
  try {
    const current = await walletLogin(() => ticket === generation);
    if (ticket !== generation) return;
    displaySession(current); notice('Wallet session authenticated. Blockchain actions remain unavailable.');
    await loadAccount(ticket);
  } catch (error) { if (ticket === generation) handleError(error); }
  finally { setBusy(false); }
});

byId('logout').addEventListener('click', async () => {
  if (busy || !session) return;
  generation++; setBusy(true);
  try { await endSession(session.csrf_token); displaySession(null); notice('Logged out of this application. Your wallet may still be connected to MetaMask.'); }
  catch (error) { handleError(error); }
  finally { setBusy(false); }
});

byId('refresh')?.addEventListener('click', async () => {
  if (!session || busy) return;
  const ticket = ++generation; setBusy(true); notice('');
  try { const current = await readSession(); if (ticket !== generation) return; displaySession(current); await loadAccount(ticket); }
  catch (error) { if (ticket === generation) handleError(error); }
  finally { setBusy(false); }
});

for (const [id, direction] of [['previous-history', -1], ['next-history', 1]]) {
  byId(id)?.addEventListener('click', async () => {
    if (!session || busy) return;
    historyOffset = Math.max(0, historyOffset + direction * historyLimit);
    const ticket = ++generation;
    try { await loadHistory(ticket); } catch (error) { if (ticket === generation) handleError(error); }
  });
}

const toggle = byId('menu-toggle'), nav = byId('site-nav');
function closeMenu() { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); }
toggle.addEventListener('click', () => { const open = nav.classList.toggle('open'); toggle.setAttribute('aria-expanded', String(open)); });
nav.addEventListener('click', event => { if (event.target.closest('a,button')) closeMenu(); });
nav.addEventListener('keydown', event => { if (event.key === 'Escape') { closeMenu(); toggle.focus(); } });

setupForms(() => session?.wallet || '');
window.ethereum?.on?.('accountsChanged', async () => {
  const old = session; generation++; displaySession(null);
  notice('Your selected wallet changed. Sign in again with the intended account.', true);
  if (old) { try { await endSession(old.csrf_token); } catch (error) { if (error.code !== 'AUTH_REQUIRED') notice(`Wallet changed. ${friendlyError(error)} Log out again or retry before continuing.`, true); } }
});
window.ethereum?.on?.('chainChanged', async () => {
  if (!session || busy) return;
  const ticket = generation, connection = await walletConnection();
  if (ticket === generation) setText('wallet-network', connection.network);
});
window.addEventListener('focus', () => { if (!busy) restore(); });
window.addEventListener('pageshow', event => { if (event.persisted) restore(); });
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && !busy) restore(); });
displaySession(null);
restore();
