class CoinFlipGame {
    constructor() {
        this.apiUrl = 'http://localhost:3001';
        this.currentUser = null;
        this.balance = 0;
        this.gameHistory = [];
        this.isPlaying = false;

        this.initializeElements();
        this.bindEvents();
        this.checkAuthStatus();
    }

    initializeElements() {
        // Auth elements
        this.authModal = document.getElementById('authModal');
        this.loginBtn = document.getElementById('loginBtn');
        this.registerBtn = document.getElementById('registerBtn');
        this.loginForm = document.getElementById('loginForm');
        this.registerForm = document.getElementById('registerForm');
        this.showRegisterLink = document.getElementById('showRegister');
        this.showLoginLink = document.getElementById('showLogin');
        this.closeButtons = document.querySelectorAll('.close');

        // Game elements
        this.coin = document.getElementById('coin');
        this.gameControls = document.getElementById('gameControls');
        this.gameResult = document.getElementById('gameResult');
        this.betSlider = document.getElementById('betSlider');
        this.betAmount = document.getElementById('betAmount');
        this.chooseHeadsBtn = document.getElementById('chooseHeads');
        this.chooseTailsBtn = document.getElementById('chooseTails');
        this.playBtn = document.getElementById('playBtn');
        this.btnText = this.playBtn.querySelector('.btn-text');
        this.btnLoading = this.playBtn.querySelector('.btn-loading');

        // User info elements
        this.userSection = document.getElementById('userSection');
        this.balance = document.getElementById('balance');
        this.walletControls = document.getElementById('walletControls');
        this.recentGames = document.getElementById('recentGames');
        this.gameHistory = document.getElementById('gameHistory');

        // Wallet elements
        this.walletModal = document.getElementById('walletModal');
        this.depositBtn = document.getElementById('depositBtn');
        this.withdrawBtn = document.getElementById('withdrawBtn');
        this.logoutBtn = document.getElementById('logoutBtn');
        this.walletForm = document.getElementById('walletFormElement');
        this.walletTitle = document.getElementById('walletTitle');
        this.walletAmount = document.getElementById('walletAmount');
        this.walletSubmitBtn = document.getElementById('walletSubmitBtn');

        // Notification
        this.notification = document.getElementById('notification');
    }

