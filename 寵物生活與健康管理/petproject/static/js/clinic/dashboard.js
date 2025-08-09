// static/js/clinic/dashboard.js

// ========== 全域變數 ==========
let dashboardData = {};
let appointmentsData = [];
let currentDateFilter = 'today';
let refreshInterval = null;
let businessStatusInterval = null;
let isInitialized = false;

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    if (!isInitialized) {
        initializeDashboard();
        isInitialized = true;
    }
});

// ========== 主要初始化函數 ==========
function initializeDashboard() {
    console.log('🚀 初始化診所管理中心...');
    
    loadDashboardData();
    initializeStatCards();
    initializeAppointmentsList();
    initializeQuickActions();
    initializeBusinessStatus();
    initializeModals();
    initializeRefreshTimer();
    initializeKeyboardShortcuts();
    loadInitialDataSafe();
    
    console.log('✅ 診所管理中心初始化完成');
}

// ========== 載入頁面數據 ==========
function loadDashboardData() {
    if (window.dashboardData) {
        dashboardData = window.dashboardData;
        console.log('📊 載入Dashboard數據:', dashboardData);
    }
}

// ========== 統計卡片功能 ==========
function initializeStatCards() {
    addStatCardClickHandlers();
    animateStatCards();
    console.log('📈 統計卡片初始化完成');
}

function addStatCardClickHandlers() {
    const todayCard = document.querySelector('.stat-card.stat-primary');
    if (todayCard) {
        todayCard.style.cursor = 'pointer';
        todayCard.addEventListener('click', () => {
            viewTodayAppointments();
        });
        todayCard.title = '點擊查看今日預約詳情';
    }
    
    const pendingCard = document.querySelector('.stat-card.stat-warning');
    if (pendingCard) {
        pendingCard.style.cursor = 'pointer';
        pendingCard.addEventListener('click', () => {
            viewPendingAppointments();
        });
        pendingCard.title = '點擊處理待確認預約';
    }
    
    const doctorsCard = document.querySelector('.stat-card.stat-success');
    if (doctorsCard) {
        doctorsCard.style.cursor = 'pointer';
        doctorsCard.addEventListener('click', () => {
            window.location.href = dashboardData.urls.doctors;
        });
        doctorsCard.title = '點擊管理醫師團隊';
    }
}

function animateStatCards() {
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.animation = 'slideInUp 0.6s ease-out forwards';
        }, index * 100);
    });
}

function updateStatCard(cardSelector, newValue, change = null) {
    const card = document.querySelector(cardSelector);
    if (!card) return;
    
    const numberElement = card.querySelector('.stat-number');
    const changeElement = card.querySelector('.stat-change span');
    
    if (numberElement) {
        animateNumber(numberElement, parseInt(numberElement.textContent), newValue);
    }
    
    if (changeElement && change) {
        changeElement.textContent = change;
    }
}

function animateNumber(element, from, to) {
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = Math.round(from + (to - from) * easeOutQuart(progress));
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function easeOutQuart(t) {
    return 1 - (--t) * t * t * t;
}

// ========== 預約列表功能 ==========
function initializeAppointmentsList() {
    const dateButtons = document.querySelectorAll('.date-btn');
    dateButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            dateButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            currentDateFilter = this.dataset.date;
            loadAppointments(currentDateFilter);
        });
    });
    
    // 初始載入
    loadAppointments('today');
    console.log('📋 預約列表初始化完成');
}

function loadAppointments(dateFilter) {
    console.log(`📋 載入預約 (${dateFilter})`);
    
    // 顯示載入狀態
    showAppointmentsLoading();
    
    // 🔧 TODO: 啟用真實API調用
    // 目前直接顯示空狀態，等API準備好後啟用以下代碼：
    /*
    fetch(`/api/appointments/list/?date=${dateFilter}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': dashboardData.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderAppointments(data.appointments);
        } else {
            showAppointmentsError(data.message || '載入失敗');
        }
    })
    .catch(error => {
        console.error('載入預約錯誤:', error);
        showAppointmentsError('載入預約失敗，請稍後重試');
    });
    */
    
    // 暫時顯示空狀態
    setTimeout(() => {
        showEmptyAppointments(dateFilter);
    }, 500);
}

function showAppointmentsLoading() {
    const appointmentsList = document.getElementById('appointmentsList');
    appointmentsList.innerHTML = `
        <div class="loading-placeholder">
            <div class="loading-spinner"></div>
            <span>載入預約資料中...</span>
        </div>
    `;
}

function showEmptyAppointments(dateFilter) {
    const appointmentsList = document.getElementById('appointmentsList');
    
    const dateText = {
        'today': '今日',
        'tomorrow': '明日',
        'week': '本週'
    };
    
    appointmentsList.innerHTML = `
        <div class="empty-appointments">
            <i class="bi bi-calendar-x"></i>
            <p>${dateText[dateFilter] || '此時段'}暫無預約</p>
        </div>
    `;
}

