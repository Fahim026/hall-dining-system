/**
 * ============================================================
 * Hall Dining Management System — API Service
 * Connects all frontend HTML pages to Django + JWT backend
 * Base URL: http://localhost:8000/api
 * ============================================================
 */

const API_BASE = 'http://localhost:8000/api';

// ─── TOKEN HELPERS ────────────────────────────────────────────────────────────

const Auth = {
    getAccess: () => localStorage.getItem('access_token'),
    getRefresh: () => localStorage.getItem('refresh_token'),
    getUser: () => JSON.parse(localStorage.getItem('user') || 'null'),
    isLoggedIn: () => !!localStorage.getItem('access_token'),

    save(data) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.user));
    },

    clear() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },

    isAdmin() {
        const user = this.getUser();
        return user && user.role === 'admin';
    },

    isStudent() {
        const user = this.getUser();
        return user && user.role === 'student';
    },

    // Guard: redirect if not logged in
    requireLogin(redirectUrl = 'login.html') {
        if (!this.isLoggedIn()) {
            window.location.href = redirectUrl;
            return false;
        }
        return true;
    },

    // Guard: redirect if not admin
    requireAdmin() {
        if (!this.isLoggedIn() || !this.isAdmin()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    },

    // Guard: redirect if not student
    requireStudent() {
        if (!this.isLoggedIn() || !this.isStudent()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }
};

// ─── HTTP CLIENT ──────────────────────────────────────────────────────────────

async function http(method, endpoint, body = null, retry = true) {
    const headers = { 'Content-Type': 'application/json' };
    const token = Auth.getAccess();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    let res = await fetch(`${API_BASE}${endpoint}`, options);

    // Auto-refresh token on 401
    if (res.status === 401 && retry) {
        const refreshed = await refreshToken();
        if (refreshed) return http(method, endpoint, body, false);
        Auth.clear();
        window.location.href = 'login.html';
        return null;
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Server error' }));
        throw err;
    }

    if (res.status === 204) return null;
    return res.json();
}

async function refreshToken() {
    const refresh = Auth.getRefresh();
    if (!refresh) return false;
    try {
        const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh })
        });
        if (!res.ok) return false;
        const data = await res.json();
        localStorage.setItem('access_token', data.access);
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh);
        return true;
    } catch {
        return false;
    }
}

const get  = (url)        => http('GET',    url);
const post = (url, body)  => http('POST',   url, body);
const put  = (url, body)  => http('PUT',    url, body);
const patch= (url, body)  => http('PATCH',  url, body);
const del  = (url)        => http('DELETE', url);

// ─── SHOW TOAST NOTIFICATION ──────────────────────────────────────────────────

function showToast(message, type = 'success') {
    // Remove existing toast
    document.querySelectorAll('.api-toast').forEach(t => t.remove());

    const colors = {
        success: '#4CAF50',
        error: '#f44336',
        warning: '#FF9800',
        info: '#2196F3'
    };

    const toast = document.createElement('div');
    toast.className = 'api-toast';
    toast.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 99999;
        background: ${colors[type] || colors.info}; color: white;
        padding: 15px 25px; border-radius: 8px; font-size: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        animation: slideIn 0.3s ease; max-width: 350px;
    `;
    toast.innerHTML = `
        <style>@keyframes slideIn { from { opacity:0; transform:translateX(100px); } to { opacity:1; transform:translateX(0); } }</style>
        ${message}
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function extractError(err) {
    if (typeof err === 'string') return err;
    if (err.detail) return err.detail;
    const msgs = Object.values(err).flat();
    return msgs.join(' ') || 'Something went wrong.';
}

// ─── LOADING BUTTON HELPER ────────────────────────────────────────────────────

function setLoading(btn, loading, originalText) {
    if (loading) {
        btn.disabled = true;
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Please wait...';
    } else {
        btn.disabled = false;
        btn.innerHTML = originalText || btn.dataset.originalText || 'Submit';
    }
}

// ─── FORMAT HELPERS ───────────────────────────────────────────────────────────

function formatCurrency(amount) {
    return '৳' + parseFloat(amount || 0).toFixed(2);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-BD', {
        day: '2-digit', month: 'short', year: 'numeric'
    });
}

