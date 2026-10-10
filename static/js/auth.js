import {APIError, postJSON, requestAPI} from './api.js';

export function provider() {
  const injected = window.ethereum;
  if (!injected?.request) throw new APIError('WALLET_UNAVAILABLE', 'MetaMask is unavailable.');
  return injected;
}

function selectedAccount(accounts) {
  const account = accounts?.[0];
  if (typeof account !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(account) || /^0x0{40}$/i.test(account)) {
    throw new APIError('WALLET_CHANGED', 'No valid wallet account is connected.');
  }
  return account;
}

export async function walletLogin(isCurrent = () => true) {
  const wallet = provider();
  try {
    const address = selectedAccount(await wallet.request({method: 'eth_requestAccounts'}));
    const challenge = await postJSON('/api/auth/nonce', {wallet: address});
    if (!isCurrent()) throw new APIError('WALLET_CHANGED', 'Login interrupted.');
    // personal_sign signs the exact UTF-8 bytes supplied by the server, encoded as hex.
    const bytes = new TextEncoder().encode(challenge.message);
    const messageHex = '0x' + Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    const signature = await wallet.request({method: 'personal_sign', params: [messageHex, address]});
    const selected = selectedAccount(await wallet.request({method: 'eth_accounts'}));
    if (!isCurrent() || selected.toLowerCase() !== address.toLowerCase()) throw new APIError('WALLET_CHANGED', 'Selected wallet changed.');
    const verified = await postJSON('/api/auth/verify', {wallet: address, nonce: challenge.nonce, signature});
    // Account events during verification must not leave an obsolete wallet session active.
    const after = (await wallet.request({method: 'eth_accounts'}))?.[0];
    if (!isCurrent() || after?.toLowerCase() !== address.toLowerCase()) {
      await endSession(verified.csrf_token);
      throw new APIError('WALLET_CHANGED', 'Selected wallet changed.');
    }
    return verified;
  } catch (error) {
    if (error.code === 4001 || error.code === '4001') throw new APIError('WALLET_REJECTED', 'Wallet request cancelled.');
    throw error;
  }
}

export const readSession = () => requestAPI('/api/auth/session');
export const endSession = csrf => postJSON('/api/auth/logout', {}, csrf);

export async function walletConnection() {
  if (!window.ethereum?.request) return {address: 'Wallet provider unavailable', network: 'Not connected'};
  try {
    const accounts = await window.ethereum.request({method: 'eth_accounts'});
    const chain = await window.ethereum.request({method: 'eth_chainId'});
    const network = chain === '0xaa36a7' ? 'Sepolia · test network' : `Wallet chain ${chain} · Sepolia required for future transactions`;
    return {address: accounts?.[0] || 'Not connected', network};
  } catch { return {address: 'Wallet connection unavailable', network: 'Unavailable'}; }
}
