class GameManager {
    constructor() {
        this.apiUrl = '';
        this.currentUser = null;
        this.balance = 0;
        this.activeGame = 'coinflip'; // Default game

        this.initializeElements();
        this.bindEvents();
        this.checkAuthStatus();

        // Initialize Games
        this.coinFlipGame = new CoinFlipGame(this);
        this.rouletteGame = new RouletteGame(this);
        this.blackjackGame = new BlackjackGame(this);
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

        // User info elements
        this.userSection = document.getElementById('userSection');
        this.balanceDisplay = document.getElementById('balance');
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

        // Game Switcher
        this.gameTabs = document.querySelectorAll('.game-tab');
        this.coinflipContainer = document.getElementById('coinflipGame');
        this.rouletteContainer = document.getElementById('rouletteGame');
        this.blackjackContainer = document.getElementById('blackjackGame');
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

        // Wallet events
        this.depositBtn.addEventListener('click', () => this.showWalletModal('deposit'));
        this.withdrawBtn.addEventListener('click', () => this.showWalletModal('withdraw'));
        this.logoutBtn.addEventListener('click', () => this.logout());
        this.walletForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleWalletTransaction();
        });

        // Notification close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('notification-close')) {
                this.hideNotification();
            }
        });

        // Game Switcher
        this.gameTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const gameName = tab.dataset.game;
                this.switchGame(gameName);
            });
        });
    }

    switchGame(gameName) {
        this.activeGame = gameName;

        // Update Tabs
        this.gameTabs.forEach(tab => {
            if (tab.dataset.game === gameName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Update Containers
        this.coinflipContainer.classList.add('hidden');
        this.rouletteContainer.classList.add('hidden');
        this.blackjackContainer.classList.add('hidden');

        if (gameName === 'coinflip') {
            this.coinflipContainer.classList.remove('hidden');
        } else if (gameName === 'roulette') {
            this.rouletteContainer.classList.remove('hidden');
        } else if (gameName === 'blackjack') {
            this.blackjackContainer.classList.remove('hidden');
        }
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
            this.gameHistory.innerHTML = '';
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
        this.coinflipContainer.querySelector('.betting-controls').classList.add('hidden');
        this.rouletteContainer.querySelector('.betting-controls').classList.add('hidden');
        this.blackjackContainer.querySelector('.betting-controls').classList.add('hidden');
        this.walletControls.classList.add('hidden');
        this.recentGames.classList.add('hidden');

        // Re-bind events for new buttons
        document.getElementById('loginBtn').addEventListener('click', () => this.showAuthModal('login'));
        document.getElementById('registerBtn').addEventListener('click', () => this.showAuthModal('register'));
    }

    showGameInterface() {
        this.userSection.innerHTML = `
            <div style="color: white; font-weight: 600;">Hoş geldin, ${this.currentUser}</div>
        `;
        this.coinflipContainer.querySelector('.betting-controls').classList.remove('hidden');
        this.rouletteContainer.querySelector('.betting-controls').classList.remove('hidden');
        this.blackjackContainer.querySelector('.betting-controls').classList.remove('hidden');
        this.walletControls.classList.remove('hidden');
        this.recentGames.classList.remove('hidden');
    }

    updateBalance(newBalance) {
        this.balance = newBalance;
        this.balanceDisplay.textContent = `💰 ${newBalance.toFixed(2)} VIRTUAL`;
        this.coinFlipGame.updateBetLimits();
        this.rouletteGame.updateBetLimits();
        this.blackjackGame.updateBetLimits();
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

        setTimeout(() => {
            this.hideNotification();
        }, 5000);
    }

    hideNotification() {
        this.notification.classList.add('hidden');
    }

    addToHistory(icon, title, isWin) {
        const iconDiv = document.createElement('div');
        iconDiv.className = `game-result-icon ${isWin ? 'win' : 'lose'}`;
        iconDiv.textContent = icon;
        iconDiv.title = title;

        this.gameHistory.insertBefore(iconDiv, this.gameHistory.firstChild);

        while (this.gameHistory.children.length > 10) {
            this.gameHistory.removeChild(this.gameHistory.lastChild);
        }
    }
}

class CoinFlipGame {
    constructor(gameManager) {
        this.gm = gameManager;
        this.isPlaying = false;
        this.selectedChoice = null;

        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.coin = document.getElementById('coin');
        this.gameResult = document.getElementById('gameResult');
        this.betSlider = document.getElementById('betSlider');
        this.betAmount = document.getElementById('betAmount');
        this.chooseHeadsBtn = document.getElementById('chooseHeads');
        this.chooseTailsBtn = document.getElementById('chooseTails');
        this.playBtn = document.getElementById('playBtn');
        this.btnText = this.playBtn.querySelector('.btn-text');
        this.btnLoading = this.playBtn.querySelector('.btn-loading');
    }

    bindEvents() {
        this.betSlider.addEventListener('input', () => {
            this.betAmount.value = this.betSlider.value;
        });

        this.betAmount.addEventListener('input', () => {
            this.betSlider.value = this.betAmount.value;
        });

        this.chooseHeadsBtn.addEventListener('click', () => this.selectChoice('yazi'));
        this.chooseTailsBtn.addEventListener('click', () => this.selectChoice('tura'));
        this.playBtn.addEventListener('click', () => this.playGame());

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
    }

    updateBetLimits() {
        const maxBet = Math.floor(this.gm.balance);
        this.betSlider.max = maxBet;
        this.betAmount.max = maxBet;

        if (parseInt(this.betAmount.value) > maxBet) {
            this.betAmount.value = Math.max(1, maxBet);
            this.betSlider.value = this.betAmount.value;
        }
    }

    selectChoice(choice) {
        this.chooseHeadsBtn.classList.remove('selected');
        this.chooseTailsBtn.classList.remove('selected');

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
        const hasValidBet = this.betAmount.value > 0 && this.betAmount.value <= this.gm.balance;
        this.playBtn.disabled = !(hasChoice && hasValidBet) || this.isPlaying;
    }

    async playGame() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.playBtn.disabled = true;
        this.btnText.classList.add('hidden');
        this.btnLoading.classList.remove('hidden');
        this.gameResult.classList.add('hidden');

        this.startCoinAnimation();

        try {
            const response = await fetch(`${this.gm.apiUrl}/game/play`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    amount: parseFloat(this.betAmount.value),
                    choice: this.selectedChoice
                })
            });

            const data = await response.json();

            if (response.ok) {
                setTimeout(() => {
                    this.showGameResult(data);
                    this.gm.updateBalance(data.new_balance);
                    this.gm.addToHistory(
                        data.result === 'yazi' ? '🪙' : '🌟',
                        `${data.your_choice} seçtin, ${data.result} geldi - ${data.message}`,
                        data.message.includes('KAZANDINIZ')
                    );
                    this.resetGame();
                }, 3000);
            } else {
                this.gm.showNotification(data.message, 'error');
                this.resetGame();
            }
        } catch (error) {
            this.gm.showNotification('Oyun hatası!', 'error');
            this.resetGame();
        }
    }

    startCoinAnimation() {
        this.coin.classList.remove('flipping-heads', 'flipping-tails');
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

        this.coin.classList.remove('flipping-heads', 'flipping-tails');
        if (data.result === 'yazi') {
            this.coin.style.transform = 'rotateY(0deg)';
        } else {
            this.coin.style.transform = 'rotateY(180deg)';
        }
    }

    resetGame() {
        this.isPlaying = false;
        this.btnText.classList.remove('hidden');
        this.btnLoading.classList.add('hidden');
        this.updatePlayButton();
        setTimeout(() => {
            this.coin.classList.remove('flipping-heads', 'flipping-tails');
        }, 500);
    }
}

