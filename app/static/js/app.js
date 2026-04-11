/**
 * Decompiled from QBW32.EXE!CMainFrame + CQBNavigator  Offset: 0x00042000
 * Original was an MFC CFrameWnd with a custom left-panel "Navigator" control
 * (the icon sidebar everyone remembers). CMainFrame::OnNavigate() dispatched
 * to individual CFormView subclasses via a 31-entry function pointer table.
 * We replaced the Win32 message pump with hash-based routing because, again,
 * it is no longer 2003. WM_COMMAND 0x8001 through 0x801F, rest in peace.
 */
const App = {
    routes: {
        '/':          { page: 'dashboard', label: 'Dashboard',        render: () => App.renderDashboard() },
        '/customers': { page: 'customers', label: 'Customer Center',  render: () => CustomersPage.render() },
        '/vendors':   { page: 'vendors',   label: 'Vendor Center',    render: () => VendorsPage.render() },
        '/items':     { page: 'items',     label: 'Item List',        render: () => ItemsPage.render() },
        '/invoices':  { page: 'invoices',  label: 'Create Invoices',  render: () => InvoicesPage.render() },
        '/estimates': { page: 'estimates', label: 'Create Estimates', render: () => EstimatesPage.render() },
        '/payments':  { page: 'payments',  label: 'Receive Payments', render: () => PaymentsPage.render() },
        '/banking':   { page: 'banking',   label: 'Bank Accounts',    render: () => BankingPage.render() },
        '/accounts':  { page: 'accounts',  label: 'Chart of Accounts',render: () => App.renderAccounts() },
        '/reports':   { page: 'reports',   label: 'Report Center',    render: () => ReportsPage.render() },
    },

    async navigate(hash) {
        const path = hash.replace('#', '') || '/';
        const route = App.routes[path];
        if (!route) { $('#page-content').innerHTML = '<p>Page not found</p>'; return; }

        // Update active nav
        $$('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === route.page);
        });

        // Status bar
        App.setStatus(`Loading ${route.label}...`);

        try {
            const html = await route.render();
            $('#page-content').innerHTML = html;
            App.setStatus(`${route.label} — Ready`);
        } catch (err) {
            console.error(err);
            $('#page-content').innerHTML = `<div class="empty-state">
                <p><strong>Error 0x8004:</strong> ${escapeHtml(err.message)}</p>
                <p style="font-size:10px; color:var(--text-muted);">CQBView::OnActivate() failed at offset 0x00042A10</p>
            </div>`;
            App.setStatus('Error — see console for details');
        }
    },

    setStatus(text) {
        const el = $('#status-text');
        if (el) el.textContent = text;
    },

    updateClock() {
        const now = new Date();
        const clock = $('#topbar-clock');
        if (clock) clock.textContent = now.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
        const statusDate = $('#status-date');
        if (statusDate) statusDate.textContent = now.toLocaleDateString('en-US', {weekday:'long', year:'numeric', month:'long', day:'numeric'});
    },

    showAbout() {
        const splash = $('#splash');
        if (splash) splash.classList.remove('hidden');
    },

    async renderDashboard() {
        const data = await API.get('/dashboard');

        let recentInv = data.recent_invoices.map(inv =>
            `<tr>
                <td><strong>${escapeHtml(inv.invoice_number)}</strong></td>
                <td>${formatDate(inv.date)}</td>
                <td>${statusBadge(inv.status)}</td>
                <td class="amount">${formatCurrency(inv.total)}</td>
            </tr>`
        ).join('') || '<tr><td colspan="4" style="color:var(--text-muted); font-size:11px;">No invoices yet &mdash; use Create Invoice to get started</td></tr>';

        let recentPay = data.recent_payments.map(p =>
            `<tr>
                <td>${formatDate(p.date)}</td>
                <td>${escapeHtml(p.method || '')}</td>
                <td class="amount">${formatCurrency(p.amount)}</td>
            </tr>`
        ).join('') || '<tr><td colspan="3" style="color:var(--text-muted); font-size:11px;">No payments recorded yet</td></tr>';

        let bankCards = data.bank_balances.map(ba =>
            `<div class="card" style="cursor:pointer" onclick="App.navigate('#/banking')">
                <div class="card-header">${escapeHtml(ba.name)}</div>
                <div class="card-value">${formatCurrency(ba.balance)}</div>
            </div>`
        ).join('');

        if (!bankCards) {
            bankCards = `<div class="card">
                <div class="card-header">No Bank Accounts</div>
                <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">
                    Go to Banking to set up an account</div>
            </div>`;
        }

        return `
            <div class="page-header">
                <h2>Company Snapshot</h2>
                <div style="font-size:10px; color:var(--text-muted);">
                    Slowbooks Pro 2026 &mdash; Build 12.0.3190-R
                </div>
            </div>

            <div class="card-grid">
                <div class="card">
                    <div class="card-header">Total Receivables</div>
                    <div class="card-value">${formatCurrency(data.total_receivables)}</div>
                </div>
                <div class="card">
                    <div class="card-header">Overdue Invoices</div>
                    <div class="card-value" ${data.overdue_count > 0 ? 'style="color:var(--qb-red)"' : ''}>${data.overdue_count}</div>
                </div>
                <div class="card">
                    <div class="card-header">Active Customers</div>
                    <div class="card-value">${data.customer_count}</div>
                </div>
            </div>

            <div class="dashboard-section">
                <h3>Bank Balances</h3>
                <div class="card-grid">${bankCards}</div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <div class="dashboard-section">
                    <h3>Recent Invoices</h3>
                    <div class="table-container"><table>
                        <thead><tr><th>#</th><th>Date</th><th>Status</th><th class="amount">Total</th></tr></thead>
                        <tbody>${recentInv}</tbody>
                    </table></div>
                </div>
                <div class="dashboard-section">
                    <h3>Recent Payments</h3>
                    <div class="table-container"><table>
                        <thead><tr><th>Date</th><th>Method</th><th class="amount">Amount</th></tr></thead>
                        <tbody>${recentPay}</tbody>
                    </table></div>
                </div>
            </div>`;
    },

    async renderAccounts() {
        const accounts = await API.get('/accounts');
        const grouped = {};
        for (const a of accounts) {
            if (!grouped[a.account_type]) grouped[a.account_type] = [];
            grouped[a.account_type].push(a);
        }

        const typeOrder = ['asset', 'liability', 'equity', 'income', 'cogs', 'expense'];
        const typeNames = { asset: 'Assets', liability: 'Liabilities', equity: 'Equity',
            income: 'Income', cogs: 'Cost of Goods Sold', expense: 'Expenses' };

        let html = `
            <div class="page-header">
                <h2>Chart of Accounts</h2>
                <button class="btn btn-primary" onclick="App.showAccountForm()">New Account</button>
            </div>
            <div class="table-container"><table>
                <thead><tr><th style="width:80px;">Number</th><th>Name</th><th style="width:100px;">Type</th><th class="amount" style="width:100px;">Balance</th><th style="width:60px;">Actions</th></tr></thead>
                <tbody>`;

        for (const type of typeOrder) {
            const accts = grouped[type] || [];
            if (accts.length === 0) continue;
            html += `<tr style="background:linear-gradient(180deg, #e8ecf2 0%, #dde2ea 100%);"><td colspan="5" style="font-weight:700; color:var(--qb-navy); font-size:11px; padding:4px 10px;">${typeNames[type]}</td></tr>`;
            for (const a of accts) {
                html += `<tr>
                    <td style="font-family:var(--font-mono);">${escapeHtml(a.account_number || '')}</td>
                    <td>${a.is_system ? '' : ''}<strong>${escapeHtml(a.name)}</strong></td>
                    <td>${a.account_type}</td>
                    <td class="amount">${formatCurrency(a.balance)}</td>
                    <td class="actions">
                        ${!a.is_system ? `<button class="btn btn-sm btn-secondary" onclick="App.showAccountForm(${a.id})">Edit</button>` : ''}
                    </td>
                </tr>`;
            }
        }
        html += `</tbody></table></div>`;
        return html;
    },

    async showAccountForm(id = null) {
        let acct = { name: '', account_number: '', account_type: 'expense', description: '' };
        if (id) acct = await API.get(`/accounts/${id}`);

        const types = ['asset','liability','equity','income','cogs','expense'];
        openModal(id ? 'Edit Account' : 'New Account', `
            <form onsubmit="App.saveAccount(event, ${id})">
                <div class="form-grid">
                    <div class="form-group"><label>Account Number</label>
                        <input name="account_number" value="${escapeHtml(acct.account_number || '')}"></div>
                    <div class="form-group"><label>Name *</label>
                        <input name="name" required value="${escapeHtml(acct.name)}"></div>
                    <div class="form-group"><label>Type *</label>
                        <select name="account_type">
                            ${types.map(t => `<option value="${t}" ${acct.account_type===t?'selected':''}>${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join('')}
                        </select></div>
                    <div class="form-group full-width"><label>Description</label>
                        <textarea name="description">${escapeHtml(acct.description || '')}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${id ? 'Update' : 'Create'} Account</button>
                </div>
            </form>`);
    },

    async saveAccount(e, id) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            if (id) { await API.put(`/accounts/${id}`, data); toast('Account updated'); }
            else { await API.post('/accounts', data); toast('Account created'); }
            closeModal();
            App.navigate('#/accounts');
        } catch (err) { toast(err.message, 'error'); }
    },

    init() {
        window.addEventListener('hashchange', () => App.navigate(location.hash));

        // Start clock — CMainFrame::OnTimer() at 1-second interval (WM_TIMER id=1)
        App.updateClock();
        setInterval(App.updateClock, 60000);

        // Navigate after splash closes
        App.navigate(location.hash || '#/');
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());