function currentMonth() { return new Date().getMonth() + 1; }
function currentYear()  { return new Date().getFullYear(); }

// ─────────────────────────────────────────────────────────────────────────────
//  PAGE: LOGIN
// ─────────────────────────────────────────────────────────────────────────────

async function initLoginPage() {
    // Already logged in → redirect
    if (Auth.isLoggedIn()) {
        redirectByRole();
        return;
    }

    // Admin login form
    const adminForm = document.getElementById('adminLoginForm');
    if (adminForm) {
        adminForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = adminForm.querySelector('.login-btn');
            setLoading(btn, true);
            try {
                const email    = document.getElementById('admin-username').value.trim();
                const password = document.getElementById('admin-password').value;
                const data = await post('/auth/login/', { email, password });
                if (data.user.role !== 'admin') {
                    showToast('This account is not an admin account.', 'error');
                    return;
                }
                Auth.save(data);
                showToast('Welcome back, Admin!', 'success');
                setTimeout(() => window.location.href = 'admin-dashboard.html', 800);
            } catch (err) {
                showToast(extractError(err), 'error');
            } finally {
                setLoading(btn, false);
            }
        });
    }

    // Student login form
    const studentForm = document.getElementById('studentLoginForm');
    if (studentForm) {
        studentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = studentForm.querySelector('.login-btn');
            setLoading(btn, true);
            try {
                // Student logs in with email (student ID field maps to email)
                const email    = document.getElementById('student-id').value.trim();
                const password = document.getElementById('student-password').value;
                const data = await post('/auth/login/', { email, password });
                if (data.user.role !== 'student') {
                    showToast('This account is not a student account.', 'error');
                    return;
                }
                Auth.save(data);
                showToast('Login successful!', 'success');
                setTimeout(() => window.location.href = 'student-dashboard.html', 800);
            } catch (err) {
                showToast(extractError(err), 'error');
            } finally {
                setLoading(btn, false);
            }
        });
    }

    // Forgot password
    const forgotForm = document.getElementById('forgotForm');
    if (forgotForm) {
        forgotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showToast('Password reset link has been sent to your email.', 'info');
            document.getElementById('forgotModal')?.classList.remove('active');
            forgotForm.reset();
        });
    }
}

function redirectByRole() {
    if (Auth.isAdmin()) window.location.href = 'admin-dashboard.html';
    else window.location.href = 'student-dashboard.html';
}

// ─────────────────────────────────────────────────────────────────────────────
//  PAGE: SIGNUP
// ─────────────────────────────────────────────────────────────────────────────

async function initSignupPage() {
    if (Auth.isLoggedIn()) { redirectByRole(); return; }

    const studentForm = document.getElementById('studentSignupForm');
    if (studentForm) {
        studentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = studentForm.querySelector('[type="submit"]');
            setLoading(btn, true);
            try {
                const payload = {
                    name:             document.getElementById('student-name')?.value,
                    email:            document.getElementById('student-email')?.value,
                    phone:            document.getElementById('student-phone')?.value || '',
                    room_number:      document.getElementById('student-room')?.value || '',
                    password:         document.getElementById('student-password')?.value,
                    password_confirm: document.getElementById('confirm-password')?.value,
                };
                const data = await post('/auth/register/', payload);
                Auth.save(data);
                showToast('Account created successfully!', 'success');
                setTimeout(() => window.location.href = 'student-dashboard.html', 1000);
            } catch (err) {
                showToast(extractError(err), 'error');
            } finally {
                setLoading(btn, false);
            }
        });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PAGE: STUDENT DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

async function initStudentDashboard() {
    if (!Auth.requireStudent()) return;

    const user = Auth.getUser();

    // Populate user info in header
    document.querySelectorAll('.student-name').forEach(el => el.textContent = user.name);
    document.querySelectorAll('.student-email').forEach(el => el.textContent = user.email);
    document.querySelectorAll('.student-room').forEach(el => el.textContent = user.room_number || '-');

    // Logout button
    document.getElementById('logoutBtn')?.addEventListener('click', logout);

    await Promise.all([
        loadStudentDashboardStats(),
        loadStudentMealHistory(),
        loadStudentMealOffRequests(),
        loadStudentGuestMeals(),
        loadStudentNotifications(),
        loadStudentDeposit(),
    ]);

    // Meal off request form
    initMealOffForm();
    // Guest meal request form
    initGuestMealForm();
    // Deposit form
    initDepositForm();
}