class RouletteGame {
    constructor(gameManager) {
        this.gm = gameManager;
        this.isPlaying = false;
        this.selectedBet = null; // { type: 'number'|'color'|'parity', value: ... }

        this.initializeElements();
        this.generateBoard();
        this.bindEvents();
    }

    initializeElements() {
        this.wheel = document.getElementById('rouletteWheel');
        this.ball = document.getElementById('rouletteBall');
        this.gameResult = document.getElementById('rouletteResult');
        this.betSlider = document.getElementById('rouletteBetSlider');
        this.betAmount = document.getElementById('rouletteBetAmount');
        this.spinBtn = document.getElementById('spinBtn');
        this.btnText = this.spinBtn.querySelector('.btn-text');
        this.btnLoading = this.spinBtn.querySelector('.btn-loading');
        this.boardNumbers = document.getElementById('boardNumbers');
        this.selectedBetInfo = document.getElementById('selectedBetInfo');
        this.betSelectionText = document.getElementById('betSelectionText');
    }

    generateBoard() {
        const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34];

        // 0 Button
        const btn0 = document.createElement('button');
        btn0.className = 'board-btn green';
        btn0.textContent = '0';
        btn0.dataset.type = 'number';
        btn0.dataset.value = '0';
        btn0.style.gridColumn = 'span 6';
        this.boardNumbers.appendChild(btn0);

