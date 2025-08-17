// static/js/clinic/dashboard-fixed.js
// 修正版dashboard - 支援營業狀態同步

// ========== 全域變數 ==========
let dashboardData = {};
let appointmentsData = [];
let currentDateFilter = 'today';
let refreshInterval = null;
let businessStatusInterval = null;
let isInitialized = false;
let currentBusinessHours = null; // 儲存當前營業時間設定

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
    
    try {
        loadDashboardData();
        initializeStatCards();
        initializeAppointmentsList();
        initializeQuickActions();
        initializeBusinessStatus();
        initializeModals();
        initializeRefreshTimer();
        initializeKeyboardShortcuts();
        loadInitialDataSafe();
        setupBusinessHoursListener(); // 新增：設置營業時間更新監聽器
        
        console.log('✅ 診所管理中心初始化完成');
    } catch (error) {
        console.error('❌ 初始化失敗:', error);
        showErrorMessage('系統初始化失敗，請重新整理頁面');
    }
}

// ========== 載入頁面數據 ==========
function loadDashboardData() {
    if (window.dashboardData) {
        dashboardData = window.dashboardData;
        console.log('📊 載入Dashboard數據:', dashboardData);
    }
}

// ========== 營業狀態檢查（提前定義） - 修正版 ==========
function initializeBusinessStatus() {
    console.log('🏥 初始化營業狀態檢查...');
    
    try {
        // 先載入儲存的營業時間設定
        loadBusinessHoursSettings().then(() => {
            updateBusinessStatusLocal();
            
            // 每分鐘更新一次營業狀態
            if (businessStatusInterval) {
                clearInterval(businessStatusInterval);
            }
            businessStatusInterval = setInterval(updateBusinessStatusLocal, 60000);
            
            console.log('🏥 營業狀態檢查初始化完成');
        });
        
    } catch (error) {
        console.error('❌ 營業狀態初始化失敗:', error);
        setDefaultBusinessStatus();
    }
}

/**
 * 載入營業時間設定 - 新增
 */
async function loadBusinessHoursSettings() {
    try {
        let response;
        try {
            response = await fetch('/api/business-hours/get/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken()
                }
            });
        } catch (error) {
            console.warn('⚠️ 營業時間API不可用，使用預設設定');
            currentBusinessHours = getDefaultBusinessHours();
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                currentBusinessHours = data.business_hours;
                console.log('✅ 營業時間設定載入成功:', currentBusinessHours);
            } else {
                currentBusinessHours = getDefaultBusinessHours();
            }
        } else {
            currentBusinessHours = getDefaultBusinessHours();
        }
    } catch (error) {
        console.error('❌ 載入營業時間設定失敗:', error);
        // 使用預設營業時間
        currentBusinessHours = getDefaultBusinessHours();
    }
}

/**
 * 獲取預設營業時間 - 新增
 */
function getDefaultBusinessHours() {
    return {
        '0': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週一
        '1': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週二
        '2': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週三
        '3': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週四
        '4': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週五
        '5': [{ startTime: '09:00', endTime: '12:00' }], // 週六
        '6': [] // 週日休息
    };
}

/**
 * 更新營業狀態 - 修正版，使用實際的營業時間設定
 */
