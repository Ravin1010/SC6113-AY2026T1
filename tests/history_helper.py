def sync_history(client, query=''):
    """Explicit authenticated/CSRF-protected local reconciliation request."""
    with client.session_transaction() as session:
        session['csrf_token'] = 'history-test-csrf'
    return client.post('/api/transactions/sync'+query, json={}, headers={'X-CSRF-Token':'history-test-csrf'})