        // 1-36 Buttons
        for (let i = 1; i <= 36; i++) {
            const btn = document.createElement('button');
            const isRed = redNumbers.includes(i);
            btn.className = `board-btn ${isRed ? 'red' : 'black'}`;
            btn.textContent = i;
            btn.dataset.type = 'number';
            btn.dataset.value = i;
            this.boardNumbers.appendChild(btn);
        }
    }

    bindEvents() {
        this.betSlider.addEventListener('input', () => {
            this.betAmount.value = this.betSlider.value;
        });

        this.betAmount.addEventListener('input', () => {
            this.betSlider.value = this.betAmount.value;
        });

        // Board clicks
        document.querySelectorAll('.roulette-board .board-btn').forEach(btn => {
            btn.addEventListener('click', () => this.selectBet(btn));
        });

        this.spinBtn.addEventListener('click', () => this.playGame());
    }

    updateBetLimits() {
        const maxBet = Math.floor(this.gm.balance);
        this.betSlider.max = maxBet;
        this.betAmount.max = maxBet;

        if (parseInt(this.betAmount.value) > maxBet) {
            this.betAmount.value = Math.max(1, maxBet);
            this.betSlider.value = this.betAmount.value;
        }
    }

    selectBet(btn) {
        document.querySelectorAll('.roulette-board .board-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        this.selectedBet = {
            type: btn.dataset.type,
            value: btn.dataset.value
        };

        this.selectedBetInfo.classList.remove('hidden');
        let displayText = '';
        if (this.selectedBet.type === 'number') displayText = `Sayı ${this.selectedBet.value}`;
        else if (this.selectedBet.type === 'color') displayText = this.selectedBet.value === 'red' ? 'Kırmızı' : 'Siyah';
        else displayText = this.selectedBet.value === 'odd' ? 'Tek' : 'Çift';

        this.betSelectionText.textContent = displayText;
        this.updateSpinButton();
    }

    updateSpinButton() {
        const hasBet = this.selectedBet;
        const hasValidAmount = this.betAmount.value > 0 && this.betAmount.value <= this.gm.balance;
        this.spinBtn.disabled = !(hasBet && hasValidAmount) || this.isPlaying;
    }

    async playGame() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.spinBtn.disabled = true;
        this.btnText.classList.add('hidden');
        this.btnLoading.classList.remove('hidden');
        this.gameResult.classList.add('hidden');

        // Spin Animation
        const randomRotation = 720 + Math.random() * 360;
        this.wheel.style.transform = `rotate(${randomRotation}deg)`;

        // Ball Animation (Simplified)
        this.ball.style.transform = `translate(-50%, -135px) rotate(-${randomRotation * 2}deg)`;

        try {
            const response = await fetch(`${this.gm.apiUrl}/game/roulette/play`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    amount: parseFloat(this.betAmount.value),
                    bet_type: this.selectedBet.type,
                    bet_value: this.selectedBet.value
                })
            });

            const data = await response.json();

            if (response.ok) {
                setTimeout(() => {
                    this.showGameResult(data);
                    this.gm.updateBalance(data.new_balance);
                    this.gm.addToHistory(
                        '🎡',
                        `${this.betSelectionText.textContent} oynadın, ${data.winning_number} (${data.winning_color}) geldi - ${data.message}`,
                        data.is_win
                    );
                    this.resetGame();
                }, 3000); // Wait for animation
            } else {
                this.gm.showNotification(data.message, 'error');
                this.resetGame();
            }
        } catch (error) {
            this.gm.showNotification('Oyun hatası!', 'error');
            this.resetGame();
        }
    }

    showGameResult(data) {
        const resultText = this.gameResult.querySelector('.result-text');
        const resultDetails = this.gameResult.querySelector('.result-details');

        resultText.textContent = data.is_win ? '🎉 KAZANDIN!' : '😔 KAYBETTİN!';
        resultText.className = `result-text ${data.is_win ? 'win' : 'lose'}`;

        resultDetails.innerHTML = `
            <div>Gelen: <span style="color:${data.winning_color}; font-weight:bold;">${data.winning_number}</span></div>
            <div>Kazanç: ${data.payout.toFixed(2)} VIRTUAL</div>
        `;

        this.gameResult.classList.remove('hidden');
    }

    resetGame() {
        this.isPlaying = false;
        this.btnText.classList.remove('hidden');
        this.btnLoading.classList.add('hidden');
        this.updateSpinButton();
    }
}

