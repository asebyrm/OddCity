document.addEventListener('DOMContentLoaded', () => {
    const loginSection = document.getElementById('loginSection');
    const dashboardSection = document.getElementById('dashboardSection');
    const navButtons = document.getElementById('navButtons');
    const adminLoginForm = document.getElementById('adminLoginForm');

    const userTableBody = document.getElementById('userTableBody');
    const logoutBtn = document.getElementById('logoutBtn');
    const historyModal = document.getElementById('historyModal');
    const historyList = document.getElementById('historyList');
    const closeModal = document.querySelector('.close');

    // Check auth on load
    checkAuth();

    adminLoginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('adminEmail').value;
        const password = document.getElementById('adminPassword').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await response.json();

            if (response.ok) {
                if (data.is_admin) {
                    checkAuth(); // Refresh UI
                } else {
                    alert('Bu hesap admin yetkisine sahip değil!');
                }
            } else {
                alert(data.message);
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Giriş hatası.');
        }
    });

    logoutBtn.addEventListener('click', async () => {
        await fetch('/logout', { method: 'POST' });
        window.location.reload();
    });

    closeModal.addEventListener('click', () => {
        historyModal.classList.add('hidden');
    });

    window.onclick = (event) => {
        if (event.target == historyModal) {
            historyModal.classList.add('hidden');
        }
    };

    async function checkAuth() {
        try {
            const response = await fetch('/admin/users');
            if (response.ok) {
                const users = await response.json();
                showDashboard();
                renderUsers(users);
            } else {
                showLogin();
            }
        } catch (error) {
            console.error('Auth check error:', error);
            showLogin();
        }
    }

    function showLogin() {
        loginSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
        navButtons.classList.add('hidden');
    }

    function showDashboard() {
        loginSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        navButtons.classList.remove('hidden');
    }

    function renderUsers(users) {
        userTableBody.innerHTML = '';
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.user_id}</td>
                <td>${user.email}</td>
                <td>${parseFloat(user.balance).toFixed(2)} ${user.currency}</td>
                <td><span class="status-badge ${user.status === 'ACTIVE' ? 'status-active' : 'status-banned'}">${user.status}</span></td>
                <td>${user.is_admin ? '✅' : '❌'}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="action-btn btn-history" data-userid="${user.user_id}">Geçmiş</button>
                    ${!user.is_admin ? `
                        ${user.status === 'ACTIVE'
                        ? `<button class="action-btn btn-ban" data-userid="${user.user_id}" data-action="ban">Yasakla</button>`
                        : `<button class="action-btn btn-unban" data-userid="${user.user_id}" data-action="unban">Yasağı Kaldır</button>`
                    }
                    ` : ''}
                </td>
            `;
            userTableBody.appendChild(tr);
        });
    }

    // Event Delegation for Table Actions
    userTableBody.addEventListener('click', async (e) => {
        const target = e.target;
        const userId = target.dataset.userid;

        if (!userId) return;

        if (target.classList.contains('btn-ban') || target.classList.contains('btn-unban')) {
            const action = target.dataset.action;
            toggleBan(userId, action);
        } else if (target.classList.contains('btn-history')) {
            viewHistory(userId);
        }
    });

    async function toggleBan(userId, action) {
        if (!confirm(`Bu kullanıcıyı ${action === 'ban' ? 'yasaklamak' : 'yasağını kaldırmak'} istediğinize emin misiniz?`)) return;

        try {
            const response = await fetch(`/admin/user/${userId}/${action}`, { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            checkAuth(); // Refresh list
        } catch (error) {
            console.error('Error:', error);
            alert('İşlem başarısız.');
        }
    }

    async function viewHistory(userId) {
        try {
            const response = await fetch(`/admin/user/${userId}/history`);
            const history = await response.json();

            historyList.innerHTML = '';
            if (history.length === 0) {
                historyList.innerHTML = '<p>İşlem geçmişi yok.</p>';
            } else {
                history.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'history-item';
                    div.innerHTML = `
                        <span>${item.tx_type}</span>
                        <span>${parseFloat(item.amount).toFixed(2)}</span>
                        <span style="font-size: 0.8rem; opacity: 0.7;">${new Date(item.created_at).toLocaleString()}</span>
                    `;
                    historyList.appendChild(div);
                });
            }
            historyModal.classList.remove('hidden');
        } catch (error) {
            console.error('Error:', error);
            alert('Geçmiş yüklenemedi.');
        }
    }
});
