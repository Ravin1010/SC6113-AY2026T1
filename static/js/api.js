export class APIError extends Error {
  constructor(code, message, status = 0, details = null) {
    super(message); this.code = code; this.status = status; this.details = details;
  }
}

export async function requestAPI(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(path, {credentials: 'same-origin', cache: 'no-store', ...options, signal: controller.signal});
    let data;
    try { data = await response.json(); }
    catch { throw new APIError('INVALID_RESPONSE', 'The server returned an unreadable response. Try again.', response.status); }
    if (!response.ok) throw new APIError(data.error?.code || 'API_ERROR', data.error?.message || 'Request failed.', response.status, data.error?.details);
    return data;
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError('NETWORK_ERROR', 'The server could not be reached. Check your connection and try again.');
  } finally { clearTimeout(timeout); }
}

export function postJSON(path, body, csrf) {
  return requestAPI(path, {method: 'POST', headers: {'Content-Type': 'application/json', ...(csrf ? {'X-CSRF-Token': csrf} : {})}, body: JSON.stringify(body)});
}

export const deploymentMessages = {
  BLOCKCHAIN_NOT_CONFIGURED: 'Blockchain deployment not configured yet. Available after verified Sepolia deployment.',
  BLOCKCHAIN_DEPLOYMENT_UNVERIFIED: 'Deployment verification is pending. Blockchain actions remain unavailable.',
  BLOCKCHAIN_READER_UNAVAILABLE: 'Live blockchain reads are not available yet. Blockchain actions remain unavailable.'
};

export function friendlyError(error) {
  const messages = {
    WALLET_UNAVAILABLE: 'MetaMask is unavailable. Install it or open this page in the MetaMask mobile browser.',
    WALLET_REJECTED: 'The wallet request was cancelled. Nothing was submitted; you can try again.',
    WALLET_CHANGED: 'Your selected wallet changed. Sign in again with the intended account.',
    SIGNER_MISMATCH: 'The signature does not match the selected wallet. Check your MetaMask account and try again.',
    LOGIN_ATTEMPT_MISMATCH: 'This login attempt no longer matches your wallet or browser. Request a new login.',
    NONCE_EXPIRED: 'The login message expired. Sign in again to request a fresh message.',
    NONCE_USED: 'This login message was already used. Sign in again for a fresh message.',
    NONCE_UNAVAILABLE: 'This login attempt expired or was already used. Sign in again.',
    AUTH_REQUIRED: 'Your session ended. Sign in again to continue.'
  };
  return deploymentMessages[error.code] || messages[error.code] || error.message || 'The request could not be completed. Try again.';
}