class BlackjackGame {
    constructor(gameManager) {
        this.gm = gameManager;
        this.isPlaying = false;

        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.dealerCards = document.getElementById('dealerCards');
        this.playerCards = document.getElementById('playerCards');
        this.dealerScore = document.getElementById('dealerScore');
        this.playerScore = document.getElementById('playerScore');
        this.bjMessage = document.getElementById('bjMessage');

        this.betSlider = document.getElementById('bjBetSlider');
        this.betAmount = document.getElementById('bjBetAmount');
        this.betArea = document.getElementById('bjBetArea');

        this.dealBtn = document.getElementById('dealBtn');
        this.btnText = this.dealBtn.querySelector('.btn-text');
        this.btnLoading = this.dealBtn.querySelector('.btn-loading');

        this.bjActions = document.getElementById('bjActions');
        this.hitBtn = document.getElementById('hitBtn');
        this.standBtn = document.getElementById('standBtn');
    }

    bindEvents() {
        this.betSlider.addEventListener('input', () => {
            this.betAmount.value = this.betSlider.value;
        });

        this.betAmount.addEventListener('input', () => {
            this.betSlider.value = this.betAmount.value;
        });

        this.dealBtn.addEventListener('click', () => this.startGame());
        this.hitBtn.addEventListener('click', () => this.hit());
        this.standBtn.addEventListener('click', () => this.stand());
    }

    updateBetLimits() {
        const maxBet = Math.floor(this.gm.balance);
        this.betSlider.max = maxBet;
        this.betAmount.max = maxBet;

        if (parseInt(this.betAmount.value) > maxBet) {
            this.betAmount.value = Math.max(1, maxBet);
            this.betSlider.value = this.betAmount.value;
        }
    }

