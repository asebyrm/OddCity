/**
 * OddCity Casino - Game Manager
 */

class GameManager {
    constructor() {
        this.apiUrl = window.location.origin;
        this.currentUser = null;
        this.balance = 0;
        this.activeGame = 'coinflip';
        this.gameHistory = [];

        this.init();
    }

    async init() {
        this.bindElements();
        this.bindEvents();
        await this.checkAuth();
        this.initGames();
    }

    bindElements() {
        // Sidebar
        this.sidebar = document.getElementById('sidebar');
        this.menuToggle = document.getElementById('menuToggle');
        this.navItems = document.querySelectorAll('.nav-item');
        
        // Auth
        this.guestButtons = document.getElementById('guestButtons');
        this.userInfo = document.getElementById('userInfo');
        this.userEmail = document.getElementById('userEmail');
        this.loginBtn = document.getElementById('loginBtn');
        this.registerBtn = document.getElementById('registerBtn');
        this.logoutBtn = document.getElementById('logoutBtn');
        
        // Balance
        this.balanceValue = document.getElementById('balanceValue');
        this.walletButtons = document.getElementById('walletButtons');
        this.depositBtn = document.getElementById('depositBtn');
        this.withdrawBtn = document.getElementById('withdrawBtn');
        
        // Game sections
        this.gameTitle = document.getElementById('gameTitle');
        this.coinflipGame = document.getElementById('coinflipGame');
        this.rouletteGame = document.getElementById('rouletteGame');
        this.blackjackGame = document.getElementById('blackjackGame');
        this.historySection = document.getElementById('historySection');
        this.historyList = document.getElementById('historyList');
        
        // Auth Modal
        this.authModal = document.getElementById('authModal');
        this.loginForm = document.getElementById('loginForm');
        this.registerForm = document.getElementById('registerForm');
        this.authModalClose = document.getElementById('authModalClose');
        
        // Wallet Modal
        this.walletModal = document.getElementById('walletModal');
        this.walletTitle = document.getElementById('walletTitle');
        this.walletAmount = document.getElementById('walletAmount');
        this.walletModalClose = document.getElementById('walletModalClose');
        
        // Notification
        this.notification = document.getElementById('notification');
        this.notificationText = document.getElementById('notificationText');
        this.notificationClose = document.getElementById('notificationClose');
    }

