/**
 * OddCity Admin Panel - JavaScript
 */

class AdminPanel {
    constructor() {
        this.apiUrl = window.location.origin;
        this.isLoggedIn = false;
        this.currentPage = 'dashboard';
        this.currentPeriod = 7;
        this.csrfToken = null;

        this.init();
    }

    async init() {
        // Check login status
        await this.checkAuth();

        // Setup event listeners
        this.setupEventListeners();

        // If logged in, load dashboard
        if (this.isLoggedIn) {
            this.loadDashboard();
        }
    }

    setupEventListeners() {
        // Login form
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });

        // Logout button
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                this.navigateTo(page);
            });
        });

        // Period selector
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentPeriod = parseInt(btn.dataset.days);
                document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.loadDashboard();
            });
        });

        // Menu toggle (mobile)
        document.getElementById('menuToggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        // Refresh buttons
        document.getElementById('refreshUsers')?.addEventListener('click', () => this.loadUsers());
        document.getElementById('refreshGames')?.addEventListener('click', () => this.loadGames());

        // Game type filter
        document.getElementById('gameTypeFilter')?.addEventListener('change', () => this.loadGames());

        // New Rule Set button
        document.getElementById('newRuleSetBtn')?.addEventListener('click', () => this.openRuleSetModal());

        // Rule Set form
        document.getElementById('ruleSetForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createRuleSet();
        });
    }

    async checkAuth() {
        try {
            const response = await fetch(`${this.apiUrl}/me`, {
                credentials: 'include'
            });

            if (response.ok) {
                const user = await response.json();
                if (user.is_admin) {
                    this.isLoggedIn = true;
                    await this.fetchCsrfToken();
                    document.getElementById('loginModal').classList.add('hidden');
                    document.getElementById('adminEmail').textContent = user.email;
                } else {
                    this.showNotification('Admin privileges required!', 'error');
                    await this.logout();
                }
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
        } catch (error) {
            console.error('Auth check error:', error);
            document.getElementById('loginModal').classList.remove('hidden');
        }
    }

    async login() {
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch(`${this.apiUrl}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                if (data.is_admin) {
                    this.isLoggedIn = true;
                    await this.fetchCsrfToken();
                    document.getElementById('loginModal').classList.add('hidden');
                    document.getElementById('adminEmail').textContent = email;
                    this.showNotification('Login successful!', 'success');
                    this.loadDashboard();
                } else {
                    this.showNotification('Admin privileges required!', 'error');
                }
            } else {
                this.showNotification(data.message || 'Login failed!', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    async logout() {
        try {
            await fetch(`${this.apiUrl}/logout`, {
                method: 'POST',
                headers: this.getSecureHeaders(),
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }

        // Tüm client-side verileri temizle
        this.isLoggedIn = false;
        this.csrfToken = null;
        this.currentPage = 'dashboard';
        this.currentPeriod = 7;

        // Dashboard verilerini temizle
        document.getElementById('totalGames').textContent = '0';
        document.getElementById('uniquePlayers').textContent = '0';
        document.getElementById('totalBets').textContent = '₿0.00';
        document.getElementById('houseProfit').textContent = '₿0.00';

        document.getElementById('loginModal').classList.remove('hidden');
        this.showNotification('Logged out', 'success');
    }

    // ========================================
    // CSRF Token Methods
    // ========================================

    async fetchCsrfToken() {
        try {
            const response = await fetch(`${this.apiUrl}/csrf-token`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.csrfToken = data.csrf_token;
            }
        } catch (error) {
            console.error('CSRF token fetch error:', error);
        }
    }

    getSecureHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.csrfToken) {
            headers['X-CSRF-Token'] = this.csrfToken;
        }
        return headers;
    }

    navigateTo(page) {
        this.currentPage = page;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        // Show page
        document.querySelectorAll('.page').forEach(p => {
            p.classList.add('hidden');
        });
        document.getElementById(`page-${page}`).classList.remove('hidden');

        // Close mobile menu
        document.getElementById('sidebar').classList.remove('open');

        // Load page data
        switch (page) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'games':
                this.loadGames();
                break;
            case 'rulesets':
                this.loadRuleSets();
                break;
            case 'transactions':
                this.loadTransactions();
                break;
        }
    }

    // ========================================
    // Dashboard
    // ========================================

    async loadDashboard() {
        await Promise.all([
            this.loadStats(),
            this.loadRecentGames(),
            this.loadTopPlayers()
        ]);
    }

    async loadStats() {
        try {
            const response = await fetch(`${this.apiUrl}/admin/dashboard/stats?days=${this.currentPeriod}`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Dashboard stats:', data);

                // Update stat cards
                const totalGames = data.games?.total || 0;
                const uniquePlayers = data.games?.unique_players || 0;
                const totalBets = data.games?.total_bets || 0;
                const houseProfit = data.games?.house_profit || 0;

                document.getElementById('totalGames').textContent = totalGames.toLocaleString();
                document.getElementById('uniquePlayers').textContent = uniquePlayers.toLocaleString();
                document.getElementById('totalBets').textContent = `₿${totalBets.toFixed(2)}`;
                document.getElementById('houseProfit').textContent = `₿${houseProfit.toFixed(2)}`;

                // Update win rate
                const winRate = parseFloat(data.games?.win_rate) || 0;
                const winRateEl = document.getElementById('winRate');
                const winRateCircle = document.querySelector('.win-rate-circle');

                if (winRateEl) {
                    winRateEl.textContent = `${winRate.toFixed(1)}%`;
                }
                if (winRateCircle) {
                    const degrees = winRate * 3.6;
                    winRateCircle.style.background =
                        `conic-gradient(var(--success) ${degrees}deg, var(--bg-tertiary) ${degrees}deg)`;
                }

                console.log('Win rate:', winRate);

                // Update game distribution
                this.renderGameDistribution(data.games?.by_type || [], totalGames);

                // Update transactions
                const transactions = data.transactions || [];
                const deposits = transactions.find(t => t.tx_type === 'DEPOSIT') || { total_amount: 0 };
                const withdraws = transactions.find(t => t.tx_type === 'WITHDRAW') || { total_amount: 0 };

                const totalDepositsEl = document.getElementById('totalDeposits');
                const totalWithdrawsEl = document.getElementById('totalWithdraws');

                if (totalDepositsEl) {
                    totalDepositsEl.textContent = `₿${parseFloat(deposits.total_amount || 0).toFixed(2)}`;
                }
                if (totalWithdrawsEl) {
                    totalWithdrawsEl.textContent = `₿${parseFloat(withdraws.total_amount || 0).toFixed(2)}`;
                }

                console.log('Transactions data:', transactions);
                console.log('Deposits:', deposits, 'Withdraws:', withdraws);
            } else {
                console.error('Stats API error:', response.status);
            }
        } catch (error) {
            console.error('Load stats error:', error);
        }
    }

    renderGameDistribution(gameTypes, total) {
        const container = document.getElementById('gameDistribution');
        if (!container) return;

        console.log('Rendering game distribution:', gameTypes, 'Total:', total);

        // Eğer veri yoksa default göster
        if (!gameTypes || gameTypes.length === 0) {
            // Default oyun tipleri göster (henüz oyun yok)
            gameTypes = [
                { game_type: 'coinflip', count: 0 },
                { game_type: 'roulette', count: 0 },
                { game_type: 'blackjack', count: 0 }
            ];
        }

        const gameNames = {
            'coinflip': '🪙 Coin Flip',
            'roulette': '🎰 Roulette',
            'blackjack': '🃏 Blackjack'
        };

        // Sort by count descending
        gameTypes.sort((a, b) => (b.count || 0) - (a.count || 0));

        container.innerHTML = gameTypes.map(game => {
            const count = parseInt(game.count) || 0;
            const percentage = total > 0 ? (count / total * 100) : 0;
            const minWidth = total === 0 ? 5 : Math.max(percentage, 2);
            return `
                <div class="game-bar">
                    <span class="game-bar-label">${gameNames[game.game_type] || game.game_type}</span>
                    <div class="game-bar-track">
                        <div class="game-bar-fill ${game.game_type}" style="width: ${minWidth}%"></div>
                    </div>
                    <span class="game-bar-value">${count}</span>
                </div>
            `;
        }).join('');
    }

    async loadRecentGames() {
        try {
            const response = await fetch(`${this.apiUrl}/admin/dashboard/recent-games?limit=10`, {
                credentials: 'include'
            });

            if (response.ok) {
                const games = await response.json();
                const tbody = document.getElementById('recentGamesBody');

                if (games.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No games yet</td></tr>';
                    return;
                }

                tbody.innerHTML = games.map(game => `
                    <tr>
                        <td>#${game.game_id}</td>
                        <td>${game.player_email}</td>
                        <td>${this.getGameIcon(game.game_type)} ${game.game_type}</td>
                        <td>₿${parseFloat(game.stake_amount || 0).toFixed(2)}</td>
                        <td>₿${parseFloat(game.win_amount || 0).toFixed(2)}</td>
                        <td><span class="status-badge ${game.outcome?.toLowerCase()}">${game.outcome || '-'}</span></td>
                        <td>${this.formatDate(game.started_at)}</td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Load recent games error:', error);
        }
    }

    async loadTopPlayers() {
        try {
            const response = await fetch(`${this.apiUrl}/admin/dashboard/top-players?days=${this.currentPeriod}`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();

                // Most active
                const activeBody = document.getElementById('topPlayersBody');
                if (data.most_active && data.most_active.length > 0) {
                    activeBody.innerHTML = data.most_active.map((player, i) => `
                        <tr>
                            <td>${this.getRankIcon(i + 1)}</td>
                            <td>${player.email}</td>
                            <td>${player.game_count}</td>
                        </tr>
                    `).join('');
                } else {
                    activeBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">No data</td></tr>';
                }

                // Top winners
                const winnersBody = document.getElementById('topWinnersBody');
                if (data.top_winners && data.top_winners.length > 0) {
                    winnersBody.innerHTML = data.top_winners.map((player, i) => `
                        <tr>
                            <td>${this.getRankIcon(i + 1)}</td>
                            <td>${player.email}</td>
                            <td style="color: ${player.net_profit >= 0 ? 'var(--success)' : 'var(--danger)'}">
                                ${player.net_profit >= 0 ? '+' : ''}₿${parseFloat(player.net_profit || 0).toFixed(2)}
                            </td>
                        </tr>
                    `).join('');
                } else {
                    winnersBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">No data</td></tr>';
                }
            }
        } catch (error) {
            console.error('Load top players error:', error);
        }
    }

    // ========================================
    // Users
    // ========================================

    async loadUsers() {
        try {
            const response = await fetch(`${this.apiUrl}/admin/users`, {
                credentials: 'include'
            });

            if (response.ok) {
                const users = await response.json();
                const tbody = document.getElementById('usersBody');

                tbody.innerHTML = users.map(user => `
                    <tr>
                        <td>#${user.user_id}</td>
                        <td>${user.email}</td>
                        <td>₿${parseFloat(user.balance || 0).toFixed(2)}</td>
                        <td><span class="status-badge ${user.status.toLowerCase()}">${user.status}</span></td>
                        <td>${user.is_admin ? '<span class="admin-badge">ADMIN</span>' : '-'}</td>
                        <td>${this.formatDate(user.created_at)}</td>
                        <td>
                            <div class="action-btns">
                                <button class="action-btn view" onclick="adminPanel.viewUser(${user.user_id})">👁️</button>
                                ${user.status === 'ACTIVE'
                        ? `<button class="action-btn ban" onclick="adminPanel.banUser(${user.user_id})">🚫</button>`
                        : `<button class="action-btn unban" onclick="adminPanel.unbanUser(${user.user_id})">✅</button>`
                    }
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Load users error:', error);
        }
    }

    async viewUser(userId) {
        try {
            // Get user games
            const gamesResponse = await fetch(`${this.apiUrl}/admin/user/${userId}/games?limit=10`, {
                credentials: 'include'
            });
            const games = await gamesResponse.json();

            // Get user from users list (already loaded)
            const usersResponse = await fetch(`${this.apiUrl}/admin/users`, {
                credentials: 'include'
            });
            const users = await usersResponse.json();
            const user = users.find(u => u.user_id === userId);

            if (!user) {
                this.showNotification('User not found!', 'error');
                return;
            }

            // Calculate stats
            let totalBets = 0, totalWins = 0, winCount = 0;
            games.forEach(g => {
                totalBets += parseFloat(g.stake_amount || 0);
                totalWins += parseFloat(g.win_amount || 0);
                if (g.outcome === 'WIN') winCount++;
            });

            const content = `
                <div class="user-detail-header">
                    <div class="user-avatar-large">👤</div>
                    <div class="user-meta">
                        <h3>${user.email}</h3>
                        <p>Kayıt: ${this.formatDate(user.created_at)}</p>
                        <p><span class="status-badge ${user.status.toLowerCase()}">${user.status}</span>
                        ${user.is_admin ? '<span class="admin-badge">ADMIN</span>' : ''}</p>
                    </div>
                </div>
                
                <div class="user-stats-grid">
                    <div class="user-stat">
                        <div class="user-stat-label">Balance</div>
                        <div class="user-stat-value">₿${parseFloat(user.balance || 0).toFixed(2)}</div>
                    </div>
                    <div class="user-stat">
                        <div class="user-stat-label">Total Games</div>
                        <div class="user-stat-value">${games.length}</div>
                    </div>
                    <div class="user-stat">
                        <div class="user-stat-label">Win Rate</div>
                        <div class="user-stat-value">${games.length > 0 ? ((winCount / games.length) * 100).toFixed(1) : 0}%</div>
                    </div>
                </div>
                
                <h4 style="margin: 20px 0 15px; color: var(--text-secondary);">Recent Games</h4>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Game</th>
                                <th>Bet</th>
                                <th>Win</th>
                                <th>Outcome</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${games.length > 0 ? games.map(game => `
                                <tr>
                                    <td>${this.getGameIcon(game.game_type)} ${game.game_type}</td>
                                    <td>₿${parseFloat(game.stake_amount || 0).toFixed(2)}</td>
                                    <td>₿${parseFloat(game.win_amount || 0).toFixed(2)}</td>
                                    <td><span class="status-badge ${game.outcome?.toLowerCase()}">${game.outcome || '-'}</span></td>
                                </tr>
                            `).join('') : '<tr><td colspan="4" style="text-align: center;">No games yet</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `;

            document.getElementById('userDetailContent').innerHTML = content;
            document.getElementById('userDetailModal').classList.remove('hidden');
        } catch (error) {
            console.error('View user error:', error);
            this.showNotification('Could not load user details!', 'error');
        }
    }

    async banUser(userId) {
        if (!confirm('Are you sure you want to ban this user?')) return;

        try {
            const response = await fetch(`${this.apiUrl}/admin/user/${userId}/ban`, {
                method: 'POST',
                headers: this.getSecureHeaders(),
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('User banned!', 'success');
                this.loadUsers();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'Operation failed!', 'error');
            }
        } catch (error) {
            console.error('Ban user error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    async unbanUser(userId) {
        try {
            const response = await fetch(`${this.apiUrl}/admin/user/${userId}/unban`, {
                method: 'POST',
                headers: this.getSecureHeaders(),
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('User unbanned!', 'success');
                this.loadUsers();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'Operation failed!', 'error');
            }
        } catch (error) {
            console.error('Unban user error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    // ========================================
    // Games
    // ========================================

    async loadGames() {
        try {
            const gameType = document.getElementById('gameTypeFilter').value;
            let url = `${this.apiUrl}/admin/dashboard/recent-games?limit=50`;
            if (gameType) {
                url += `&game_type=${gameType}`;
            }

            const response = await fetch(url, {
                credentials: 'include'
            });

            if (response.ok) {
                const games = await response.json();
                const tbody = document.getElementById('gamesBody');

                if (games.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No games found</td></tr>';
                    return;
                }

                tbody.innerHTML = games.map(game => `
                    <tr>
                        <td>#${game.game_id}</td>
                        <td>${game.player_email}</td>
                        <td>${this.getGameIcon(game.game_type)} ${game.game_type}</td>
                        <td>${game.rule_set_name || '-'}</td>
                        <td>₿${parseFloat(game.stake_amount || 0).toFixed(2)}</td>
                        <td>₿${parseFloat(game.win_amount || 0).toFixed(2)}</td>
                        <td><span class="status-badge ${game.outcome?.toLowerCase()}">${game.outcome || '-'}</span></td>
                        <td>${this.formatDate(game.started_at)}</td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Load games error:', error);
        }
    }

    // ========================================
    // Rule Sets
    // ========================================

    async loadRuleSets() {
        try {
            console.log('Loading rule sets...');
            const response = await fetch(`${this.apiUrl}/admin/rule-sets`, {
                credentials: 'include'
            });

            console.log('Rule sets response status:', response.status);

            if (response.ok) {
                const ruleSets = await response.json();
                console.log('Rule sets data:', ruleSets);

                const container = document.getElementById('rulesetsGrid');

                if (!ruleSets || ruleSets.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">No rule sets yet</p>';
                    return;
                }

                // Get rules for each rule set
                const rulePromises = ruleSets.map(rs =>
                    fetch(`${this.apiUrl}/admin/rule-sets/${rs.rule_set_id}`, { credentials: 'include' })
                        .then(r => r.ok ? r.json() : { rules: [] })
                        .catch(() => ({ rules: [] }))
                );

                const rulesData = await Promise.all(rulePromises);
                console.log('Rules data:', rulesData);

                const ruleNames = {
                    'coinflip_payout': '🪙 Coin Flip',
                    'roulette_number_payout': '🎰 Roulette Number',
                    'roulette_color_payout': '🎨 Roulette Color',
                    'roulette_parity_payout': '🔢 Roulette Parity',
                    'blackjack_payout': '🃏 Blackjack',
                    'blackjack_normal_payout': '🃏 BJ Normal'
                };

                container.innerHTML = ruleSets.map((rs, i) => {
                    const rules = rulesData[i]?.rules || [];
                    const houseEdge = rs.house_edge || 5.0;

                    return `
                        <div class="ruleset-card ${rs.is_active ? 'active' : ''}">
                            <div class="ruleset-header">
                                <span class="ruleset-title">${rs.name || 'Unnamed'}</span>
                                <span class="ruleset-status ${rs.is_active ? 'active' : 'inactive'}">
                                    ${rs.is_active ? '✓ ACTIVE' : 'INACTIVE'}
                                </span>
                            </div>
                            <div class="ruleset-info">
                                <p>${rs.description || 'No description'}</p>
                                <span class="house-edge">House Edge: ${houseEdge}%</span>
                            </div>
                            <div class="ruleset-rules">
                                ${rules.length > 0 ? rules.map(rule => `
                                    <div class="rule-item">
                                        <span class="rule-name">${ruleNames[rule.rule_type] || rule.rule_type}</span>
                                        <span class="rule-value">${rule.rule_param}x</span>
                                    </div>
                                `).join('') : '<p style="color: var(--text-secondary); text-align: center;">No rules</p>'}
                            </div>
                            <div class="ruleset-actions">
                                ${!rs.is_active ? `
                                    <button class="btn-success" onclick="adminPanel.activateRuleSet(${rs.rule_set_id})">
                                        ✓ Activate
                                    </button>
                                    <button class="btn-danger" onclick="adminPanel.deleteRuleSet(${rs.rule_set_id}, '${rs.name}')">
                                        🗑️ Delete
                                    </button>
                                ` : `
                                    <button class="btn-secondary" disabled>Active</button>
                                `}
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                console.error('Rule sets API error:', response.status);
                const container = document.getElementById('rulesetsGrid');
                container.innerHTML = '<p style="color: var(--danger); text-align: center; padding: 40px;">Rule setler yüklenemedi</p>';
            }
        } catch (error) {
            console.error('Load rule sets error:', error);
            const container = document.getElementById('rulesetsGrid');
            container.innerHTML = '<p style="color: var(--danger); text-align: center; padding: 40px;">Bağlantı hatası</p>';
        }
    }

    async activateRuleSet(ruleSetId) {
        try {
            const response = await fetch(`${this.apiUrl}/admin/rule-sets/${ruleSetId}/activate`, {
                method: 'POST',
                headers: this.getSecureHeaders(),
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('Rule set activated!', 'success');
                this.loadRuleSets();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'Operation failed!', 'error');
            }
        } catch (error) {
            console.error('Activate rule set error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    async deleteRuleSet(ruleSetId, ruleSetName) {
        if (!confirm(`Are you sure you want to delete rule set "${ruleSetName}"?\n\nThis action cannot be undone!`)) {
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/admin/rule-sets/${ruleSetId}`, {
                method: 'DELETE',
                headers: this.getSecureHeaders(),
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification(data.message || 'Rule set deleted!', 'success');
                this.loadRuleSets();
            } else {
                this.showNotification(data.message || 'Delete failed!', 'error');
            }
        } catch (error) {
            console.error('Delete rule set error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    openRuleSetModal() {
        // Reset form to defaults
        document.getElementById('rsName').value = '';
        document.getElementById('rsDescription').value = '';
        document.getElementById('rsHouseEdge').value = '5';
        document.getElementById('rsCoinflip').value = '1.95';
        document.getElementById('rsRouletteNumber').value = '35';
        document.getElementById('rsRouletteColor').value = '1';
        document.getElementById('rsRouletteParity').value = '1';
        document.getElementById('rsBlackjack').value = '2.5';
        document.getElementById('rsBlackjackNormal').value = '2';

        document.getElementById('ruleSetModal').classList.remove('hidden');
    }

    async createRuleSet() {
        const name = document.getElementById('rsName').value.trim();
        const description = document.getElementById('rsDescription').value.trim();
        const houseEdge = parseFloat(document.getElementById('rsHouseEdge').value);

        if (!name) {
            this.showNotification('Rule set name is required!', 'error');
            return;
        }

        // Collect rule values
        const rules = [
            { rule_type: 'coinflip_payout', rule_param: document.getElementById('rsCoinflip').value },
            { rule_type: 'roulette_number_payout', rule_param: document.getElementById('rsRouletteNumber').value },
            { rule_type: 'roulette_color_payout', rule_param: document.getElementById('rsRouletteColor').value },
            { rule_type: 'roulette_parity_payout', rule_param: document.getElementById('rsRouletteParity').value },
            { rule_type: 'blackjack_payout', rule_param: document.getElementById('rsBlackjack').value },
            { rule_type: 'blackjack_normal_payout', rule_param: document.getElementById('rsBlackjackNormal').value }
        ];

        try {
            // 1. Create rule set
            const rsResponse = await fetch(`${this.apiUrl}/admin/rule-sets`, {
                method: 'POST',
                headers: this.getSecureHeaders(),
                credentials: 'include',
                body: JSON.stringify({ name, description, house_edge: houseEdge })
            });

            if (!rsResponse.ok) {
                const data = await rsResponse.json();
                this.showNotification(data.message || 'Rule set could not be created!', 'error');
                return;
            }

            const rsData = await rsResponse.json();
            const ruleSetId = rsData.rule_set_id;

            // 2. Add each rule
            let successCount = 0;
            for (const rule of rules) {
                const ruleResponse = await fetch(`${this.apiUrl}/admin/rule-sets/${ruleSetId}/rules`, {
                    method: 'POST',
                    headers: this.getSecureHeaders(),
                    credentials: 'include',
                    body: JSON.stringify(rule)
                });

                if (ruleResponse.ok) {
                    successCount++;
                } else {
                    console.error(`Failed to add rule: ${rule.rule_type}`);
                }
            }

            // 3. Close modal and refresh
            document.getElementById('ruleSetModal').classList.add('hidden');
            this.showNotification(`Rule set "${name}" created! (${successCount} rules added)`, 'success');
            this.loadRuleSets();

        } catch (error) {
            console.error('Create rule set error:', error);
            this.showNotification('Connection error!', 'error');
        }
    }

    // ========================================
    // Transactions
    // ========================================

    async loadTransactions() {
        // Stats are already loaded in dashboard
        await this.loadStats();
    }

    // ========================================
    // Utilities
    // ========================================

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getGameIcon(gameType) {
        const icons = {
            'coinflip': '🪙',
            'roulette': '🎰',
            'blackjack': '🃏'
        };
        return icons[gameType] || '🎮';
    }

    getRankIcon(rank) {
        const icons = { 1: '🥇', 2: '🥈', 3: '🥉' };
        return icons[rank] || `#${rank}`;
    }

    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        const text = document.getElementById('notificationText');

        notification.className = `notification ${type}`;
        text.textContent = message;

        setTimeout(() => {
            notification.classList.add('hidden');
        }, 3000);
    }
}

// Close user modal
function closeUserModal() {
    document.getElementById('userDetailModal').classList.add('hidden');
}

// Close rule set modal
function closeRuleSetModal() {
    document.getElementById('ruleSetModal').classList.add('hidden');
}

// Hide notification
function hideNotification() {
    document.getElementById('notification').classList.add('hidden');
}

// Initialize
const adminPanel = new AdminPanel();

