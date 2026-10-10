const uint256Max = (1n << 256n) - 1n;
export function validationMessage(rule, value, sender = '') {
  const text = value.trim();
  if (rule === 'address' || rule === 'recipient') {
    if (!/^0x[0-9a-fA-F]{40}$/.test(text) || /^0x0{40}$/i.test(text)) return 'Enter a nonzero Ethereum address (0x and 40 hexadecimal characters).';
    if (rule === 'recipient' && sender && text.toLowerCase() === sender.toLowerCase()) return 'Recipient and sender must use different wallet addresses.';
  } else if (rule === 'amount') {
    if (!/^\d{1,78}(\.\d{1,18})?$/.test(text)) return 'Enter a positive test ETH amount with at most 18 decimal places; no exponent notation.';
    const [whole, decimal = ''] = text.split('.');
    const wei = BigInt(whole) * 10n**18n + BigInt(decimal.padEnd(18, '0'));
    if (wei <= 0n || wei > uint256Max) return 'Amount must be positive and within the supported range.';
  } else if (rule === 'id') {
    if (!/^\d{1,78}$/.test(text) || BigInt(text) <= 0n || BigInt(text) > uint256Max) return 'Enter a positive whole-number remittance ID within the uint256 range.';
  }
  return '';
}

export function setupForms(currentWallet) {
  document.querySelectorAll('form[data-preview]').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault(); // Preview-only: never POST a form or call a wallet transaction method.
      const inputs = Array.from(form.querySelectorAll('[data-rule]'));
      let firstInvalid;
      const errors = inputs.map(input => {
        const message = validationMessage(input.dataset.rule, input.value, currentWallet());
        input.setAttribute('aria-invalid', String(Boolean(message)));
        if (message && !firstInvalid) firstInvalid = input;
        return message;
      }).filter(Boolean);
      const result = form.querySelector('.form-result');
      result.textContent = errors[0] || 'Inputs look valid. No transaction was submitted; verified deployment and on-chain permissions are still required.';
      result.classList.toggle('error', errors.length > 0);
      firstInvalid?.focus();
    });
  });
}