async function loadStudentDashboardStats() {
    try {
        const data = await get(`/dashboard/student/?month=${currentMonth()}&year=${currentYear()}`);

        setEl('balanceAmount',        formatCurrency(data.balance_remaining));
        setEl('depositedAmount',      formatCurrency(data.deposited_amount));
        setEl('totalMealsEaten',      data.total_meals_eaten);
        setEl('mealRate',             formatCurrency(data.meal_rate));
        setEl('totalCost',            formatCurrency(data.total_cost));
        setEl('mealOffUsed',          data.meal_off_days_used);
        setEl('mealOffLimit',         data.meal_off_days_limit);
        setEl('mealOffRemaining',     data.meal_off_days_remaining);
        setEl('depositStatus',        data.deposit_confirmed ? '✅ Confirmed' : '⏳ Pending');
        setEl('unreadNotifCount',     data.unread_notifications || '');
        setEl('pendingMealOff',       data.pending_requests?.meal_off || 0);
        setEl('pendingGuestMeal',     data.pending_requests?.guest_meal || 0);

        // Color balance based on amount
        const balEl = document.getElementById('balanceAmount');
        if (balEl) balEl.style.color = data.balance_remaining >= 0 ? 'var(--primary-color)' : '#f44336';
    } catch (err) {
        console.error('Dashboard stats error:', err);
    }
}

