-- Existing classroom table and columns retained, never dropped/rebuilt.
CREATE TABLE IF NOT EXISTS user (name text, timestamp timestamp);
CREATE TABLE IF NOT EXISTS auth_nonces (
    nonce TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL,
    attempt_hash TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    consumed_at INTEGER
);
CREATE INDEX IF NOT EXISTS auth_nonces_wallet_expiry ON auth_nonces(wallet_address, expires_at);
CREATE TABLE IF NOT EXISTS app_wallets (
    wallet_address TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    last_login_at INTEGER NOT NULL
);
-- Server validation and logout revocation of signed Flask sessions.
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL REFERENCES app_wallets(wallet_address),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    revoked_at INTEGER
);
-- Only a future verified indexer writes these blockchain-derived records.
CREATE TABLE IF NOT EXISTS indexed_transactions (
    chain_id INTEGER NOT NULL CHECK (chain_id > 0),
    deployment_id TEXT NOT NULL,
    tx_hash TEXT NOT NULL,
    sender_wallet TEXT NOT NULL,
    recipient_wallet TEXT,
    block_number INTEGER CHECK (block_number >= 0),
    block_hash TEXT,
    receipt_status INTEGER CHECK (receipt_status IN (0, 1)),
    observed_at INTEGER NOT NULL,
    PRIMARY KEY (chain_id, deployment_id, tx_hash)
);
CREATE INDEX IF NOT EXISTS indexed_transactions_wallet ON indexed_transactions(sender_wallet, recipient_wallet);
CREATE TABLE IF NOT EXISTS indexed_events (
    chain_id INTEGER NOT NULL,
    deployment_id TEXT NOT NULL,
    tx_hash TEXT NOT NULL,
    log_index INTEGER NOT NULL CHECK (log_index >= 0),
    block_number INTEGER NOT NULL CHECK (block_number >= 0),
    block_hash TEXT NOT NULL,
    event_type TEXT NOT NULL,
    remittance_id TEXT,
    payload_json TEXT NOT NULL,
    observed_at INTEGER NOT NULL,
    PRIMARY KEY (chain_id, deployment_id, tx_hash, log_index),
    FOREIGN KEY (chain_id, deployment_id, tx_hash)
        REFERENCES indexed_transactions(chain_id, deployment_id, tx_hash)
);
CREATE TABLE IF NOT EXISTS indexing_state (
    chain_id INTEGER NOT NULL CHECK (chain_id > 0),
    deployment_id TEXT NOT NULL,
    contract_address TEXT NOT NULL,
    last_block INTEGER NOT NULL CHECK (last_block >= 0),
    last_block_hash TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (chain_id, deployment_id, contract_address)
);