function renderAppointments(appointments) {
    const appointmentsList = document.getElementById('appointmentsList');
    
    if (!appointments || appointments.length === 0) {
        appointmentsList.innerHTML = `
            <div class="empty-appointments">
                <i class="bi bi-calendar-x"></i>
                <p>此時段暫無預約</p>
            </div>
        `;
        return;
    }
    
    const appointmentsHTML = appointments.map(appointment => `
        <div class="appointment-item" data-appointment-id="${appointment.id}">
            <div class="appointment-header">
                <div class="appointment-time">
                    <i class="bi bi-clock"></i>
                    ${appointment.time}
                </div>
                <div class="appointment-status ${appointment.status}">
                    ${getStatusText(appointment.status)}
                </div>
            </div>
            <div class="appointment-info">
                <div class="appointment-row">
                    <i class="bi bi-person"></i>
                    <div class="owner-pet-info">
                        <span class="owner-name">${appointment.owner_name}</span>
                        <span class="info-separator">•</span>
                        <i class="bi bi-heart"></i>
                        <span class="pet-name">${appointment.pet_name}</span>
                    </div>
                </div>
                <div class="appointment-row">
                    <i class="bi bi-person-badge"></i>
                    <span class="doctor-info">${appointment.doctor_name}</span>
                </div>
                ${appointment.reason ? `
                <div class="appointment-row">
                    <i class="bi bi-chat-text"></i>
                    <span class="reason-info">${appointment.reason}</span>
                </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    appointmentsList.innerHTML = appointmentsHTML;
    
    // 添加點擊事件
    appointmentsList.querySelectorAll('.appointment-item').forEach(item => {
        item.addEventListener('click', function() {
            const appointmentId = this.dataset.appointmentId;
            viewAppointmentDetail(appointmentId);
        });
    });
}

function showAppointmentsError(message) {
    const appointmentsList = document.getElementById('appointmentsList');
    appointmentsList.innerHTML = `
        <div class="empty-appointments">
            <i class="bi bi-exclamation-triangle"></i>
            <p>${message}</p>
            <button class="btn-modern btn-primary-modern btn-sm mt-2" onclick="loadAppointments('${currentDateFilter}')">
                <i class="bi bi-arrow-clockwise"></i>
                重新載入
            </button>
        </div>
    `;
}

function getStatusText(status) {
    const statusMap = {
        'pending': '待確認',
        'confirmed': '已確認',
        'completed': '已完成',
        'cancelled': '已取消',
        'no_show': '未到診'
    };
    
    return statusMap[status] || status;
}

// ========== 快速操作功能 ==========
function initializeQuickActions() {
    initializeFeatureCards();
    initializeQuickActionButtons();
    console.log('⚡ 快速操作初始化完成');
}

function initializeFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        const actionBtn = card.querySelector('.btn-feature');
        if (actionBtn && actionBtn.href) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function(e) {
                if (e.target === this || !e.target.closest('.btn-feature')) {
                    window.location.href = actionBtn.href;
                }
            });
        }
    });
}

function initializeQuickActionButtons() {
    const quickActionBtns = document.querySelectorAll('.quick-action-btn');
    quickActionBtns.forEach(btn => {
        const actionTitle = btn.querySelector('.action-title');
        if (actionTitle) {
            const title = actionTitle.textContent.trim();
            
            switch(title) {
                case '新增醫師':
                    btn.addEventListener('click', showAddDoctorModal);
                    break;
                case '新增排班':
                    btn.addEventListener('click', showAddScheduleModal);
                    break;
                case '今日預約':
                    btn.addEventListener('click', viewTodayAppointments);
                    break;
                case '通知中心':
                    btn.addEventListener('click', showNotifications);
                    break;
            }
        }
    });
}

function showAddDoctorModal() {
    window.location.href = dashboardData.urls.addDoctor;
}

function showAddScheduleModal() {
    window.location.href = dashboardData.urls.schedules;
}

function viewTodayAppointments() {
    window.location.href = `${dashboardData.urls.appointments}?date=today`;
}

function viewPendingAppointments() {
    window.location.href = `${dashboardData.urls.appointments}?status=pending`;
}

function viewAppointmentDetail(appointmentId) {
    window.location.href = `${dashboardData.urls.appointments}${appointmentId}/`;
}

function showNotifications() {
    window.location.href = '/notifications/';
}

// ========== 營業狀態檢查 ==========
function initializeBusinessStatus() {
    updateBusinessStatusLocal();
    businessStatusInterval = setInterval(updateBusinessStatusLocal, 60000);
    console.log('🏥 營業狀態檢查初始化完成');
}