function updateBusinessStatusLocal() {
    const statusElement = document.getElementById('businessStatus');
    if (!statusElement) {
        console.warn('⚠️ 找不到營業狀態元素');
        return;
    }
    
    try {
        const now = new Date();
        const currentWeekday = now.getDay(); // 0=週日, 1=週一, ..., 6=週六
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        const currentTimeStr = `${currentHour.toString().padStart(2, '0')}:${currentMinute.toString().padStart(2, '0')}`;
        
        const indicator = statusElement.querySelector('.status-indicator');
        const text = statusElement.querySelector('.status-text');
        
        let isOpen = false;
        let statusText = '';
        let currentPeriod = null;
        let nextPeriod = null;
        
        // 轉換週日編號：JavaScript的0(週日)對應到我們系統的6，1-6(週一到週六)對應到0-5
        const systemWeekday = currentWeekday === 0 ? 6 : currentWeekday - 1;
        
        // 獲取今天的營業時間
        const todayHours = currentBusinessHours ? (currentBusinessHours[systemWeekday.toString()] || []) : [];
        
        console.log(`📅 今天是系統編號 ${systemWeekday}，營業時間:`, todayHours);
        
        // 檢查當前是否在營業時間內
        if (Array.isArray(todayHours)) {
            for (const period of todayHours) {
                const startTime = period.startTime;
                const endTime = period.endTime;
                
                if (startTime && endTime) {
                    if (currentTimeStr >= startTime && currentTimeStr <= endTime) {
                        isOpen = true;
                        currentPeriod = { start: startTime, end: endTime };
                        break;
                    }
                }
            }
        }
        
        if (isOpen && currentPeriod) {
            // 計算距離關門還有多久
            const endHour = parseInt(currentPeriod.end.split(':')[0]);
            const endMinute = parseInt(currentPeriod.end.split(':')[1]);
            const minutesUntilClose = (endHour * 60 + endMinute) - (currentHour * 60 + currentMinute);
            
            if (minutesUntilClose <= 60) {
                statusText = `營業中 (${minutesUntilClose}分鐘後關診)`;
            } else {
                statusText = `營業中 (至 ${currentPeriod.end} 關診)`;
            }
        } else {
            // 找下一個營業時段
            let allPeriods = [];
            
            // 收集今天剩餘的營業時段
            if (Array.isArray(todayHours)) {
                for (const period of todayHours) {
                    if (period.startTime && currentTimeStr < period.startTime) {
                        allPeriods.push({
                            day: systemWeekday,
                            start: period.startTime,
                            isToday: true
                        });
                    }
                }
            }
            
            // 如果今天沒有剩餘時段，查找未來幾天
            if (allPeriods.length === 0 && currentBusinessHours) {
                for (let i = 1; i <= 7; i++) {
                    const futureDay = (systemWeekday + i) % 7;
                    const futureDayHours = currentBusinessHours[futureDay.toString()] || [];
                    
                    if (Array.isArray(futureDayHours) && futureDayHours.length > 0) {
                        const firstPeriod = futureDayHours[0];
                        if (firstPeriod.startTime) {
                            const dayNames = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
                            allPeriods.push({
                                day: futureDay,
                                start: firstPeriod.startTime,
                                dayName: dayNames[futureDay],
                                isToday: false
                            });
                            break;
                        }
                    }
                }
            }
            
            if (allPeriods.length > 0) {
                nextPeriod = allPeriods[0];
                if (nextPeriod.isToday) {
                    const nextHour = parseInt(nextPeriod.start.split(':')[0]);
                    const nextMinute = parseInt(nextPeriod.start.split(':')[1]);
                    const minutesUntilOpen = (nextHour * 60 + nextMinute) - (currentHour * 60 + currentMinute);
                    
                    if (minutesUntilOpen <= 60) {
                        statusText = `休診中 (${minutesUntilOpen}分鐘後開診)`;
                    } else {
                        statusText = `休診中 (${nextPeriod.start} 開診)`;
                    }
                } else {
                    statusText = `休診中 (${nextPeriod.dayName} ${nextPeriod.start} 開診)`;
                }
            } else {
                statusText = '休診中';
            }
        }
        
        // 更新UI
        if (indicator) {
            indicator.className = `status-indicator ${isOpen ? 'online' : ''}`;
        }
        
        if (text) {
            text.textContent = statusText;
        }
        
        console.log(`🏥 營業狀態更新: ${isOpen ? '營業中' : '休診中'} - ${statusText}`);
        
    } catch (error) {
        console.error('❌ 更新營業狀態失敗:', error);
        setDefaultBusinessStatus();
    }
}

/**
 * 設置營業時間更新監聽器 - 新增
 */
function setupBusinessHoursListener() {
    window.addEventListener('businessHoursUpdated', function(event) {
        console.log('📡 收到營業時間更新事件，刷新營業狀態');
        
        // 更新儲存的營業時間
        if (event.detail && event.detail.businessHours) {
            currentBusinessHours = event.detail.businessHours;
        }
        
        // 立即更新營業狀態
        setTimeout(() => {
            updateBusinessStatusLocal();
        }, 500);
    });
}

/**
 * 全域更新營業狀態函數（供外部調用）- 新增
 */
window.updateBusinessStatus = function() {
    console.log('🔄 外部調用更新營業狀態');
    loadBusinessHoursSettings().then(() => {
        updateBusinessStatusLocal();
    });
};

/**
 * 獲取CSRF Token - 新增
 */