    bindEvents() {
        // Mobile menu
        this.menuToggle.addEventListener('click', () => {
            this.sidebar.classList.toggle('open');
        });

        // Game navigation
        this.navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchGame(item.dataset.game);
                this.sidebar.classList.remove('open');
            });
        });

        // Auth buttons
        this.loginBtn.addEventListener('click', () => this.showAuthModal('login'));
        this.registerBtn.addEventListener('click', () => this.showAuthModal('register'));
        this.logoutBtn.addEventListener('click', () => this.logout());
        
        // Auth modal
        this.authModalClose.addEventListener('click', () => this.hideModal(this.authModal));
        document.getElementById('showRegister').addEventListener('click', (e) => {
            e.preventDefault();
            this.showAuthModal('register');
        });
        document.getElementById('showLogin').addEventListener('click', (e) => {
            e.preventDefault();
            this.showAuthModal('login');
        });
        
        // Auth forms
        document.getElementById('loginFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });
        document.getElementById('registerFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.register();
        });

        // Wallet buttons
        this.depositBtn.addEventListener('click', () => this.showWalletModal('deposit'));
        this.withdrawBtn.addEventListener('click', () => this.showWalletModal('withdraw'));
        this.walletModalClose.addEventListener('click', () => this.hideModal(this.walletModal));
        
        // Wallet form
        document.getElementById('walletFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.processWallet();
        });

        // Quick amounts in wallet modal
        document.querySelectorAll('.quick-amount').forEach(btn => {
            btn.addEventListener('click', () => {
                this.walletAmount.value = btn.dataset.amount;
            });
        });

        // Notification close
        this.notificationClose.addEventListener('click', () => this.hideNotification());

        // Close modals on outside click
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideModal(e.target);
            }
        });
    }

    // ========================================
    // Auth Methods
    // ========================================

    async checkAuth() {
        try {
            const response = await fetch(`${this.apiUrl}/me`, {
                credentials: 'include'
            });

            if (response.ok) {
                const user = await response.json();
                this.currentUser = user;
                await this.onLogin(user);
            }
        } catch (error) {
            console.error('Auth check error:', error);
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
                this.currentUser = data;
                await this.onLogin(data);
                this.hideModal(this.authModal);
                this.showNotification('Giriş başarılı!', 'success');
            } else {
                this.showNotification(data.message || 'Giriş başarısız!', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async register() {
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;

        try {
            const response = await fetch(`${this.apiUrl}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Kayıt başarılı! Giriş yapabilirsiniz.', 'success');
                this.showAuthModal('login');
            } else {
                this.showNotification(data.message || 'Kayıt başarısız!', 'error');
            }
        } catch (error) {
            console.error('Register error:', error);
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

        this.currentUser = null;
        this.onLogout();
        this.showNotification('Çıkış yapıldı', 'success');
    }

    async onLogin(user) {
        this.guestButtons.classList.add('hidden');
        this.userInfo.classList.remove('hidden');
        this.walletButtons.classList.remove('hidden');
        this.historySection.classList.remove('hidden');
        this.userEmail.textContent = user.email;
        
        // Eğer user objesinde balance varsa direkt kullan, yoksa fetch et
        if (user.balance !== undefined && user.balance !== null) {
            this.balance = parseFloat(user.balance);
            this.updateBalanceDisplay();
        } else {
            await this.fetchBalance();
        }
        
        this.enableGameControls();
    }

    onLogout() {
        this.guestButtons.classList.remove('hidden');
        this.userInfo.classList.add('hidden');
        this.walletButtons.classList.add('hidden');
        this.historySection.classList.add('hidden');
        this.balanceValue.textContent = '0.00';
        this.balance = 0;
        this.disableGameControls();
    }

    // ========================================
    // Wallet Methods
    // ========================================

    async fetchBalance() {
        try {
            const response = await fetch(`${this.apiUrl}/wallets/me`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.balance = data.balance;
                this.updateBalanceDisplay();
            }
        } catch (error) {
            console.error('Fetch balance error:', error);
        }
    }

    updateBalanceDisplay() {
        this.balanceValue.textContent = this.balance.toFixed(2);
    }

    showWalletModal(type) {
        this.walletType = type;
        this.walletTitle.textContent = type === 'deposit' ? '💰 Para Yatır' : '💸 Para Çek';
        document.getElementById('walletSubmitBtn').textContent = type === 'deposit' ? 'Yatır' : 'Çek';
        this.walletAmount.value = '';
        this.walletModal.classList.remove('hidden');
    }

    async processWallet() {
        const amount = parseFloat(this.walletAmount.value);
        if (!amount || amount <= 0) {
            this.showNotification('Geçerli bir miktar girin!', 'error');
            return;
        }

        const endpoint = this.walletType === 'deposit' ? '/wallets/me/deposit' : '/wallets/me/withdraw';

        try {
            const response = await fetch(`${this.apiUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ amount })
            });

            const data = await response.json();

            if (response.ok) {
                this.balance = data.new_balance;
                this.updateBalanceDisplay();
                this.hideModal(this.walletModal);
                this.showNotification(data.message, 'success');
            } else {
                this.showNotification(data.message || 'İşlem başarısız!', 'error');
            }
        } catch (error) {
            console.error('Wallet error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    // ========================================
    // Game Methods
    // ========================================

    initGames() {
        this.initCoinFlip();
        this.initRoulette();
        this.initBlackjack();
    }

    switchGame(game) {
        this.activeGame = game;

        // Update nav
        this.navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.game === game);
        });

        // Update title
        const titles = {
            coinflip: 'Coin Flip',
            roulette: 'Roulette',
            blackjack: 'Blackjack'
        };
        this.gameTitle.textContent = titles[game];

        // Show game section
        this.coinflipGame.classList.toggle('hidden', game !== 'coinflip');
        this.rouletteGame.classList.toggle('hidden', game !== 'roulette');
        this.blackjackGame.classList.toggle('hidden', game !== 'blackjack');
    }

    enableGameControls() {
        document.querySelectorAll('.game-controls').forEach(c => c.classList.remove('hidden'));
    }

    disableGameControls() {
        document.querySelectorAll('.game-controls').forEach(c => c.classList.add('hidden'));
    }

    addToHistory(result, isWin) {
        const item = document.createElement('div');
        item.className = `history-item ${isWin ? 'win' : 'lose'}`;
        item.textContent = isWin ? '✓' : '✗';
        
        if (this.historyList.children.length >= 20) {
            this.historyList.removeChild(this.historyList.lastChild);
        }
        this.historyList.insertBefore(item, this.historyList.firstChild);
    }

    // ========================================
    // Coin Flip
    // ========================================

    initCoinFlip() {
        this.coin = document.getElementById('coin');
        this.coinBetAmount = document.getElementById('coinBetAmount');
        this.coinPlayBtn = document.getElementById('coinPlayBtn');
        this.coinResult = document.getElementById('coinResult');
        this.coinChoice = null;

        // Quick bet buttons
        document.querySelectorAll('#coinControls .bet-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#coinControls .bet-quick').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.coinBetAmount.value = btn.dataset.amount;
            });
        });

        // Choice buttons
        document.querySelectorAll('#coinControls .choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#coinControls .choice-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                this.coinChoice = btn.dataset.choice;
                this.coinPlayBtn.disabled = false;
            });
        });

        // Play button
        this.coinPlayBtn.addEventListener('click', () => this.playCoinFlip());
    }

    async playCoinFlip() {
        if (!this.coinChoice) return;

        const amount = parseFloat(this.coinBetAmount.value);
        if (!amount || amount <= 0) {
            this.showNotification('Geçerli bir bahis miktarı girin!', 'error');
            return;
        }

        if (amount > this.balance) {
            this.showNotification('Yetersiz bakiye!', 'error');
            return;
        }

        this.coinPlayBtn.disabled = true;
        this.coinResult.classList.add('hidden');

        try {
            const response = await fetch(`${this.apiUrl}/game/play`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ choice: this.coinChoice, amount: amount })
            });

            const data = await response.json();

            if (response.ok) {
                // Animate coin
                this.coin.classList.remove('flipping-heads', 'flipping-tails');
                void this.coin.offsetWidth; // Force reflow
                this.coin.classList.add(data.result === 'yazi' ? 'flipping-heads' : 'flipping-tails');

                // Show result after animation
                setTimeout(() => {
                    const isWin = data.your_choice === data.result;
                    this.showCoinResult(isWin, data);
                    this.balance = data.new_balance;
                    this.updateBalanceDisplay();
                    this.addToHistory(data.result, isWin);
                }, 2500);
            } else {
                this.showNotification(data.message || 'Oyun hatası!', 'error');
                this.coinPlayBtn.disabled = false;
            }
        } catch (error) {
            console.error('Coin flip error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
            this.coinPlayBtn.disabled = false;
        }
    }

    showCoinResult(isWin, data) {
        this.coinResult.classList.remove('hidden', 'win', 'lose');
        this.coinResult.classList.add(isWin ? 'win' : 'lose');
        
        this.coinResult.querySelector('.result-icon').textContent = isWin ? '🎉' : '😔';
        this.coinResult.querySelector('.result-text').textContent = isWin ? 'KAZANDINIZ!' : 'KAYBETTİNİZ';
        this.coinResult.querySelector('.result-amount').textContent = data.message;
        
        // Reset for next game
        setTimeout(() => {
            this.coinPlayBtn.disabled = false;
            document.querySelectorAll('#coinControls .choice-btn').forEach(b => b.classList.remove('selected'));
            this.coinChoice = null;
            this.coinPlayBtn.disabled = true;
        }, 2000);
    }

    // ========================================
    // Roulette
    // ========================================

    initRoulette() {
        this.rouletteStrip = document.getElementById('rouletteStrip');
        this.rouletteBetAmount = document.getElementById('rouletteBetAmount');
        this.roulettePlayBtn = document.getElementById('roulettePlayBtn');
        this.rouletteResult = document.getElementById('rouletteResult');
        this.selectedBet = document.getElementById('selectedBet');
        this.stripResultDisplay = document.getElementById('stripResultDisplay');
        this.stripResultNum = document.getElementById('stripResultNum');
        this.stripResultColor = document.getElementById('stripResultColor');
        this.rouletteBet = null;

        // Rulet sırası (Avrupa ruleti)
        this.rouletteSequence = [
            0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
            5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
        ];
        
        this.redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
        
        // Şeridi oluştur (5 tekrar - sonsuz döngü hissi için)
        this.buildRouletteStrip();

        // Generate number buttons
        const numbersContainer = document.querySelector('#rouletteGame .bet-row.numbers');
        
        for (let i = 1; i <= 36; i++) {
            const btn = document.createElement('button');
            btn.className = `bet-option ${this.redNumbers.includes(i) ? 'red' : 'black'}`;
            btn.dataset.type = 'number';
            btn.dataset.value = i;
            btn.textContent = i;
            numbersContainer.appendChild(btn);
        }

        // Quick bet buttons
        document.querySelectorAll('#rouletteControls .bet-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#rouletteControls .bet-quick').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.rouletteBetAmount.value = btn.dataset.amount;
            });
        });

        // Bet option buttons
        document.querySelectorAll('#rouletteGame .bet-option').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#rouletteGame .bet-option').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                
                this.rouletteBet = {
                    type: btn.dataset.type,
                    value: btn.dataset.value
                };
                
                const labels = {
                    color: { red: '🔴 Kırmızı', black: '⚫ Siyah' },
                    parity: { even: 'Çift', odd: 'Tek' },
                    number: btn.dataset.value
                };
                
                const betLabel = btn.dataset.type === 'number' 
                    ? `Sayı: ${btn.dataset.value}` 
                    : labels[btn.dataset.type][btn.dataset.value];
                
                this.selectedBet.textContent = `Seçim: ${betLabel}`;
                this.roulettePlayBtn.disabled = false;
            });
        });

        // Play button
        this.roulettePlayBtn.addEventListener('click', () => this.playRoulette());
    }

    buildRouletteStrip() {
        this.rouletteStrip.innerHTML = '';
        
        // 10 tekrar oluştur (sonsuz döngü hissi için)
        this.stripRepeatCount = 10;
        for (let repeat = 0; repeat < this.stripRepeatCount; repeat++) {
            this.rouletteSequence.forEach(num => {
                const numberEl = document.createElement('div');
                let colorClass = 'green';
                if (num !== 0) {
                    colorClass = this.redNumbers.includes(num) ? 'red' : 'black';
                }
                numberEl.className = `strip-number ${colorClass}`;
                numberEl.textContent = num;
                numberEl.dataset.number = num;
                this.rouletteStrip.appendChild(numberEl);
            });
        }
        
        // Başlangıç pozisyonu
        this.stripNumberWidth = 60;
        this.stripResetPosition();
    }

    stripResetPosition() {
        // Şeridi sıfırla - 2. tekrarın başına getir (böylece sola ve sağa yer var)
        const startRepeat = 2;
        const startPosition = startRepeat * this.rouletteSequence.length * this.stripNumberWidth;
        this.rouletteStrip.style.transition = 'none';
        this.rouletteStrip.style.transform = `translateX(-${startPosition}px)`;
    }

    async playRoulette() {
        if (!this.rouletteBet) return;

        const amount = parseFloat(this.rouletteBetAmount.value);
        if (!amount || amount <= 0) {
            this.showNotification('Geçerli bir bahis miktarı girin!', 'error');
            return;
        }

        if (amount > this.balance) {
            this.showNotification('Yetersiz bakiye!', 'error');
            return;
        }

        this.roulettePlayBtn.disabled = true;
        this.rouletteResult.classList.add('hidden');
        this.stripResultDisplay.classList.add('hidden');
        
        // Önceki kazanan işaretini temizle
        this.rouletteStrip.querySelectorAll('.winning').forEach(el => el.classList.remove('winning'));
        
        // Şeridi sıfırla ve animasyon için hazırla
        this.rouletteStrip.style.transition = 'none';
        this.stripResetPosition();
        
        // Bir frame bekle ki browser yeni pozisyonu render etsin
        await new Promise(resolve => requestAnimationFrame(resolve));

        try {
            const response = await fetch(`${this.apiUrl}/game/roulette/play`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    bet_type: this.rouletteBet.type,
                    bet_value: this.rouletteBet.value,
                    amount: amount
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Backend field mapping
                const result = data.winning_number;
                const isWin = data.is_win;
                const color = data.winning_color;
                
                // Şerit animasyonu
                this.animateRouletteStrip(result, () => {
                    this.showRouletteResult(result, color, isWin, data.payout, data.message);
                    this.balance = data.new_balance;
                    this.updateBalanceDisplay();
                    this.addToHistory(result, isWin);
                });
            } else {
                this.showNotification(data.message || 'Oyun hatası!', 'error');
                this.roulettePlayBtn.disabled = false;
            }
        } catch (error) {
            console.error('Roulette error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
            this.roulettePlayBtn.disabled = false;
        }
    }

    animateRouletteStrip(resultNumber, callback) {
        // Sonuç gösterimini gizle
        this.stripResultDisplay.classList.add('hidden');
        
        // Sonuç sayısının şeritteki indeksini bul
        const resultIndex = this.rouletteSequence.indexOf(resultNumber);
        
        if (resultIndex === -1) {
            console.error('Sonuç sayısı şeritte bulunamadı:', resultNumber);
            callback();
            return;
        }
        
        // 3-5 tam tur + sonuç pozisyonuna git
        const fullRotations = 3 + Math.floor(Math.random() * 3); // 3-5 tur
        const numbersToTravel = fullRotations * this.rouletteSequence.length + resultIndex;
        
        // Her sayı 60px genişliğinde
        const travelDistance = numbersToTravel * this.stripNumberWidth;
        
        // 2. tekrardan başlıyoruz
        const startRepeat = 2;
        const startPosition = startRepeat * this.rouletteSequence.length * this.stripNumberWidth;
        const finalPosition = startPosition + travelDistance;
        
        // Animasyonu başlat
        this.rouletteStrip.style.transition = 'transform 4s cubic-bezier(0.15, 0.85, 0.35, 1)';
        this.rouletteStrip.style.transform = `translateX(-${finalPosition}px)`;
        
        // Animasyon bitince
        setTimeout(() => {
            // Kazanan sayıyı işaretle
            const allNumbers = this.rouletteStrip.querySelectorAll('.strip-number');
            allNumbers.forEach(el => {
                if (parseInt(el.dataset.number) === resultNumber) {
                    el.classList.add('winning');
                }
            });
            
            // Sonuç gösterimini güncelle ve göster
            this.showStripResult(resultNumber);
            
            callback();
            
            // Bir süre sonra şeridi sıfırla
            setTimeout(() => {
                this.rouletteStrip.style.transition = 'none';
                this.stripResetPosition();
                // Bir frame sonra transition'ı geri aç
                requestAnimationFrame(() => {
                    this.rouletteStrip.style.transition = '';
                });
            }, 3000);
        }, 4000);
    }

    showStripResult(number) {
        const colorName = number === 0 ? 'Yeşil' : (this.redNumbers.includes(number) ? 'Kırmızı' : 'Siyah');
        const colorClass = number === 0 ? 'green' : (this.redNumbers.includes(number) ? 'red' : 'black');
        
        this.stripResultNum.textContent = number;
        this.stripResultNum.className = `result-num ${colorClass}`;
        this.stripResultColor.textContent = colorName;
        this.stripResultDisplay.classList.remove('hidden');
    }

    showRouletteResult(result, color, isWin, payout, message) {
        this.rouletteResult.classList.remove('hidden', 'win', 'lose');
        this.rouletteResult.classList.add(isWin ? 'win' : 'lose');
        
        const colorClass = result === 0 ? 'green' : (color === 'red' ? 'red' : 'black');
        this.rouletteResult.querySelector('.result-number').textContent = result;
        this.rouletteResult.querySelector('.result-number').className = `result-number ${colorClass}`;
        this.rouletteResult.querySelector('.result-text').textContent = isWin ? 'KAZANDINIZ!' : 'KAYBETTİNİZ';
        
        // Kazanç miktarını göster
        if (isWin && payout > 0) {
            this.rouletteResult.querySelector('.result-amount').textContent = `+${payout.toFixed(2)} ₿`;
        } else {
            this.rouletteResult.querySelector('.result-amount').textContent = message;
        }
        
        // Reset for next game
        setTimeout(() => {
            this.roulettePlayBtn.disabled = false;
            document.querySelectorAll('#rouletteGame .bet-option').forEach(b => b.classList.remove('selected'));
            this.rouletteBet = null;
            this.selectedBet.textContent = 'Seçim yapın...';
            this.roulettePlayBtn.disabled = true;
        }, 2000);
    }

    // ========================================
    // Blackjack
    // ========================================

    initBlackjack() {
        this.bjBetAmount = document.getElementById('bjBetAmount');
        this.bjPlayBtn = document.getElementById('bjPlayBtn');
        this.bjActions = document.getElementById('bjActions');
        this.bjBetSection = document.getElementById('bjBetSection');
        this.hitBtn = document.getElementById('hitBtn');
        this.standBtn = document.getElementById('standBtn');
        this.bjMessage = document.getElementById('bjMessage');
        this.dealerCards = document.getElementById('dealerCards');
        this.playerCards = document.getElementById('playerCards');
        this.dealerScore = document.getElementById('dealerScore');
        this.playerScore = document.getElementById('playerScore');
        this.bjGameActive = false;

        // Quick bet buttons
        document.querySelectorAll('#blackjackControls .bet-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#blackjackControls .bet-quick').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.bjBetAmount.value = btn.dataset.amount;
            });
        });

        // Play button
        this.bjPlayBtn.addEventListener('click', () => this.startBlackjack());
        this.hitBtn.addEventListener('click', () => this.blackjackHit());
        this.standBtn.addEventListener('click', () => this.blackjackStand());
    }

    async startBlackjack() {
        const amount = parseFloat(this.bjBetAmount.value);
        if (!amount || amount <= 0) {
            this.showNotification('Geçerli bir bahis miktarı girin!', 'error');
            return;
        }

        if (amount > this.balance) {
            this.showNotification('Yetersiz bakiye!', 'error');
            return;
        }

        this.bjPlayBtn.disabled = true;
        this.bjMessage.classList.add('hidden');

        try {
            const response = await fetch(`${this.apiUrl}/game/blackjack/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ amount: amount })
            });

            const data = await response.json();

            if (response.ok) {
                this.bjGameActive = true;
                this.bjBetSection.classList.add('hidden');
                this.bjActions.classList.remove('hidden');
                this.bjPlayBtn.classList.add('hidden');
                
                this.renderBlackjackHands(data);
                this.balance = data.new_balance;
                this.updateBalanceDisplay();

                // Check for immediate blackjack or game over
                if (data.status === 'finished' || data.status === 'blackjack') {
                    this.endBlackjack(data);
                }
            } else {
                this.showNotification(data.message || 'Oyun başlatılamadı!', 'error');
                this.bjPlayBtn.disabled = false;
            }
        } catch (error) {
            console.error('Blackjack start error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
            this.bjPlayBtn.disabled = false;
        }
    }

    async blackjackHit() {
        try {
            const response = await fetch(`${this.apiUrl}/game/blackjack/hit`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.renderBlackjackHands(data);
                
                // Check if game is over (bust or finished)
                if (data.status === 'bust' || data.status === 'finished') {
                    this.endBlackjack(data);
                }
            } else {
                this.showNotification(data.message || 'Hata!', 'error');
            }
        } catch (error) {
            console.error('Blackjack hit error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    async blackjackStand() {
        try {
            const response = await fetch(`${this.apiUrl}/game/blackjack/stand`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                this.renderBlackjackHands(data, true);
                this.endBlackjack(data);
            } else {
                this.showNotification(data.message || 'Hata!', 'error');
            }
        } catch (error) {
            console.error('Blackjack stand error:', error);
            this.showNotification('Bağlantı hatası!', 'error');
        }
    }

    renderBlackjackHands(data, showAllDealer = false) {
        // Clear cards
        this.dealerCards.innerHTML = '';
        this.playerCards.innerHTML = '';

        // Check if game is over
        const isGameOver = data.status === 'finished' || data.status === 'bust' || data.status === 'blackjack';

        // Backend sends different field names depending on the endpoint
        // start: player_hand, dealer_card (single card shown)
        // hit/stand: player_hand, dealer_hand (full hand)
        
        // Render dealer cards
        const dealerCards = data.dealer_hand || (data.dealer_card ? [data.dealer_card] : []);
        if (dealerCards.length > 0) {
            dealerCards.forEach((card, i) => {
                // If not showing all and it's the second card (and game not over), hide it
                if (!showAllDealer && !isGameOver && i === 1 && data.dealer_hand) {
                    const cardEl = document.createElement('div');
                    cardEl.className = 'card hidden-card';
                    this.dealerCards.appendChild(cardEl);
                } else {
                    this.dealerCards.appendChild(this.createCardElement(card));
                }
            });
            
            // If only one dealer card shown (from start), add hidden card
            if (!data.dealer_hand && data.dealer_card && !isGameOver) {
                const cardEl = document.createElement('div');
                cardEl.className = 'card hidden-card';
                this.dealerCards.appendChild(cardEl);
            }
        }

        // Render player cards
        const playerCards = data.player_hand || data.player_cards || [];
        playerCards.forEach(card => {
            this.playerCards.appendChild(this.createCardElement(card));
        });

        // Update scores
        this.playerScore.textContent = data.player_value || '?';
        this.dealerScore.textContent = (showAllDealer || isGameOver) ? (data.dealer_value || '?') : '?';
    }

    createCardElement(card) {
        // Backend uses H, D, C, S for suits
        const suits = { 
            'H': '♥', 'hearts': '♥',
            'D': '♦', 'diamonds': '♦', 
            'C': '♣', 'clubs': '♣', 
            'S': '♠', 'spades': '♠' 
        };
        const suitSymbol = suits[card.suit] || card.suit;
        const isRed = card.suit === 'H' || card.suit === 'D' || card.suit === 'hearts' || card.suit === 'diamonds';
        
        const cardEl = document.createElement('div');
        cardEl.className = `card ${isRed ? 'red' : 'black'}`;
        cardEl.innerHTML = `
            <div class="card-rank">${card.rank}</div>
            <div class="card-suit">${suitSymbol}</div>
            <div class="card-rank card-rank-bottom">${card.rank}</div>
        `;
        return cardEl;
    }

    endBlackjack(data) {
        this.bjGameActive = false;
        this.bjActions.classList.add('hidden');
        
        // Determine win status from result
        const isWin = data.result === 'win' || data.status === 'blackjack';
        const isPush = data.result === 'push';
        
        // Show result message
        this.bjMessage.classList.remove('hidden');
        this.bjMessage.textContent = data.message || (isWin ? 'Kazandınız!' : 'Kaybettiniz!');
        
        // Update balance
        if (data.new_balance !== undefined) {
            this.balance = data.new_balance;
            this.updateBalanceDisplay();
        }

        // Add to history (push counts as neither win nor loss)
        if (!isPush) {
            this.addToHistory('BJ', isWin);
        }

        // Reset for next game
        setTimeout(() => {
            this.bjBetSection.classList.remove('hidden');
            this.bjPlayBtn.classList.remove('hidden');
            this.bjPlayBtn.disabled = false;
            this.bjMessage.classList.add('hidden');
            this.dealerCards.innerHTML = '';
            this.playerCards.innerHTML = '';
            this.dealerScore.textContent = '?';
            this.playerScore.textContent = '0';
        }, 3000);
    }

    // ========================================
    // UI Helpers
    // ========================================

    showAuthModal(type) {
        this.authModal.classList.remove('hidden');
        this.loginForm.classList.toggle('hidden', type !== 'login');
        this.registerForm.classList.toggle('hidden', type !== 'register');
    }

    hideModal(modal) {
        modal.classList.add('hidden');
    }

    showNotification(message, type = 'success') {
        this.notification.classList.remove('hidden', 'success', 'error');
        this.notification.classList.add(type);
        this.notificationText.textContent = message;

        setTimeout(() => this.hideNotification(), 4000);
    }

    hideNotification() {
        this.notification.classList.add('hidden');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.gameManager = new GameManager();
});