function updateBusinessStatusLocal() {
    const statusElement = document.getElementById('businessStatus');
    if (!statusElement) return;
    
    const now = new Date();
    const currentHour = now.getHours();
    const indicator = statusElement.querySelector('.status-indicator');
    const text = statusElement.querySelector('.status-text');
    
    let isOpen = false;
    let statusText = '';
    
    if (currentHour >= 9 && currentHour < 12) {
        isOpen = true;
        statusText = '上午診 (09:00-12:00)';
    } else if (currentHour >= 14 && currentHour < 17) {
        isOpen = true;
        statusText = '下午診 (14:00-17:00)';
    } else if (currentHour >= 18 && currentHour < 21) {
        isOpen = true;
        statusText = '晚診 (18:00-21:00)';
    } else {
        isOpen = false;
        if (currentHour >= 0 && currentHour < 9) {
            statusText = '休診中 (09:00 開診)';
        } else if (currentHour >= 12 && currentHour < 14) {
            statusText = '午休中 (14:00 開診)';
        } else if (currentHour >= 17 && currentHour < 18) {
            statusText = '休息中 (18:00 開診)';
        } else {
            statusText = '休診中 (明日 09:00 開診)';
        }
    }
    
    if (indicator) {
        indicator.className = `status-indicator ${isOpen ? 'online' : ''}`;
    }
    
    if (text) {
        text.textContent = statusText;
    }
}

// ========== Modal 管理 ==========
function initializeModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this);
            }
        });
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
    
    initializeSettingsTabs();
    console.log('🗂️ Modal 管理初始化完成');
}

function initializeSettingsTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.dataset.tab;
            
            tabButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            tabContents.forEach(content => {
                content.style.display = 'none';
            });
            
            const targetContent = document.getElementById(targetTab + 'Tab');
            if (targetContent) {
                targetContent.style.display = 'block';
            }
        });
    });
}

function showSettingsModal() {
    const modal = document.getElementById('settingsModal');
    showModal(modal);
}

function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    closeModal(modal);
}

function showModal(modal) {
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

function closeModal(modal) {
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        closeModal(modal);
    });
}

// ========== 設定管理 ==========
function saveClinicSettings() {
    const form = document.getElementById('clinicSettingsForm');
    const formData = new FormData(form);
    
    showSaveLoading(true);
    
    const data = {
        clinic_phone: formData.get('clinic_phone'),
        clinic_email: formData.get('clinic_email'),
        clinic_address: formData.get('clinic_address')
    };
    
    // 🔧 TODO: 啟用真實API調用
    // 目前模擬成功，等API準備好後啟用以下代碼：
    /*
    fetch('/api/clinic/settings/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': dashboardData.csrfToken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showSuccessMessage('診所設定已更新');
            closeSettingsModal();
            updateClinicInfo(data);
        } else {
            showErrorMessage(result.message || '更新失敗');
        }
    })
    .catch(error => {
        console.error('儲存設定錯誤:', error);
        showErrorMessage('儲存失敗，請稍後重試');
    })
    .finally(() => {
        showSaveLoading(false);
    });
    */
    
    // 暫時模擬成功
    setTimeout(() => {
        showSuccessMessage('設定功能開發中，資料未實際儲存');
        closeSettingsModal();
        showSaveLoading(false);
        updateClinicInfo(data);
    }, 1500);
}

function showSaveLoading(show) {
    const button = document.querySelector('#settingsModal .btn-primary-modern');
    
    if (show) {
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>儲存中...';
    } else {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check me-2"></i>儲存設定';
    }
}

function updateClinicInfo(newData) {
    if (newData.clinic_phone) {
        dashboardData.clinic.phone = newData.clinic_phone;
    }
    if (newData.clinic_email) {
        dashboardData.clinic.email = newData.clinic_email;
    }
    if (newData.clinic_address) {
        dashboardData.clinic.address = newData.clinic_address;
    }
    
    console.log('🔄 診所資訊已更新:', newData);
}

// ========== 自動刷新功能 ==========
function initializeRefreshTimer() {
    console.log('🔄 自動刷新功能初始化完成');
    
    // 🔧 TODO: 啟用自動刷新統計數據
    /*
    refreshInterval = setInterval(() => {
        refreshDashboardStats();
    }, 5 * 60 * 1000);
    */
}

function refreshDashboardStats() {
    // 🔧 TODO: 啟用真實API調用刷新統計
    console.log('🔄 刷新統計數據...');
}