function getCSRFToken() {
    // 從cookie獲取
    let csrfToken = getCookie('csrftoken');
    
    // 從hidden input獲取（備用）
    if (!csrfToken) {
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        csrfToken = tokenInput ? tokenInput.value : '';
    }
    
    // 從全域變數獲取（備用）
    if (!csrfToken && window.dashboardData && window.dashboardData.csrfToken) {
        csrfToken = window.dashboardData.csrfToken;
    }
    
    return csrfToken;
}

/**
 * 獲取Cookie值 - 新增
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function setDefaultBusinessStatus() {
    const statusElement = document.getElementById('businessStatus');
    if (!statusElement) return;
    
    const indicator = statusElement.querySelector('.status-indicator');
    const text = statusElement.querySelector('.status-text');
    
    if (indicator) {
        indicator.className = 'status-indicator';
    }
    
    if (text) {
        text.textContent = '狀態未知';
    }
}

// ========== 統計卡片功能 ==========
function initializeStatCards() {
    try {
        addStatCardClickHandlers();
        animateStatCards();
        console.log('📈 統計卡片初始化完成');
    } catch (error) {
        console.error('❌ 統計卡片初始化失敗:', error);
    }
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
            if (dashboardData.urls && dashboardData.urls.doctors) {
                window.location.href = dashboardData.urls.doctors;
            }
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

// ========== 預約列表功能 ==========
function initializeAppointmentsList() {
    try {
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
    } catch (error) {
        console.error('❌ 預約列表初始化失敗:', error);
    }
}

function loadAppointments(dateFilter) {
    console.log(`📋 載入預約 (${dateFilter})`);
    
    try {
        // 顯示載入狀態
        showAppointmentsLoading();
        
        // 模擬 API 調用
        if (dashboardData.urls && dashboardData.urls.appointments) {
            // 實際項目中這裡應該調用 API
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
                    displayAppointments(data.appointments);
                } else {
                    showAppointmentsError(data.message || '載入預約失敗');
                }
            })
            .catch(error => {
                console.error('載入預約錯誤:', error);
                showAppointmentsError('載入預約失敗，請稍後重試');
            });
            */
        }
        
        // 暫時顯示空狀態
        setTimeout(() => {
            showEmptyAppointments(dateFilter);
        }, 800);
        
    } catch (error) {
        console.error('❌ 載入預約失敗:', error);
        showAppointmentsError('載入預約失敗，請稍後重試');
    }
}

function showAppointmentsLoading() {
    const appointmentsList = document.getElementById('appointmentsList');
    if (appointmentsList) {
        appointmentsList.innerHTML = `
            <div class="loading-placeholder">
                <div class="loading-spinner"></div>
                <span>載入預約資料中...</span>
            </div>
        `;
    }
}

function showEmptyAppointments(dateFilter) {
    const appointmentsList = document.getElementById('appointmentsList');
    if (!appointmentsList) return;
    
    const dateText = {
        'today': '今日',
        'tomorrow': '明日',
        'week': '本週'
    };
    
    appointmentsList.innerHTML = `
        <div class="empty-appointments">
            <i class="bi bi-calendar-x"></i>
            <p>${dateText[dateFilter] || '此時段'}暫無預約</p>
            <small class="text-muted">新預約會自動顯示在這裡</small>
        </div>
    `;
}

function showAppointmentsError(message) {
    const appointmentsList = document.getElementById('appointmentsList');
    if (appointmentsList) {
        appointmentsList.innerHTML = `
            <div class="empty-appointments">
                <i class="bi bi-exclamation-triangle text-warning"></i>
                <p>${message}</p>
                <button class="btn-modern btn-primary-modern btn-sm mt-2" onclick="loadAppointments('${currentDateFilter}')">
                    <i class="bi bi-arrow-clockwise"></i>
                    重新載入
                </button>
            </div>
        `;
    }
}

