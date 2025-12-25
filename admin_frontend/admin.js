/**
 * OddCity Admin Panel - JavaScript
 */

class AdminPanel {
    constructor() {
        this.apiUrl = window.location.origin;
        this.isLoggedIn = false;
        this.currentPage = 'dashboard';
        this.currentPeriod = 7;
        
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
                    document.getElementById('loginModal').classList.add('hidden');
                    document.getElementById('adminEmail').textContent = user.email;
                } else {
                    this.showNotification('Admin yetkisi gerekli!', 'error');
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
                    document.getElementById('loginModal').classList.add('hidden');
                    document.getElementById('adminEmail').textContent = email;
                    this.showNotification('Giriş başarılı!', 'success');
                    this.loadDashboard();
                } else {
                    this.showNotification('Admin yetkisi gerekli!', 'error');
                }
            } else {
                this.showNotification(data.message || 'Giriş başarısız!', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async logout() {
        try {
            await fetch(`${this.apiUrl}/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        this.isLoggedIn = false;
        document.getElementById('loginModal').classList.remove('hidden');
        this.showNotification('Çıkış yapıldı', 'success');
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
                const winRate = data.games?.win_rate || 0;
                document.getElementById('winRate').textContent = `${winRate.toFixed(1)}%`;
                document.querySelector('.win-rate-circle').style.background = 
                    `conic-gradient(var(--success) ${winRate * 3.6}deg, var(--bg-primary) ${winRate * 3.6}deg)`;

                // Update game distribution
                this.renderGameDistribution(data.games?.by_type || [], totalGames);

                // Update transactions
                if (data.transactions) {
                    const deposits = data.transactions.find(t => t.tx_type === 'DEPOSIT') || { total_amount: 0 };
                    const withdraws = data.transactions.find(t => t.tx_type === 'WITHDRAW') || { total_amount: 0 };
                    document.getElementById('totalDeposits').textContent = `₿${parseFloat(deposits.total_amount || 0).toFixed(2)}`;
                    document.getElementById('totalWithdraws').textContent = `₿${parseFloat(withdraws.total_amount || 0).toFixed(2)}`;
                }
            } else {
                console.error('Stats API error:', response.status);
            }
        } catch (error) {
            console.error('Load stats error:', error);
        }
    }

    renderGameDistribution(gameTypes, total) {
        const container = document.getElementById('gameDistribution');
        
        // Eğer veri yoksa default göster
        if (!gameTypes || gameTypes.length === 0) {
            // Default oyun tipleri göster (henüz oyun yok)
            const defaultGames = [
                { game_type: 'coinflip', count: 0 },
                { game_type: 'roulette', count: 0 },
                { game_type: 'blackjack', count: 0 }
            ];
            gameTypes = defaultGames;
        }

        const gameNames = {
            'coinflip': '🪙 Coin Flip',
            'roulette': '🎰 Roulette',
            'blackjack': '🃏 Blackjack'
        };

        container.innerHTML = gameTypes.map(game => {
            const count = game.count || 0;
            const percentage = total > 0 ? (count / total * 100) : 0;
            return `
                <div class="game-bar">
                    <span class="game-bar-label">${gameNames[game.game_type] || game.game_type}</span>
                    <div class="game-bar-track">
                        <div class="game-bar-fill ${game.game_type}" style="width: ${Math.max(percentage, 2)}%"></div>
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
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">Henüz oyun yok</td></tr>';
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
                    activeBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">Veri yok</td></tr>';
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
                    winnersBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">Veri yok</td></tr>';
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
                this.showNotification('Kullanıcı bulunamadı!', 'error');
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
                        <div class="user-stat-label">Bakiye</div>
                        <div class="user-stat-value">₿${parseFloat(user.balance || 0).toFixed(2)}</div>
                    </div>
                    <div class="user-stat">
                        <div class="user-stat-label">Toplam Oyun</div>
                        <div class="user-stat-value">${games.length}</div>
                    </div>
                    <div class="user-stat">
                        <div class="user-stat-label">Kazanma Oranı</div>
                        <div class="user-stat-value">${games.length > 0 ? ((winCount / games.length) * 100).toFixed(1) : 0}%</div>
                    </div>
                </div>
                
                <h4 style="margin: 20px 0 15px; color: var(--text-secondary);">Son Oyunlar</h4>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Oyun</th>
                                <th>Bahis</th>
                                <th>Kazanç</th>
                                <th>Sonuç</th>
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
                            `).join('') : '<tr><td colspan="4" style="text-align: center;">Henüz oyun yok</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `;

            document.getElementById('userDetailContent').innerHTML = content;
            document.getElementById('userDetailModal').classList.remove('hidden');
        } catch (error) {
            console.error('View user error:', error);
            this.showNotification('Kullanıcı bilgileri yüklenemedi!', 'error');
        }
    }

    async banUser(userId) {
        if (!confirm('Bu kullanıcıyı yasaklamak istediğinizden emin misiniz?')) return;

        try {
            const response = await fetch(`${this.apiUrl}/admin/user/${userId}/ban`, {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('Kullanıcı yasaklandı!', 'success');
                this.loadUsers();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'İşlem başarısız!', 'error');
            }
        } catch (error) {
            console.error('Ban user error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async unbanUser(userId) {
        try {
            const response = await fetch(`${this.apiUrl}/admin/user/${userId}/unban`, {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('Kullanıcı yasağı kaldırıldı!', 'success');
                this.loadUsers();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'İşlem başarısız!', 'error');
            }
        } catch (error) {
            console.error('Unban user error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
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
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">Oyun bulunamadı</td></tr>';
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
                    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">Henüz rule set yok</p>';
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
                                <span class="ruleset-title">${rs.name || 'İsimsiz'}</span>
                                <span class="ruleset-status ${rs.is_active ? 'active' : 'inactive'}">
                                    ${rs.is_active ? '✓ AKTİF' : 'PASİF'}
                                </span>
                            </div>
                            <div class="ruleset-info">
                                <p>${rs.description || 'Açıklama yok'}</p>
                                <span class="house-edge">Ev Avantajı: ${houseEdge}%</span>
                            </div>
                            <div class="ruleset-rules">
                                ${rules.length > 0 ? rules.map(rule => `
                                    <div class="rule-item">
                                        <span class="rule-name">${ruleNames[rule.rule_type] || rule.rule_type}</span>
                                        <span class="rule-value">${rule.rule_param}x</span>
                                    </div>
                                `).join('') : '<p style="color: var(--text-secondary); text-align: center;">Kural yok</p>'}
                            </div>
                            <div class="ruleset-actions">
                                ${!rs.is_active ? `
                                    <button class="btn-success" onclick="adminPanel.activateRuleSet(${rs.rule_set_id})">
                                        ✓ Aktif Et
                                    </button>
                                ` : `
                                    <button class="btn-secondary" disabled>Aktif</button>
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
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification('Rule set aktif edildi!', 'success');
                this.loadRuleSets();
            } else {
                const data = await response.json();
                this.showNotification(data.message || 'İşlem başarısız!', 'error');
            }
        } catch (error) {
            console.error('Activate rule set error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
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

// Hide notification
function hideNotification() {
    document.getElementById('notification').classList.add('hidden');
}

// Initialize
const adminPanel = new AdminPanel();