    async startGame() {
        if (this.isPlaying) return;

        const amount = parseFloat(this.betAmount.value);
        if (amount > this.gm.balance) {
            this.gm.showNotification('Yetersiz bakiye!', 'error');
            return;
        }

        this.isPlaying = true;
        this.dealBtn.disabled = true;
        this.btnText.classList.add('hidden');
        this.btnLoading.classList.remove('hidden');
        this.bjMessage.classList.add('hidden');

        // Clear table
        this.dealerCards.innerHTML = '';
        this.playerCards.innerHTML = '';
        this.dealerScore.textContent = '?';
        this.playerScore.textContent = '0';

        try {
            const response = await fetch(`${this.gm.apiUrl}/game/blackjack/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ amount })
            });

            const data = await response.json();

            if (response.ok) {
                this.gm.updateBalance(data.new_balance);

                // Render cards
                this.renderCard(data.dealer_card, this.dealerCards);
                this.renderHiddenCard(this.dealerCards);

                data.player_hand.forEach(card => this.renderCard(card, this.playerCards));
                this.playerScore.textContent = data.player_value;

                if (data.status === 'finished') {
                    // Immediate Blackjack
                    this.endGame(data);
                } else {
                    // Show actions
                    this.betArea.classList.add('hidden');
                    this.dealBtn.classList.add('hidden');
                    this.bjActions.classList.remove('hidden');
                }
            } else {
                this.gm.showNotification(data.message, 'error');
                this.resetUI();
            }
        } catch (error) {
            this.gm.showNotification('Oyun hatası!', 'error');
            this.resetUI();
        }
    }

    async hit() {
        try {
            const response = await fetch(`${this.gm.apiUrl}/game/blackjack/hit`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                // Add new card
                const newCard = data.player_hand[data.player_hand.length - 1];
                this.renderCard(newCard, this.playerCards);
                this.playerScore.textContent = data.player_value;

                if (data.status === 'bust') {
                    this.showMessage('BUST! 💥', 'lose');
                    this.resetUI();
                }
            }
        } catch (error) {
            console.error(error);
        }
    }

    async stand() {
        try {
            const response = await fetch(`${this.gm.apiUrl}/game/blackjack/stand`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.endGame(data);
            }
        } catch (error) {
            console.error(error);
        }
    }

    endGame(data) {
        // Reveal dealer cards
        this.dealerCards.innerHTML = '';
        data.dealer_hand.forEach(card => this.renderCard(card, this.dealerCards));
        this.dealerScore.textContent = data.dealer_value;

        // Show result
        const isWin = data.result === 'win';
        const isPush = data.result === 'push';
        const msgType = isWin ? 'win' : (isPush ? 'info' : 'lose');

        this.showMessage(data.message, msgType);

        if (data.payout > 0) {
            this.gm.updateBalance(data.new_balance);
        }

        this.gm.addToHistory(
            '🃏',
            `Blackjack: ${data.message}`,
            isWin
        );

        this.resetUI();
    }

    resetUI() {
        this.isPlaying = false;
        this.bjActions.classList.add('hidden');
        this.betArea.classList.remove('hidden');
        this.dealBtn.classList.remove('hidden');
        this.dealBtn.disabled = false;
        this.btnText.classList.remove('hidden');
        this.btnLoading.classList.add('hidden');
    }

    showMessage(text, type) {
        this.bjMessage.textContent = text;
        this.bjMessage.className = `bj-message ${type}`;
        this.bjMessage.classList.remove('hidden');
    }

    renderCard(card, container) {
        const el = document.createElement('div');
        const isRed = ['H', 'D'].includes(card.suit);
        const suitSymbol = { 'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠' }[card.suit];

        el.className = `card ${isRed ? 'red' : 'black'}`;
        el.innerHTML = `
            <div class="card-rank-top">${card.rank}</div>
            <div class="card-suit">${suitSymbol}</div>
            <div class="card-rank-bottom">${card.rank}</div>
        `;

        container.appendChild(el);
    }

    renderHiddenCard(container) {
        const el = document.createElement('div');
        el.className = 'card hidden-card';
        container.appendChild(el);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new GameManager();
});