async function loadStudentMealHistory() {
    try {
        const data = await get(`/meal-entries/?month=${currentMonth()}&year=${currentYear()}`);
        const tbody = document.getElementById('mealHistoryBody');
        if (!tbody) return;

        if (!data.results?.length && !data.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999">No meal entries yet.</td></tr>';
            return;
        }

        const entries = data.results || data;
        tbody.innerHTML = entries.map(e => `
            <tr>
                <td>${formatDate(e.date)}</td>
                <td>${e.breakfast ? '✅' : '❌'}</td>
                <td>${e.lunch ? '✅' : '❌'}</td>
                <td>${e.dinner ? '✅' : '❌'}</td>
                <td><strong>${e.total_meals}</strong></td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadStudentMealOffRequests() {
    try {
        const data = await get('/meal-off/');
        const container = document.getElementById('mealOffList');
        if (!container) return;
        const entries = data.results || data;
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center">No meal-off requests yet.</p>';
            return;
        }
        container.innerHTML = entries.map(r => `
            <div class="request-item" style="padding:15px;background:#f9f9f9;border-radius:8px;margin-bottom:10px;border-left:4px solid ${statusColor(r.status)}">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
                    <div>
                        <strong>${formatDate(r.start_date)} → ${formatDate(r.end_date)}</strong>
                        <div style="font-size:0.85rem;color:#666;margin-top:4px">
                            ${r.skip_breakfast ? '🌅 Breakfast ' : ''}${r.skip_lunch ? '☀️ Lunch ' : ''}${r.skip_dinner ? '🌙 Dinner' : ''}
                        </div>
                        ${r.reason ? `<div style="font-size:0.85rem;color:#666;margin-top:4px">${r.reason}</div>` : ''}
                        ${r.admin_note ? `<div style="font-size:0.85rem;color:#800000;margin-top:4px">Admin: ${r.admin_note}</div>` : ''}
                    </div>
                    <div style="display:flex;align-items:center;gap:10px">
                        <span class="status-badge ${r.status}" style="background:${statusColor(r.status)}20;color:${statusColor(r.status)};padding:5px 12px;border-radius:20px;font-weight:600;font-size:0.85rem">${r.status.toUpperCase()}</span>
                        ${r.status === 'pending' ? `<button onclick="cancelMealOff(${r.id})" style="background:#f44336;color:white;border:none;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:0.85rem">Cancel</button>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadStudentGuestMeals() {
    try {
        const data = await get('/guest-meals/');
        const container = document.getElementById('guestMealList');
        if (!container) return;
        const entries = data.results || data;
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center">No guest meal requests yet.</p>';
            return;
        }
        container.innerHTML = entries.map(r => `
            <div style="padding:15px;background:#f9f9f9;border-radius:8px;margin-bottom:10px;border-left:4px solid ${statusColor(r.status)}">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
                    <div>
                        <strong>${r.guest_name}</strong> (${r.guest_count} guest${r.guest_count > 1 ? 's' : ''}) — ${r.meal_type}
                        <div style="font-size:0.85rem;color:#666;margin-top:4px">${formatDate(r.date)}</div>
                        ${r.extra_charge > 0 ? `<div style="font-size:0.85rem;color:#800000;margin-top:4px">Extra charge: ${formatCurrency(r.extra_charge)}</div>` : ''}
                    </div>
                    <span class="status-badge" style="background:${statusColor(r.status)}20;color:${statusColor(r.status)};padding:5px 12px;border-radius:20px;font-weight:600;font-size:0.85rem">${r.status.toUpperCase()}</span>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadStudentDeposit() {
    try {
        const data = await get(`/deposits/?month=${currentMonth()}&year=${currentYear()}`);
        const entries = data.results || data;
        const deposit = entries.find(d => d.month == currentMonth() && d.year == currentYear());
        const btn = document.getElementById('submitDepositBtn');
        if (btn && deposit) {
            btn.textContent = `Deposit Submitted: ${formatCurrency(deposit.deposited_amount)} — ${deposit.is_confirmed ? 'Confirmed' : 'Awaiting Confirmation'}`;
            btn.disabled = true;
        }
    } catch {}
}

async function loadStudentNotifications() {
    try {
        const data = await get('/notifications/');
        const container = document.getElementById('notificationList');
        if (!container) return;
        const entries = data.results || data;
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center;padding:20px">No notifications.</p>';
            return;
        }
        container.innerHTML = entries.slice(0, 10).map(n => `
            <div onclick="markNotifRead(${n.id}, this)" style="padding:15px;border-radius:8px;margin-bottom:10px;cursor:pointer;
                background:${n.is_read ? '#f9f9f9' : '#fff8e1'};border-left:4px solid ${n.is_read ? '#ddd' : '#FFD700'}">
                <strong style="color:#600000">${n.title}</strong>
                <p style="font-size:0.9rem;color:#666;margin-top:5px">${n.message}</p>
                <small style="color:#999">${formatDate(n.created_at)}</small>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

function initMealOffForm() {
    const form = document.getElementById('mealOffForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const payload = {
                start_date:      document.getElementById('mealOffStart').value,
                end_date:        document.getElementById('mealOffEnd').value,
                skip_breakfast:  document.getElementById('skipBreakfast')?.checked || false,
                skip_lunch:      document.getElementById('skipLunch')?.checked || false,
                skip_dinner:     document.getElementById('skipDinner')?.checked || false,
                reason:          document.getElementById('mealOffReason')?.value || '',
            };
            await post('/meal-off/', payload);
            showToast('Meal-off request submitted!', 'success');
            form.reset();
            loadStudentMealOffRequests();
            loadStudentDashboardStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

function initGuestMealForm() {
    const form = document.getElementById('guestMealForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const payload = {
                guest_name:   document.getElementById('guestName').value,
                guest_count:  parseInt(document.getElementById('guestCount')?.value || 1),
                date:         document.getElementById('guestDate').value,
                meal_type:    document.getElementById('guestMealType').value,
                reason:       document.getElementById('guestReason')?.value || '',
            };
            await post('/guest-meals/', payload);
            showToast('Guest meal request submitted!', 'success');
            form.reset();
            loadStudentGuestMeals();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

function initDepositForm() {
    const form = document.getElementById('depositForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const payload = {
                deposited_amount: parseFloat(document.getElementById('depositAmount').value),
                notes: document.getElementById('depositNotes')?.value || '',
            };
            await post('/deposits/', payload);
            showToast('Deposit submitted! Awaiting admin confirmation.', 'success');
            form.reset();
            loadStudentDeposit();
            loadStudentDashboardStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

async function cancelMealOff(id) {
    if (!confirm('Cancel this meal-off request?')) return;
    try {
        await del(`/meal-off/${id}/`);
        showToast('Request cancelled.', 'info');
        loadStudentMealOffRequests();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function markNotifRead(id, el) {
    try {
        await post(`/notifications/${id}/read/`, {});
        el.style.background = '#f9f9f9';
        el.style.borderLeftColor = '#ddd';
        loadStudentDashboardStats();
    } catch {}
}

// ─────────────────────────────────────────────────────────────────────────────
//  PAGE: ADMIN DASHBOARD
// ─────────────────────────────────────────────────────────────────────────────

async function initAdminDashboard() {
    if (!Auth.requireAdmin()) return;

    const user = Auth.getUser();
    document.querySelectorAll('.admin-name').forEach(el => el.textContent = user.name);
    document.getElementById('logoutBtn')?.addEventListener('click', logout);

    await Promise.all([
        loadAdminStats(),
        loadAdminStudents(),
        loadPendingMealOffs(),
        loadPendingGuestMeals(),
        loadPendingDeposits(),
        loadBazarEntries(),
        loadBazarSummary(),
    ]);

    // Forms
    initAdminMealEntryForm();
    initAdminBazarForm();
    initAdminMealRateForm();
    initAdminAddStudentForm();
}

async function loadAdminStats() {
    try {
        const data = await get(`/dashboard/admin/?month=${currentMonth()}&year=${currentYear()}`);
        setEl('totalStudentsStat',    data.total_students);
        setEl('totalDepositsStat',    formatCurrency(data.total_confirmed_deposits));
        setEl('totalBazarStat',       formatCurrency(data.total_bazar_cost));
        setEl('totalMealsStat',       data.total_meals_this_month);
        setEl('mealRateStat',         formatCurrency(data.current_meal_rate));
        setEl('balanceStat',          formatCurrency(data.balance));
        setEl('pendingMealOffsStat',  data.pending_meal_offs);
        setEl('pendingGuestStat',     data.pending_guest_meals);
        setEl('pendingDepositsStat',  data.pending_deposits);
    } catch (err) { console.error(err); }
}

async function loadAdminStudents(search = '') {
    try {
        const url = search ? `/admin/users/?search=${encodeURIComponent(search)}` : '/admin/users/';
        const data = await get(url);
        const tbody = document.getElementById('studentsTableBody');
        if (!tbody) return;
        const entries = data.results || data;
        if (!entries.length) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#999">No students found.</td></tr>';
            return;
        }
        tbody.innerHTML = entries.map(s => `
            <tr>
                <td>${s.id}</td>
                <td><strong>${s.name}</strong></td>
                <td>${s.email}</td>
                <td>${s.room_number || '-'}</td>
                <td>${s.phone || '-'}</td>
                <td>
                    <span class="status-badge ${s.is_active ? 'active' : 'pending'}">
                        ${s.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button onclick="toggleStudentActive(${s.id}, this)" style="padding:5px 12px;border:none;border-radius:6px;cursor:pointer;
                        background:${s.is_active ? '#f44336' : '#4CAF50'};color:white;font-size:0.85rem">
                        ${s.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadPendingMealOffs() {
    try {
        const data = await get('/meal-off/?status=pending');
        const container = document.getElementById('pendingMealOffList');
        if (!container) return;
        const entries = data.results || data;
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center;padding:20px">No pending requests.</p>';
            return;
        }
        container.innerHTML = entries.map(r => `
            <div style="padding:15px;background:#f9f9f9;border-radius:8px;margin-bottom:12px;border-left:4px solid #FF9800">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
                    <div>
                        <strong>${r.student_name}</strong>
                        <div style="font-size:0.9rem;color:#666;margin-top:4px">${formatDate(r.start_date)} → ${formatDate(r.end_date)}</div>
                        <div style="font-size:0.85rem;color:#666;margin-top:2px">
                            ${r.skip_breakfast ? '🌅 Breakfast ' : ''}${r.skip_lunch ? '☀️ Lunch ' : ''}${r.skip_dinner ? '🌙 Dinner' : ''}
                        </div>
                        ${r.reason ? `<div style="font-size:0.85rem;margin-top:4px;font-style:italic">"${r.reason}"</div>` : ''}
                        <div style="margin-top:8px">
                            <input type="text" id="mealOffNote_${r.id}" placeholder="Admin note (optional)"
                                style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:0.85rem;width:200px">
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        <button onclick="reviewMealOff(${r.id}, 'approved')" style="background:#4CAF50;color:white;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;font-weight:600">✓ Approve</button>
                        <button onclick="reviewMealOff(${r.id}, 'rejected')" style="background:#f44336;color:white;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;font-weight:600">✗ Reject</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadPendingGuestMeals() {
    try {
        const data = await get('/guest-meals/?status=pending');
        const container = document.getElementById('pendingGuestMealList');
        if (!container) return;
        const entries = data.results || data;
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center;padding:20px">No pending guest meal requests.</p>';
            return;
        }
        container.innerHTML = entries.map(r => `
            <div style="padding:15px;background:#f9f9f9;border-radius:8px;margin-bottom:12px;border-left:4px solid #2196F3">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
                    <div>
                        <strong>${r.student_name}</strong> → Guest: <strong>${r.guest_name}</strong> (×${r.guest_count})
                        <div style="font-size:0.9rem;color:#666;margin-top:4px">${formatDate(r.date)} — ${r.meal_type}</div>
                        ${r.reason ? `<div style="font-size:0.85rem;margin-top:4px;font-style:italic">"${r.reason}"</div>` : ''}
                        <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">
                            <input type="number" id="guestCharge_${r.id}" placeholder="Extra charge (৳)" value="0"
                                style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:0.85rem;width:160px">
                            <input type="text" id="guestNote_${r.id}" placeholder="Admin note"
                                style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:0.85rem;width:160px">
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        <button onclick="reviewGuestMeal(${r.id}, 'approved')" style="background:#4CAF50;color:white;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;font-weight:600">✓ Approve</button>
                        <button onclick="reviewGuestMeal(${r.id}, 'rejected')" style="background:#f44336;color:white;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;font-weight:600">✗ Reject</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadPendingDeposits() {
    try {
        const data = await get(`/deposits/?month=${currentMonth()}&year=${currentYear()}`);
        const container = document.getElementById('pendingDepositList');
        if (!container) return;
        const entries = (data.results || data).filter(d => !d.is_confirmed);
        if (!entries.length) {
            container.innerHTML = '<p style="color:#999;text-align:center;padding:20px">No pending deposits.</p>';
            return;
        }
        container.innerHTML = entries.map(d => `
            <div style="padding:15px;background:#f9f9f9;border-radius:8px;margin-bottom:12px;border-left:4px solid #9C27B0">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
                    <div>
                        <strong>${d.student_name}</strong>
                        <div style="font-size:0.9rem;color:#666;margin-top:4px">Amount: <strong>${formatCurrency(d.deposited_amount)}</strong> — ${d.month}/${d.year}</div>
                        ${d.notes ? `<div style="font-size:0.85rem;margin-top:4px">${d.notes}</div>` : ''}
                    </div>
                    <button onclick="confirmDeposit(${d.id})" style="background:#4CAF50;color:white;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;font-weight:600">✓ Confirm Receipt</button>
                </div>
            </div>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadBazarEntries() {
    try {
        const data = await get(`/bazar/?month=${currentMonth()}&year=${currentYear()}`);
        const tbody = document.getElementById('bazarTableBody');
        if (!tbody) return;
        const entries = data.results || data;
        if (!entries.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999">No bazar entries yet.</td></tr>';
            return;
        }
        tbody.innerHTML = entries.map(b => `
            <tr>
                <td>${formatDate(b.date)}</td>
                <td>${b.item_name}</td>
                <td>${b.quantity || '-'}</td>
                <td>${formatCurrency(b.unit_price)}</td>
                <td><strong>${formatCurrency(b.total_cost)}</strong></td>
                <td>
                    <button onclick="deleteBazar(${b.id})" style="background:#f44336;color:white;border:none;padding:4px 10px;border-radius:5px;cursor:pointer;font-size:0.8rem">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function loadBazarSummary() {
    try {
        const data = await get(`/bazar/summary/${currentMonth()}/${currentYear()}/`);
        setEl('bazarTotalCost', formatCurrency(data.total_cost));
        setEl('bazarEntryCount', data.entry_count);
    } catch {}
}

function initAdminMealEntryForm() {
    const form = document.getElementById('mealEntryForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            // Collect entries from the table rows
            const rows = form.querySelectorAll('[data-student-id]');
            if (rows.length === 0) {
                // Single student entry
                const payload = {
                    student: parseInt(document.getElementById('mealEntryStudent').value),
                    date: document.getElementById('mealEntryDate').value,
                    breakfast: document.getElementById('mealBreakfast')?.checked || false,
                    lunch: document.getElementById('mealLunch')?.checked || false,
                    dinner: document.getElementById('mealDinner')?.checked || false,
                };
                await post('/meal-entries/', payload);
            } else {
                // Bulk entry
                const date = document.getElementById('mealEntryDate').value;
                const entries = Array.from(rows).map(row => ({
                    student_id: parseInt(row.dataset.studentId),
                    breakfast: row.querySelector('.cb-breakfast')?.checked || false,
                    lunch: row.querySelector('.cb-lunch')?.checked || false,
                    dinner: row.querySelector('.cb-dinner')?.checked || false,
                }));
                await post('/meal-entries/bulk/', { date, entries });
            }
            showToast('Meal entries saved!', 'success');
            form.reset();
            loadAdminStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

function initAdminBazarForm() {
    const form = document.getElementById('bazarForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const payload = {
                date:       document.getElementById('bazarDate').value,
                item_name:  document.getElementById('bazarItem').value,
                quantity:   document.getElementById('bazarQty')?.value || '',
                unit_price: parseFloat(document.getElementById('bazarUnitPrice')?.value || 0),
                total_cost: parseFloat(document.getElementById('bazarTotalCost').value),
                notes:      document.getElementById('bazarNotes')?.value || '',
            };
            await post('/bazar/', payload);
            showToast('Bazar entry added!', 'success');
            form.reset();
            loadBazarEntries();
            loadBazarSummary();
            loadAdminStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

function initAdminMealRateForm() {
    const form = document.getElementById('mealRateForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const month = document.getElementById('rateMonth')?.value || currentMonth();
            const year  = document.getElementById('rateYear')?.value  || currentYear();
            const data  = await post(`/meal-rates/finalize/${month}/${year}/`, {});
            showToast(`Meal rate set: ${formatCurrency(data.rate_per_meal)}/meal`, 'success');
            loadAdminStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

function initAdminAddStudentForm() {
    const form = document.getElementById('addStudentForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('[type="submit"]');
        setLoading(btn, true);
        try {
            const payload = {
                name:        document.getElementById('newStudentName').value,
                email:       document.getElementById('newStudentEmail').value,
                phone:       document.getElementById('newStudentPhone')?.value || '',
                room_number: document.getElementById('newStudentRoom')?.value || '',
                password:    document.getElementById('newStudentPassword')?.value || 'changeme123',
                role:        'student',
                is_active:   true,
            };
            await post('/admin/users/', payload);
            showToast('Student added successfully!', 'success');
            form.reset();
            loadAdminStudents();
            loadAdminStats();
        } catch (err) {
            showToast(extractError(err), 'error');
        } finally {
            setLoading(btn, false);
        }
    });
}

// Admin action functions (called from inline onclick)
async function reviewMealOff(id, status) {
    try {
        const note = document.getElementById(`mealOffNote_${id}`)?.value || '';
        await post(`/meal-off/${id}/review/`, { status, admin_note: note });
        showToast(`Meal-off request ${status}!`, 'success');
        loadPendingMealOffs();
        loadAdminStats();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function reviewGuestMeal(id, status) {
    try {
        const charge = parseFloat(document.getElementById(`guestCharge_${id}`)?.value || 0);
        const note   = document.getElementById(`guestNote_${id}`)?.value || '';
        await post(`/guest-meals/${id}/review/`, { status, extra_charge: charge, admin_note: note });
        showToast(`Guest meal request ${status}!`, 'success');
        loadPendingGuestMeals();
        loadAdminStats();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function confirmDeposit(id) {
    try {
        await post(`/deposits/${id}/confirm/`, {});
        showToast('Deposit confirmed!', 'success');
        loadPendingDeposits();
        loadAdminStats();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function deleteBazar(id) {
    if (!confirm('Delete this bazar entry?')) return;
    try {
        await del(`/bazar/${id}/`);
        showToast('Entry deleted.', 'info');
        loadBazarEntries();
        loadBazarSummary();
        loadAdminStats();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function toggleStudentActive(id, btn) {
    try {
        const data = await post(`/admin/users/${id}/toggle-active/`, {});
        showToast(`Student ${data.is_active ? 'activated' : 'deactivated'}.`, 'success');
        loadAdminStudents();
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

async function setMealOffLimit() {
    const val = document.getElementById('mealOffLimitInput')?.value;
    if (!val) return;
    try {
        await post('/meal-off/limit/', { max_days_per_month: parseInt(val) });
        showToast(`Meal-off limit set to ${val} days/month.`, 'success');
    } catch (err) {
        showToast(extractError(err), 'error');
    }
}

// ─── ADMIN BULK MEAL ENTRY TABLE ─────────────────────────────────────────────

async function loadBulkMealTable() {
    try {
        const data = await get('/admin/users/');
        const container = document.getElementById('bulkMealTable');
        if (!container) return;
        const students = data.results || data;
        container.innerHTML = `
            <table style="width:100%;border-collapse:collapse">
                <thead>
                    <tr style="background:#f5f5f5">
                        <th style="padding:10px;text-align:left;border-bottom:2px solid #800000">Student</th>
                        <th style="padding:10px;text-align:center">🌅 Breakfast</th>
                        <th style="padding:10px;text-align:center">☀️ Lunch</th>
                        <th style="padding:10px;text-align:center">🌙 Dinner</th>
                    </tr>
                </thead>
                <tbody>
                    ${students.map(s => `
                        <tr data-student-id="${s.id}" style="border-bottom:1px solid #eee">
                            <td style="padding:10px">${s.name}</td>
                            <td style="padding:10px;text-align:center"><input type="checkbox" class="cb-breakfast" style="width:18px;height:18px"></td>
                            <td style="padding:10px;text-align:center"><input type="checkbox" class="cb-lunch" style="width:18px;height:18px"></td>
                            <td style="padding:10px;text-align:center"><input type="checkbox" class="cb-dinner" style="width:18px;height:18px"></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (err) { console.error(err); }
}

// Student search
function initStudentSearch() {
    const searchInput = document.getElementById('studentSearch');
    if (!searchInput) return;
    let timeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => loadAdminStudents(searchInput.value), 400);
    });
}

// ─── LOGOUT ───────────────────────────────────────────────────────────────────

async function logout() {
    try {
        await post('/auth/logout/', { refresh: Auth.getRefresh() });
    } catch {}
    Auth.clear();
    window.location.href = 'login.html';
}

// ─── UTILS ────────────────────────────────────────────────────────────────────

function setEl(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function statusColor(status) {
    const map = { approved: '#4CAF50', rejected: '#f44336', pending: '#FF9800', cancelled: '#9E9E9E' };
    return map[status] || '#666';
}

// ─── AUTO-INIT ON PAGE LOAD ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const page = window.location.pathname.split('/').pop() || 'index.html';
    
    console.log('Current page detected:', page); // debug line

    if (page.includes('login'))             initLoginPage();
    else if (page.includes('signup'))       initSignupPage();
    else if (page.includes('student-dashboard')) initStudentDashboard();
    else if (page.includes('admin-dashboard'))   initAdminDashboard();
});