function displayAppointments(appointments) {
    const appointmentsList = document.getElementById('appointmentsList');
    if (!appointmentsList) return;
    
    if (!appointments || appointments.length === 0) {
        showEmptyAppointments(currentDateFilter);
        return;
    }
    
    const appointmentsHTML = appointments.map(appointment => `
        <div class="appointment-item" onclick="viewAppointmentDetail(${appointment.id})">
            <div class="appointment-header">
                <div class="appointment-time">
                    <i class="bi bi-clock"></i>
                    ${appointment.startTime}
                </div>
                <span class="appointment-status ${appointment.status}">
                    ${getStatusText(appointment.status)}
                </span>
            </div>
            <div class="appointment-info">
                <div class="appointment-row">
                    <i class="bi bi-person"></i>
                    <div class="owner-pet-info">
                        <span class="owner-name">${appointment.ownerName}</span>
                        <span class="info-separator">・</span>
                        <span class="pet-name">${appointment.petName}</span>
                    </div>
                </div>
                <div class="appointment-row">
                    <i class="bi bi-person-badge"></i>
                    <span class="doctor-info">Dr. ${appointment.doctorName}</span>
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
}

function getStatusText(status) {
    const statusMap = {
        'pending': '待確認',
        'confirmed': '已確認',
        'completed': '已完成',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

function viewAppointmentDetail(appointmentId) {
    if (dashboardData.urls && dashboardData.urls.appointments) {
        window.location.href = `${dashboardData.urls.appointments}#appointment-${appointmentId}`;
    }
}

// ========== 快速操作功能 ==========
function initializeQuickActions() {
    try {
        initializeFeatureCards();
        initializeQuickActionButtons();
        initializeSettingsButton();
        console.log('⚡ 快速操作初始化完成');
    } catch (error) {
        console.error('❌ 快速操作初始化失敗:', error);
    }
}

function initializeFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        // 特殊處理設定卡片
        if (card.classList.contains('settings-card')) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function(e) {
                // 如果點擊的是按鈕，不處理（讓按鈕自己處理）
                if (e.target.id === 'settingsButton' || e.target.closest('#settingsButton')) {
                    return;
                }
                
                e.preventDefault();
                showSettingsModal();
            });
            return; // 設定卡片不需後續處理
        }
        
        // 其他卡片的處理邏輯
        const actionBtn = card.querySelector('.btn-feature');
        if (actionBtn && actionBtn.href) {
            card.addEventListener('click', function(e) {
                if (e.target === actionBtn || actionBtn.contains(e.target)) {
                    return;
                }
                window.location.href = actionBtn.href;
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

function initializeSettingsButton() {
    try {
        const settingsButton = document.getElementById('settingsButton');
        if (settingsButton) {
            // 移除可能的舊事件監聽器
            settingsButton.removeEventListener('click', handleSettingsClick);
            
            // 添加新的事件監聽器
            settingsButton.addEventListener('click', handleSettingsClick);
            console.log('✅ 診所設定按鈕事件綁定完成');
        } else {
            console.warn('⚠️ 找不到診所設定按鈕');
        }
    } catch (error) {
        console.error('❌ 診所設定按鈕初始化失敗:', error);
    }
}

// 處理設定按鈕點擊的函數
function handleSettingsClick(e) {
    e.preventDefault();
    e.stopPropagation();
    console.log('🔧 點擊診所設定按鈕');
    showSettingsModal();
}

// ========== 快速操作函數 ==========
function showAddDoctorModal() {
    if (dashboardData.urls && dashboardData.urls.addDoctor) {
        window.location.href = dashboardData.urls.addDoctor;
    } else {
        console.error('❌ 缺少新增醫師 URL');
        showErrorMessage('無法打開新增醫師頁面');
    }
}

function showAddScheduleModal() {
    if (dashboardData.urls && dashboardData.urls.schedules) {
        window.location.href = dashboardData.urls.schedules;
    } else {
        console.error('❌ 缺少排班管理 URL');
        showErrorMessage('無法打開排班管理頁面');
    }
}

function viewTodayAppointments() {
    if (dashboardData.urls && dashboardData.urls.appointments) {
        window.location.href = `${dashboardData.urls.appointments}?date=today`;
    } else {
        console.error('❌ 缺少預約管理 URL');
        showErrorMessage('無法打開預約管理頁面');
    }
}

function viewPendingAppointments() {
    if (dashboardData.urls && dashboardData.urls.appointments) {
        window.location.href = `${dashboardData.urls.appointments}?status=pending`;
    } else {
        console.error('❌ 缺少預約管理 URL');
        showErrorMessage('無法打開預約管理頁面');
    }
}

function showNotifications() {
    window.location.href = '/notifications/';
}

// ========== Modal 管理 ==========
function initializeModals() {
    try {
        // 點擊遮罩關閉 Modal
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeModal(this);
                }
            });
        });
        
        // ESC 鍵關閉 Modal
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeAllModals();
            }
        });
        
        // 初始化標籤頁
        initializeSettingsTabs();
        console.log('🗂️ Modal 管理初始化完成');
    } catch (error) {
        console.error('❌ Modal 初始化失敗:', error);
    }
}

function initializeSettingsTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.dataset.tab;
            
            // 移除所有活躍狀態
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // 設定當前活躍狀態
            this.classList.add('active');
            
            const targetContent = document.getElementById(targetTab + 'Tab');
            if (targetContent) {
                targetContent.classList.add('active');
                
                // 如果是營業時間標籤，立即初始化
                if (targetTab === 'business') {
                    console.log('🕘 切換到營業時間標籤，開始初始化...');
                    setTimeout(() => {
                        if (typeof businessHours !== 'undefined') {
                            businessHours.initialize();
                        } else if (typeof initializeBusinessHours === 'function') {
                            initializeBusinessHours();
                        } else {
                            console.error('❌ initializeBusinessHours 函數未找到');
                            // 手動載入 business-hours.js
                            loadBusinessHoursScript();
                        }
                    }, 100);
                }
            }
        });
    });
}

function showSettingsModal() {
    console.log('🔧 顯示診所設定 Modal');
    
    try {
        const modal = document.getElementById('settingsModal');
        if (!modal) {
            console.error('❌ 找不到設定 Modal 元素');
            showErrorMessage('無法打開設定視窗：找不到Modal元素');
            return;
        }

        // 顯示 Modal
        showModal(modal);
        
        // 初始化營業時間系統
        setTimeout(() => {
            initializeBusinessHoursSystem();
        }, 300);
        
    } catch (error) {
        console.error('❌ 顯示設定 Modal 失敗:', error);
        showErrorMessage('無法打開設定視窗：' + error.message);
    }
}

// ========== 營業時間系統初始化 ==========
function initializeBusinessHoursSystem() {
    console.log('🕘 初始化營業時間系統...');
    
    try {
        const container = document.getElementById('businessHoursDays');
        if (!container) {
            console.error('❌ 找不到 businessHoursDays 容器');
            showBusinessHoursError();
            return;
        }
        
        // 檢查 business-hours.js 是否載入
        if (typeof initializeBusinessHours === 'function') {
            try {
                // 延遲初始化，確保modal完全顯示
                setTimeout(() => {
                    initializeBusinessHours();
                    console.log('✅ 營業時間系統初始化成功');
                }, 300);
            } catch (error) {
                console.error('❌ 營業時間系統初始化失敗:', error);
                showBusinessHoursError();
            }
        } else if (typeof businessHours !== 'undefined') {
            // 直接使用 businessHours 實例
            try {
                setTimeout(() => {
                    businessHours.initialize();
                    console.log('✅ 營業時間系統實例初始化成功');
                }, 300);
            } catch (error) {
                console.error('❌ 營業時間系統實例初始化失敗:', error);
                showBusinessHoursError();
            }
        } else {
            console.warn('⚠️ initializeBusinessHours 函數未載入');
            loadBusinessHoursScript();
        }
        
    } catch (error) {
        console.error('❌ 營業時間系統初始化過程發生錯誤:', error);
        showBusinessHoursError();
    }
}

// ========== 動態載入 business-hours.js ==========
function loadBusinessHoursScript() {
    console.log('📦 動態載入 business-hours.js...');
    
    // 檢查腳本是否已經載入
    if (document.querySelector('script[src*="business-hours"]')) {
        console.log('📦 business-hours.js 已載入，直接初始化');
        setTimeout(() => {
            if (typeof initializeBusinessHours === 'function') {
                initializeBusinessHours();
            } else {
                showBusinessHoursError();
            }
        }, 500);
        return;
    }
    
    // 動態創建 script 標籤
    const script = document.createElement('script');
    script.src = '/static/js/clinic/business-hours.js';
    script.onload = function() {
        console.log('✅ business-hours.js 載入成功');
        setTimeout(() => {
            if (typeof initializeBusinessHours === 'function') {
                initializeBusinessHours();
            } else {
                console.error('❌ 載入後仍無法找到 initializeBusinessHours 函數');
                showBusinessHoursError();
            }
        }, 100);
    };
    script.onerror = function() {
        console.error('❌ business-hours.js 載入失敗');
        showBusinessHoursError();
    };
    
    document.head.appendChild(script);
}