    bindEvents() {
        // Auth events
        this.loginBtn.addEventListener('click', () => this.showAuthModal('login'));
        this.registerBtn.addEventListener('click', () => this.showAuthModal('register'));
        this.showRegisterLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showAuthModal('register');
        });
        this.showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showAuthModal('login');
        });

        // Close modal events
        this.closeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.add('hidden');
            });
        });

        // Click outside modal to close
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.add('hidden');
            }
        });

        // Form submissions
        document.getElementById('loginFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });

        document.getElementById('registerFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.register();
        });

        // Game events
        this.betSlider.addEventListener('input', () => {
            this.betAmount.value = this.betSlider.value;
        });

        this.betAmount.addEventListener('input', () => {
            this.betSlider.value = this.betAmount.value;
        });

        this.chooseHeadsBtn.addEventListener('click', () => this.selectChoice('yazi'));
        this.chooseTailsBtn.addEventListener('click', () => this.selectChoice('tura'));
        this.playBtn.addEventListener('click', () => this.playGame());

        // Wallet events
        this.depositBtn.addEventListener('click', () => this.showWalletModal('deposit'));
        this.withdrawBtn.addEventListener('click', () => this.showWalletModal('withdraw'));
        this.logoutBtn.addEventListener('click', () => this.logout());
        this.walletForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleWalletTransaction();
        });

        // Coin hover effect
        this.coin.addEventListener('mouseenter', () => {
            if (!this.isPlaying) {
                this.coin.style.transform = 'rotateY(15deg) rotateX(5deg) scale(1.05)';
            }
        });

        this.coin.addEventListener('mouseleave', () => {
            if (!this.isPlaying) {
                this.coin.style.transform = '';
            }
        });

        // Notification close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('notification-close')) {
                this.hideNotification();
            }
        });
    }

    async checkAuthStatus() {
        try {
            const response = await fetch(`${this.apiUrl}/wallets/me`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.currentUser = data.wallet.email;
                this.updateBalance(data.wallet.balance);
                this.showGameInterface();
            } else {
                this.showAuthInterface();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showAuthInterface();
        }
    }

    showAuthModal(type) {
        this.authModal.classList.remove('hidden');
        if (type === 'login') {
            this.loginForm.classList.remove('hidden');
            this.registerForm.classList.add('hidden');
        } else {
            this.loginForm.classList.add('hidden');
            this.registerForm.classList.remove('hidden');
        }
    }

    async login() {
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch(`${this.apiUrl}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.currentUser = email;
                this.authModal.classList.add('hidden');
                this.showNotification('Giriş başarılı!', 'success');
                await this.loadWalletInfo();
                this.showGameInterface();
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async register() {
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;

        try {
            const response = await fetch(`${this.apiUrl}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Kayıt başarılı! Giriş yapabilirsiniz.', 'success');
                this.showAuthModal('login');
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async logout() {
        try {
            await fetch(`${this.apiUrl}/logout`, {
                method: 'POST',
                credentials: 'include'
            });

            this.currentUser = null;
            this.balance = 0;
            this.gameHistory = [];
            this.showAuthInterface();
            this.showNotification('Çıkış yapıldı!', 'info');
        } catch (error) {
            this.showNotification('Çıkış hatası!', 'error');
        }
    }

    async loadWalletInfo() {
        try {
            const response = await fetch(`${this.apiUrl}/wallets/me`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.updateBalance(data.wallet.balance);
                this.updateBetLimits();
            }
        } catch (error) {
            console.error('Wallet info load failed:', error);
        }
    }

    showAuthInterface() {
        this.userSection.innerHTML = `
            <button id="loginBtn" class="btn btn-secondary">Giriş Yap</button>
            <button id="registerBtn" class="btn btn-secondary">Kayıt Ol</button>
        `;
        this.gameControls.classList.add('hidden');
        this.walletControls.classList.add('hidden');
        this.recentGames.classList.add('hidden');
        this.gameResult.classList.add('hidden');

        // Re-bind events for new buttons
        document.getElementById('loginBtn').addEventListener('click', () => this.showAuthModal('login'));
        document.getElementById('registerBtn').addEventListener('click', () => this.showAuthModal('register'));
    }

    showGameInterface() {
        this.userSection.innerHTML = `
            <div style="color: white; font-weight: 600;">Hoş geldin, ${this.currentUser}</div>
        `;
        this.gameControls.classList.remove('hidden');
        this.walletControls.classList.remove('hidden');
        this.recentGames.classList.remove('hidden');
    }

    updateBalance(newBalance) {
        this.balance = newBalance;
        document.getElementById('balance').textContent = `💰 ${newBalance.toFixed(2)} VIRTUAL`;
        this.updateBetLimits();
    }

    updateBetLimits() {
        const maxBet = Math.floor(this.balance);
        this.betSlider.max = maxBet;
        this.betAmount.max = maxBet;

        if (parseInt(this.betAmount.value) > maxBet) {
            this.betAmount.value = Math.max(1, maxBet);
            this.betSlider.value = this.betAmount.value;
        }
    }

    selectChoice(choice) {
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.classList.remove('selected');
        });

        if (choice === 'yazi') {
            this.chooseHeadsBtn.classList.add('selected');
        } else {
            this.chooseTailsBtn.classList.add('selected');
        }

        this.selectedChoice = choice;
        this.updatePlayButton();
    }

    updatePlayButton() {
        const hasChoice = this.selectedChoice;
        const hasValidBet = this.betAmount.value > 0 && this.betAmount.value <= this.balance;

        this.playBtn.disabled = !(hasChoice && hasValidBet) || this.isPlaying;
    }

    async playGame() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.playBtn.disabled = true;
        this.btnText.classList.add('hidden');
        this.btnLoading.classList.remove('hidden');
        this.gameResult.classList.add('hidden');

        // Start coin flip animation
        this.startCoinAnimation();

        try {
            const response = await fetch(`${this.apiUrl}/game/play`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    amount: parseFloat(this.betAmount.value),
                    choice: this.selectedChoice
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Show result after animation completes
                setTimeout(() => {
                    this.showGameResult(data);
                    this.updateBalance(data.new_balance);
                    this.addToHistory(data);
                    this.resetGame();
                }, 3000);
            } else {
                this.showNotification(data.message, 'error');
                this.resetGame();
            }
        } catch (error) {
            this.showNotification('Oyun hatası!', 'error');
            this.resetGame();
        }
    }

    startCoinAnimation() {
        this.coin.classList.remove('flipping-heads', 'flipping-tails');

        // Add appropriate animation class based on future result
        // For now, we'll use a random animation since we don't know the result yet
        const randomAnimation = Math.random() > 0.5 ? 'flipping-heads' : 'flipping-tails';

        setTimeout(() => {
            this.coin.classList.add(randomAnimation);
        }, 100);
    }

    showGameResult(data) {
        const resultText = this.gameResult.querySelector('.result-text');
        const resultDetails = this.gameResult.querySelector('.result-details');

        const isWin = data.message.includes('KAZANDINIZ');

        resultText.textContent = isWin ? '🎉 KAZANDIN!' : '😔 KAYBETTİN!';
        resultText.className = `result-text ${isWin ? 'win' : 'lose'}`;

        resultDetails.innerHTML = `
            <div>Seçimin: ${data.your_choice.toUpperCase()}</div>
            <div>Sonuç: ${data.result.toUpperCase()}</div>
            <div>Yeni bakiye: ${data.new_balance.toFixed(2)} VIRTUAL</div>
        `;

        this.gameResult.classList.remove('hidden');

        // Update coin to show final result
        this.coin.classList.remove('flipping-heads', 'flipping-tails');
        if (data.result === 'yazi') {
            this.coin.style.transform = 'rotateY(0deg)';
        } else {
            this.coin.style.transform = 'rotateY(180deg)';
        }
    }

    addToHistory(data) {
        const isWin = data.message.includes('KAZANDINIZ');
        const icon = document.createElement('div');
        icon.className = `game-result-icon ${isWin ? 'win' : 'lose'}`;
        icon.textContent = data.result === 'yazi' ? '🪙' : '🌟';
        icon.title = `${data.your_choice} seçtin, ${data.result} geldi - ${isWin ? 'Kazandın' : 'Kaybettin'}`;

        this.gameHistory.insertBefore(icon, this.gameHistory.firstChild);

        // Keep only last 10 games
        while (this.gameHistory.children.length > 10) {
            this.gameHistory.removeChild(this.gameHistory.lastChild);
        }
    }

    resetGame() {
        this.isPlaying = false;
        this.btnText.classList.remove('hidden');
        this.btnLoading.classList.add('hidden');
        this.updatePlayButton();

        // Reset coin animation classes after a delay
        setTimeout(() => {
            this.coin.classList.remove('flipping-heads', 'flipping-tails');
        }, 500);
    }

    showWalletModal(type) {
        this.walletModal.classList.remove('hidden');
        this.walletTitle.textContent = type === 'deposit' ? 'Para Yatır' : 'Para Çek';
        this.walletSubmitBtn.textContent = type === 'deposit' ? 'Yatır' : 'Çek';
        this.walletType = type;
        this.walletAmount.value = '';
        this.walletAmount.focus();
    }

    async handleWalletTransaction() {
        const amount = parseFloat(this.walletAmount.value);
        const endpoint = this.walletType === 'deposit' ? '/wallets/me/deposit' : '/wallets/me/withdraw';

        try {
            const response = await fetch(`${this.apiUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ amount })
            });

            const data = await response.json();

            if (response.ok) {
                this.updateBalance(data.new_balance);
                this.walletModal.classList.add('hidden');
                this.showNotification(data.message, 'success');
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('İşlem hatası!', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notificationMessage = this.notification.querySelector('.notification-message');
        notificationMessage.textContent = message;

        this.notification.className = `notification ${type}`;
        this.notification.classList.remove('hidden');

        // Auto hide after 5 seconds
        setTimeout(() => {
            this.hideNotification();
        }, 5000);
    }

    hideNotification() {
        this.notification.classList.add('hidden');
    }
}

// Initialize the game when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CoinFlipGame();
});