function updateDashboardStats(newStats) {
    if (newStats.todayAppointments !== undefined) {
        updateStatCard('.stat-card.stat-primary', newStats.todayAppointments);
    }
    
    if (newStats.pendingAppointments !== undefined) {
        updateStatCard('.stat-card.stat-warning', newStats.pendingAppointments);
    }
    
    if (newStats.doctorsCount !== undefined) {
        updateStatCard('.stat-card.stat-success', newStats.doctorsCount);
    }
    
    if (newStats.totalAppointmentsThisMonth !== undefined) {
        updateStatCard('.stat-card.stat-info', newStats.totalAppointmentsThisMonth);
    }
    
    dashboardData.stats = { ...dashboardData.stats, ...newStats };
    
    if (currentDateFilter === 'today') {
        loadAppointments('today');
    }
}

// ========== 鍵盤快捷鍵 ==========
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            window.location.href = '/clinic/dashboard/';
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
            e.preventDefault();
            window.location.href = dashboardData.urls.doctors;
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            e.preventDefault();
            window.location.href = dashboardData.urls.appointments;
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            window.location.href = dashboardData.urls.schedules;
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            showSettingsModal();
        }
    });
    
    console.log('⌨️ 鍵盤快捷鍵初始化完成');
}

// ========== 初始資料載入 ==========
function loadInitialDataSafe() {
    console.log('📊 安全初始資料載入');
    
    updateScheduleStats({ 
        activeSchedules: '--', 
        totalSchedules: '--' 
    });
    
    console.log('📊 安全初始資料載入完成');
}

function updateScheduleStats(stats) {
    const activeSchedulesElement = document.getElementById('activeSchedulesCount');
    if (activeSchedulesElement && stats.activeSchedules !== undefined) {
        activeSchedulesElement.textContent = stats.activeSchedules;
    }
}

// ========== 訊息顯示系統 ==========
function showSuccessMessage(message) {
    showMessage(message, 'success');
}

function showErrorMessage(message) {
    showMessage(message, 'error');
}

function showWarningMessage(message) {
    showMessage(message, 'warning');
}

function showInfoMessage(message) {
    showMessage(message, 'info');
}

function showMessage(message, type) {
    const messageEl = document.createElement('div');
    messageEl.className = `message-toast message-${type}`;
    
    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${iconMap[type] || 'info-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="message-close">&times;</button>
    `;
    
    document.body.appendChild(messageEl);
    
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.classList.add('fade-out');
            setTimeout(() => {
                if (messageEl.parentNode) {
                    document.body.removeChild(messageEl);
                }
            }, 300);
        }
    }, 5000);
    
    messageEl.querySelector('.message-close').addEventListener('click', () => {
        messageEl.classList.add('fade-out');
        setTimeout(() => {
            if (messageEl.parentNode) {
                document.body.removeChild(messageEl);
            }
        }, 300);
    });
}

// ========== 工具函數 ==========
function formatTime(timeString) {
    return new Date(`2000-01-01T${timeString}`).toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
    });
}

// ========== 清理函數 ==========
function cleanup() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    if (businessStatusInterval) {
        clearInterval(businessStatusInterval);
        businessStatusInterval = null;
    }
}

window.addEventListener('beforeunload', cleanup);

// ========== CSS 動畫注入 ==========
const dashboardAnimationCSS = `
@keyframes slideInUp {
    from { 
        opacity: 0; 
        transform: translateY(30px); 
    }
    to { 
        opacity: 1; 
        transform: translateY(0); 
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes fadeOut {
    from { opacity: 1; transform: scale(1); }
    to { opacity: 0; transform: scale(0.95); }
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.fade-out {
    animation: fadeOut 0.3s ease-out forwards;
}

.message-toast {
    position: fixed; 
    top: 2rem; 
    right: 2rem; 
    background: white;
    padding: 1rem 1.5rem; 
    border-radius: 0.75rem;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    border-left: 4px solid; 
    z-index: 1000;
    display: flex; 
    align-items: center; 
    gap: 1rem; 
    max-width: 400px;
    animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
    from { 
        opacity: 0; 
        transform: translateX(100px); 
    }
    to { 
        opacity: 1; 
        transform: translateX(0); 
    }
}

.message-success { border-left-color: #10b981; }
.message-error { border-left-color: #ef4444; }
.message-warning { border-left-color: #f59e0b; }
.message-info { border-left-color: #06b6d4; }

.message-content { 
    display: flex; 
    align-items: center; 
    gap: 0.5rem; 
    flex: 1;
}

.message-close { 
    background: none; 
    border: none; 
    font-size: 1.25rem; 
    cursor: pointer; 
    opacity: 0.5; 
    transition: opacity 0.15s ease;
}

.message-close:hover { 
    opacity: 1; 
}

@media (max-width: 768px) {
    .message-toast {
        top: 1rem;
        right: 1rem;
        left: 1rem;
        max-width: none;
    }
}
`;

if (!document.getElementById('dashboard-animations')) {
    const style = document.createElement('style');
    style.id = 'dashboard-animations';
    style.textContent = dashboardAnimationCSS;
    document.head.appendChild(style);
}

console.log('✅ 診所管理中心 JavaScript 載入完成');