// ========== 營業時間錯誤處理 ==========
function showBusinessHoursError() {
    const container = document.getElementById('businessHoursDays');
    if (container) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <div class="d-flex align-items-center">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <div>
                        <strong>營業時間設定暫時無法載入</strong><br>
                        <small>請嘗試重新載入或聯繫技術支援</small>
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="retryBusinessHours()">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        重新載入
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="location.reload()">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        重新整理頁面
                    </button>
                </div>
            </div>
        `;
    }
}

// 重試營業時間載入
function retryBusinessHours() {
    console.log('🔄 重試載入營業時間...');
    
    if (typeof forceRenderBusinessHours === 'function') {
        forceRenderBusinessHours();
    } else if (typeof businessHours !== 'undefined') {
        businessHours.forceRenderInterface();
    } else if (typeof initializeBusinessHours === 'function') {
        initializeBusinessHours();
    } else {
        console.error('❌ 無法找到營業時間初始化函數');
        showBusinessHoursError();
    }
}

function saveClinicSettings() {
    console.log('💾 儲存診所設定...');
    
    const activeTab = document.querySelector('.tab-btn.active');
    if (!activeTab) {
        showErrorMessage('請選擇要儲存的設定分類');
        return;
    }
    
    const tabType = activeTab.dataset.tab;
    
    switch(tabType) {
        case 'basic':
            saveBasicSettings();
            break;
        case 'business':
            if (typeof saveBusinessHours === 'function') {
                const result = saveBusinessHours();
                if (result) {
                    // 設定儲存成功後關閉 Modal
                    setTimeout(() => {
                        closeSettingsModal();
                    }, 1500);
                }
            } else {
                showErrorMessage('營業時間系統尚未載入');
            }
            break;
        case 'notification':
            saveNotificationSettings();
            break;
        default:
            showErrorMessage('未知的設定類型');
    }
}

// 儲存基本設定
function saveBasicSettings() {
    console.log('💾 儲存基本設定...');
    
    const form = document.getElementById('clinicSettingsForm');
    if (!form) {
        showErrorMessage('找不到設定表單');
        return;
    }
    
    const formData = new FormData(form);
    const data = {
        clinic_phone: formData.get('clinic_phone'),
        clinic_email: formData.get('clinic_email'),
        clinic_address: formData.get('clinic_address')
    };
    
    // 簡單驗證
    if (!data.clinic_phone || !data.clinic_email) {
        showErrorMessage('請填寫所有必填欄位');
        return;
    }
    
    // 顯示載入狀態
    showSaveLoading(true);
    
    // 暫時模擬成功
    setTimeout(() => {
        showSaveLoading(false);
        showSuccessMessage('基本設定已更新');
        updateClinicInfo(data);
        setTimeout(() => {
            closeSettingsModal();
        }, 1000);
    }, 1500);
}

function saveNotificationSettings() {
    console.log('💾 儲存通知設定...');
    
    showSaveLoading(true);
    
    // 收集通知設定
    const notificationSettings = {};
    document.querySelectorAll('.notification-settings input[type="checkbox"]').forEach(checkbox => {
        notificationSettings[checkbox.name || checkbox.id] = checkbox.checked;
    });
    
    // 暫時模擬成功
    setTimeout(() => {
        showSaveLoading(false);
        showSuccessMessage('通知設定已更新');
        setTimeout(() => {
            closeSettingsModal();
        }, 1000);
    }, 1000);
}

function updateClinicInfo(data) {
    try {
        // 更新電話顯示
        const phoneElement = document.querySelector('[data-clinic-phone]');
        if (phoneElement) {
            phoneElement.textContent = data.clinic_phone;
        }
        
        // 更新信箱顯示
        const emailElement = document.querySelector('[data-clinic-email]');
        if (emailElement) {
            emailElement.textContent = data.clinic_email;
        }
        
        // 更新地址顯示
        const addressElement = document.querySelector('[data-clinic-address]');
        if (addressElement) {
            addressElement.textContent = data.clinic_address;
        }
        
        console.log('✅ 診所資訊顯示已更新');
    } catch (error) {
        console.error('❌ 更新診所資訊顯示失敗:', error);
    }
}

function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
        closeModal(modal);
    }
}

function showModal(modal) {
    if (!modal) return;
    
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
    
    // 防止背景滾動
    document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
    if (!modal) return;
    
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }, 250);
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        closeModal(modal);
    });
}

// 顯示儲存載入狀態
function showSaveLoading(show) {
    const saveButton = document.querySelector('.modal-footer .btn-primary-modern');
    if (!saveButton) return;
    
    if (show) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 儲存中...';
        saveButton.style.pointerEvents = 'none';
    } else {
        saveButton.disabled = false;
        saveButton.innerHTML = '<i class="bi bi-check me-2"></i> 儲存設定';
        saveButton.style.pointerEvents = 'auto';
    }
}

// ========== 清除所有時段功能 ==========
function clearAllSchedules() {
    if (typeof window.clearAllSchedules === 'function') {
        window.clearAllSchedules();
    } else {
        console.error('❌ clearAllSchedules 函數未找到');
        showErrorMessage('清除功能暫時無法使用');
    }
}

// ========== 其他初始化函數 ==========
function initializeRefreshTimer() {
    // 每 5 分鐘自動刷新預約列表
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(() => {
        loadAppointments(currentDateFilter);
    }, 300000); // 5 分鐘
    
    console.log('🔄 自動刷新功能初始化完成');
}

function initializeKeyboardShortcuts() {
    try {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + D - Dashboard
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                window.location.href = '/clinic/dashboard/';
            }
            
            // Ctrl/Cmd + , - Settings
            if ((e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault();
                showSettingsModal();
            }
            
            // Ctrl/Cmd + A - Appointments
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                e.preventDefault();
                viewTodayAppointments();
            }
        });
        
        console.log('⌨️ 鍵盤快捷鍵初始化完成');
    } catch (error) {
        console.error('❌ 鍵盤快捷鍵初始化失敗:', error);
    }
}

function loadInitialDataSafe() {
    console.log('📊 安全初始資料載入');
    
    try {
        updateScheduleStats({ 
            activeSchedules: '--', 
            totalSchedules: '--' 
        });
        
        console.log('📊 安全初始資料載入完成');
    } catch (error) {
        console.error('❌ 初始資料載入失敗:', error);
    }
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
    
    // 自動消失
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
    
    // 手動關閉
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
function formatDate(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function formatTime(time) {
    if (typeof time === 'string') {
        return time;
    }
    return time.toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
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
    
    // 恢復背景滾動
    document.body.style.overflow = '';
}

// ========== 調試函數 ==========
function debugSettingsButton() {
    console.log('🔍 調試診所設定按鈕...');
    
    const button = document.getElementById('settingsButton');
    const modal = document.getElementById('settingsModal');
    const container = document.getElementById('businessHoursDays');
    
    console.log('按鈕元素:', button);
    console.log('Modal元素:', modal);
    console.log('營業時間容器:', container);
    console.log('initializeBusinessHours函數:', typeof initializeBusinessHours);
    console.log('當前營業時間:', currentBusinessHours);
    
    if (button) {
        console.log('按鈕樣式:', window.getComputedStyle(button).display);
        console.log('按鈕事件:', getEventListeners ? getEventListeners(button) : '無法檢查事件');
    }
}

/**
 * 刷新dashboard統計數據 - 新增
 */
window.refreshDashboardStats = function() {
    console.log('📊 刷新dashboard統計數據');
    // 這裡可以添加刷新統計數據的邏輯
    // 例如重新載入今日預約數、待確認預約數等
};

// 頁面卸載時清理
window.addEventListener('beforeunload', cleanup);

// 導出全域函數
window.showSettingsModal = showSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.saveClinicSettings = saveClinicSettings;
window.showAddDoctorModal = showAddDoctorModal;
window.showAddScheduleModal = showAddScheduleModal;
window.viewTodayAppointments = viewTodayAppointments;
window.showNotifications = showNotifications;
window.showSuccessMessage = showSuccessMessage;
window.showErrorMessage = showErrorMessage;
window.showWarningMessage = showWarningMessage;
window.showInfoMessage = showInfoMessage;
window.debugSettingsButton = debugSettingsButton;
window.clearAllSchedules = clearAllSchedules;
window.updateBusinessStatusLocal = updateBusinessStatusLocal; // 新增
window.retryBusinessHours = retryBusinessHours; // 新增重試函數

console.log('✅ 修正版診所管理中心 JavaScript 載入完成（支援營業狀態同步）');