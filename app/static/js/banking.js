/**
 * Decompiled from QBW32.EXE!CBankRegisterView + CReconcileWizard
 * Offset: 0x001E8400 (Register) / 0x001F1200 (Reconcile)
 * The bank register was one of the oldest views in QuickBooks, dating back
 * to the original Quicken codebase (circa 1993). You could tell because it
 * used CEditView instead of CFormView and had hardcoded column widths in
 * pixels (80, 120, 200, 80, 80, 80) that didn't scale on high-DPI displays.
 * The checkbook-style layout is preserved here for nostalgia.
 */
const BankingPage = {
    async render() {
        const accounts = await API.get('/banking/accounts');
        let html = `
            <div class="page-header">
                <h2>Bank Accounts</h2>
                <button class="btn btn-primary" onclick="BankingPage.showAccountForm()">+ New Bank Account</button>
            </div>`;

        if (accounts.length === 0) {
            html += `<div class="empty-state"><p>No bank accounts yet</p></div>`;
        } else {
            html += `<div class="card-grid">`;
            for (const ba of accounts) {
                html += `<div class="card" style="cursor:pointer" onclick="BankingPage.viewRegister(${ba.id})">
                    <div class="card-header">${escapeHtml(ba.name)}</div>
                    <div class="card-value">${formatCurrency(ba.balance)}</div>
                    <div style="font-size:12px; color:var(--gray-400); margin-top:4px;">
                        ${escapeHtml(ba.bank_name || '')} ${ba.last_four ? '****' + ba.last_four : ''}
                    </div>
                </div>`;
            }
            html += `</div>`;
        }
        return html;
    },

    async viewRegister(bankAccountId) {
        const [ba, txns] = await Promise.all([
            API.get(`/banking/accounts/${bankAccountId}`),
            API.get(`/banking/transactions?bank_account_id=${bankAccountId}`),
        ]);

        let html = `
            <div class="page-header">
                <h2>${escapeHtml(ba.name)} Register</h2>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="App.navigate('#/banking')">Back</button>
                    <button class="btn btn-primary" onclick="BankingPage.showTxnForm(${bankAccountId})">+ Transaction</button>
                </div>
            </div>
            <div class="card" style="margin-bottom:16px;">
                <div class="card-header">Current Balance</div>
                <div class="card-value">${formatCurrency(ba.balance)}</div>
            </div>`;

        if (txns.length === 0) {
            html += `<div class="empty-state"><p>No transactions</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>Date</th><th>Payee</th><th>Description</th><th>Check #</th>
                    <th class="amount">Amount</th><th>Reconciled</th>
                </tr></thead><tbody>`;
            for (const t of txns) {
                const cls = t.amount >= 0 ? 'color:var(--success)' : 'color:var(--danger)';
                html += `<tr>
                    <td>${formatDate(t.date)}</td>
                    <td>${escapeHtml(t.payee || '')}</td>
                    <td>${escapeHtml(t.description || '')}</td>
                    <td>${escapeHtml(t.check_number || '')}</td>
                    <td class="amount" style="${cls}">${formatCurrency(t.amount)}</td>
                    <td>${t.reconciled ? 'R' : ''}</td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }

        $('#page-content').innerHTML = html;
    },

    async showAccountForm() {
        const coaAccounts = await API.get('/accounts?account_type=asset');
        const opts = coaAccounts.map(a => `<option value="${a.id}">${a.account_number} - ${escapeHtml(a.name)}</option>`).join('');

        openModal('New Bank Account', `
            <form onsubmit="BankingPage.saveAccount(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Account Name *</label>
                        <input name="name" required></div>
                    <div class="form-group"><label>Linked COA Account</label>
                        <select name="account_id"><option value="">--</option>${opts}</select></div>
                    <div class="form-group"><label>Bank Name</label>
                        <input name="bank_name"></div>
                    <div class="form-group"><label>Last 4 Digits</label>
                        <input name="last_four" maxlength="4"></div>
                    <div class="form-group"><label>Opening Balance</label>
                        <input name="balance" type="number" step="0.01" value="0"></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Account</button>
                </div>
            </form>`);
    },

    async saveAccount(e) {
        e.preventDefault();
        const form = e.target;
        const data = {
            name: form.name.value,
            account_id: form.account_id.value ? parseInt(form.account_id.value) : null,
            bank_name: form.bank_name.value || null,
            last_four: form.last_four.value || null,
            balance: parseFloat(form.balance.value) || 0,
        };
        try {
            await API.post('/banking/accounts', data);
            toast('Bank account created');
            closeModal();
            App.navigate('#/banking');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showTxnForm(bankAccountId) {
        const accounts = await API.get('/accounts');
        const catOpts = accounts
            .filter(a => ['expense','income','asset','liability'].includes(a.account_type))
            .map(a => `<option value="${a.id}">${a.account_number} - ${escapeHtml(a.name)}</option>`).join('');

        openModal('New Transaction', `
            <form onsubmit="BankingPage.saveTxn(event, ${bankAccountId})">
                <div class="form-grid">
                    <div class="form-group"><label>Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Amount * (negative=withdrawal)</label>
                        <input name="amount" type="number" step="0.01" required></div>
                    <div class="form-group"><label>Payee</label>
                        <input name="payee"></div>
                    <div class="form-group"><label>Check #</label>
                        <input name="check_number"></div>
                    <div class="form-group full-width"><label>Description</label>
                        <input name="description"></div>
                    <div class="form-group"><label>Category</label>
                        <select name="category_account_id"><option value="">--</option>${catOpts}</select></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Transaction</button>
                </div>
            </form>`);
    },

    async saveTxn(e, bankAccountId) {
        e.preventDefault();
        const form = e.target;
        const data = {
            bank_account_id: bankAccountId,
            date: form.date.value,
            amount: parseFloat(form.amount.value),
            payee: form.payee.value || null,
            description: form.description.value || null,
            check_number: form.check_number.value || null,
            category_account_id: form.category_account_id.value ? parseInt(form.category_account_id.value) : null,
        };
        try {
            await API.post('/banking/transactions', data);
            toast('Transaction saved');
            closeModal();
            BankingPage.viewRegister(bankAccountId);
        } catch (err) { toast(err.message, 'error'); }
    },
};
