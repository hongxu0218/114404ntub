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
//     console.log('🚀 初始化診所管理中心...');
    
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
        
//         console.log('✅ 診所管理中心初始化完成');
    } catch (error) {
        console.error('❌ 初始化失敗:', error);
        showErrorMessage('系統初始化失敗，請重新整理頁面');
    }
}

// ========== 載入頁面數據 ==========
function loadDashboardData() {
    if (window.dashboardData) {
        dashboardData = window.dashboardData;
//         console.log('📊 載入Dashboard數據:', dashboardData);
    }
}

// ========== 營業狀態檢查（提前定義） - 修正版 ==========
function initializeBusinessStatus() {
//     console.log('🏥 初始化營業狀態檢查...');
    
    try {
        // 先載入儲存的營業時間設定
        loadBusinessHoursSettings().then(() => {
            updateBusinessStatusLocal();
            
            // 每分鐘更新一次營業狀態
            if (businessStatusInterval) {
                clearInterval(businessStatusInterval);
            }
            businessStatusInterval = setInterval(updateBusinessStatusLocal, 60000);
            
//             console.log('🏥 營業狀態檢查初始化完成');
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
//                 console.log('✅ 營業時間設定載入成功:', currentBusinessHours);
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
        
//         console.log(`📅 今天是系統編號 ${systemWeekday}，營業時間:`, todayHours);
        
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
        
//         console.log(`🏥 營業狀態更新: ${isOpen ? '營業中' : '休診中'} - ${statusText}`);
        
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
//         console.log('📡 收到營業時間更新事件，刷新營業狀態');
        
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
//     console.log('🔄 外部調用更新營業狀態');
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
//         console.log('📈 統計卡片初始化完成');
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
//         console.log('📋 預約列表初始化完成');
    } catch (error) {
        console.error('❌ 預約列表初始化失敗:', error);
    }
}

function loadAppointments(dateFilter) {
//     console.log(`📋 載入預約 (${dateFilter})`);
    
    try {
        // 顯示載入狀態
        showAppointmentsLoading();
        
        // API 調用
        let url = '/api/appointments/list/';
        const params = new URLSearchParams();
        
        // 根據日期篩選設定參數
        const today = new Date();
        if (dateFilter === 'today') {
            params.append('date_from', today.toISOString().split('T')[0]);
            params.append('date_to', today.toISOString().split('T')[0]);
        } else if (dateFilter === 'tomorrow') {
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            params.append('date_from', tomorrow.toISOString().split('T')[0]);
            params.append('date_to', tomorrow.toISOString().split('T')[0]);
        } else if (dateFilter === 'week') {
            const nextWeek = new Date(today);
            nextWeek.setDate(nextWeek.getDate() + 7);
            params.append('date_from', today.toISOString().split('T')[0]);
            params.append('date_to', nextWeek.toISOString().split('T')[0]);
        }
        
        url += '?' + params.toString();
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayAppointments(data.data, dateFilter);
            } else {
                showAppointmentsError(data.message || '載入預約失敗');
            }
        })
        .catch(error => {
            console.error('載入預約錯誤:', error);
            showAppointmentsError('載入預約失敗，請稍後重試');
        });
        
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
                    ${appointment.start_time} - ${appointment.end_time}
                </div>
                <span class="appointment-status ${appointment.status}">
                    ${appointment.status_display}
                </span>
            </div>
            <div class="appointment-info">
                <div class="appointment-row">
                    <i class="bi bi-person"></i>
                    <div class="owner-pet-info">
                        <span class="owner-name">${appointment.owner_name}</span>
                        <span class="info-separator">・</span>
                        <span class="pet-name">${appointment.pet_name} (${appointment.pet_species})</span>
                    </div>
                </div>
                <div class="appointment-row">
                    <i class="bi bi-person-badge"></i>
                    <span class="doctor-info">Dr. ${appointment.doctor_name}</span>
                </div>
                ${appointment.notes ? `
                <div class="appointment-row">
                    <i class="bi bi-chat-text"></i>
                    <span class="reason-info">${appointment.notes}</span>
                </div>
                ` : ''}
                ${appointment.owner_phone ? `
                <div class="appointment-row">
                    <i class="bi bi-telephone"></i>
                    <span class="phone-info">${appointment.owner_phone}</span>
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
//         console.log('⚡ 快速操作初始化完成');
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
//             console.log('✅ 診所設定按鈕事件綁定完成');
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
//     console.log('🔧 點擊診所設定按鈕');
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
//         console.log('🗂️ Modal 管理初始化完成');
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
                
                // 如果是營業時間標籤，載入營業時間表單
                if (targetTab === 'business') {
//                     console.log('🕘 切換到營業時間標籤，載入表單...');
                    setTimeout(async () => {
                        try {
                            await loadBusinessHoursForm();
//                             console.log('✅ 營業時間表單載入成功');
                        } catch (error) {
                            console.error('❌ 營業時間表單載入失敗:', error);
                        }
                    }, 100);
                }
            }
        });
    });
}

function showSettingsModal() {
//     console.log('🔧 顯示診所設定 Modal');
    
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
//     console.log('🕘 初始化營業時間系統...');
    
    try {
        const container = document.getElementById('businessHoursRows');
        if (!container) {
            console.error('❌ 找不到 businessHoursRows 容器');
            showBusinessHoursError();
            return;
        }
        
        // 使用我們新的營業時間管理系統
//         console.log('✅ 使用新的營業時間管理系統');
        
    } catch (error) {
        console.error('❌ 營業時間系統初始化過程發生錯誤:', error);
        showBusinessHoursError();
    }
}

// ========== 動態載入 business-hours.js ==========
function loadBusinessHoursScript() {
//     console.log('📦 動態載入 business-hours.js...');
    
    // 檢查腳本是否已經載入
    if (document.querySelector('script[src*="business-hours"]')) {
//         console.log('📦 business-hours.js 已載入，直接初始化');
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
//         console.log('✅ business-hours.js 載入成功');
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
    const container = document.getElementById('businessHoursRows');
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
//     console.log('🔄 重試載入營業時間...');
    
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

async function saveClinicSettings() {
//     console.log('💾 儲存診所設定...');
    
    // 調試：檢查所有 tab 按鈕
    const allTabs = document.querySelectorAll('.tab-btn');
//     console.log('🔍 找到的所有 tab 按鈕:', allTabs.length);
    allTabs.forEach((tab, index) => {
//         console.log(`Tab ${index}: ${tab.dataset.tab}, active: ${tab.classList.contains('active')}`);
    });
    
    const activeTab = document.querySelector('.tab-btn.active');
    if (!activeTab) {
//         console.log('⚠️ 沒有找到激活的 tab，嘗試使用第一個可見的內容區域');
        
        // 嘗試根據可見的內容區域判斷當前 tab
        const visibleContent = document.querySelector('.tab-content.active, .tab-content[style*="display: block"]');
        if (visibleContent) {
            const contentId = visibleContent.id;
//             console.log('📋 根據可見內容推斷的分類:', contentId);
            
            if (contentId === 'businessTab') {
                await saveBusinessHours();
                showInfoMessage('診所營業時間設定已更新');
                return;
            } else if (contentId === 'basicTab') {
                await saveBasicSettings();
                return;
            }
        }
        
        // 如果還是找不到，默認嘗試保存基本設定
//         console.log('⚠️ 無法確定當前 tab，嘗試保存基本設定...');
        await saveBasicSettings();
        return;
    }
    
    const tabType = activeTab.dataset.tab;
//     console.log('📋 當前選擇的設定分類:', tabType);
    
    try {
        switch(tabType) {
            case 'basic':
                await saveBasicSettings();
                break;
            case 'business':
                if (typeof saveBusinessHours === 'function') {
                    await saveBusinessHours();
                    // 設定儲存成功後顯示額外訊息
                    showInfoMessage('診所營業時間設定已更新');
                } else {
                    showErrorMessage('營業時間系統尚未載入');
                }
                break;
            case 'mode':
                // 診所模式切換通常是即時的，不需要額外儲存
                showInfoMessage('診所模式設定已確認');
                break;
            default:
                showErrorMessage(`未知的設定類型: ${tabType}`);
                return;
        }
        
        // 所有設定儲存成功
//         console.log('✅ 診所設定儲存完成');
        
    } catch (error) {
        console.error('❌ 儲存診所設定時發生錯誤:', error);
        showErrorMessage('儲存設定時發生錯誤');
    }
}

// 儲存基本設定
async function saveBasicSettings() {
//     console.log('💾 儲存基本設定...');
    
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
    
    try {
        // 顯示載入狀態
        showSaveLoading(true);
        showInfoMessage('正在儲存基本設定...');
        
        // 調用實際的 API 來儲存基本設定
        const response = await fetch('/api/clinic/settings/', {
            method: 'POST', 
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
//         console.log('📥 基本設定 API 響應:', result);
        
        if (!response.ok || result.status !== 'success') {
            throw new Error(result.message || '保存基本設定失敗');
        }
        
        showSaveLoading(false);
        showSuccessMessage('基本設定已更新');
        updateClinicInfo(data);
        
        // 延遲關閉設定頁面
        setTimeout(() => {
            closeSettingsModal();
        }, 1500);
        
    } catch (error) {
        showSaveLoading(false);
        console.error('❌ 儲存基本設定錯誤:', error);
        showErrorMessage('儲存基本設定時發生錯誤');
    }
}

function saveNotificationSettings() {
//     console.log('💾 儲存通知設定...');
    
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
        
//         console.log('✅ 診所資訊顯示已更新');
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
    
//     console.log('🔄 自動刷新功能初始化完成');
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
        
//         console.log('⌨️ 鍵盤快捷鍵初始化完成');
    } catch (error) {
        console.error('❌ 鍵盤快捷鍵初始化失敗:', error);
    }
}

function loadInitialDataSafe() {
//     console.log('📊 安全初始資料載入');
    
    try {
        updateScheduleStats({ 
            activeSchedules: '--', 
            totalSchedules: '--' 
        });
        
//         console.log('📊 安全初始資料載入完成');
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
//     console.log('🔍 調試診所設定按鈕...');
    
    const button = document.getElementById('settingsButton');
    const modal = document.getElementById('settingsModal');
    const container = document.getElementById('businessHoursRows');
    
//     console.log('按鈕元素:', button);
//     console.log('Modal元素:', modal);
//     console.log('營業時間容器:', container);
//     console.log('initializeBusinessHours函數:', typeof initializeBusinessHours);
//     console.log('當前營業時間:', currentBusinessHours);
    
    if (button) {
//         console.log('按鈕樣式:', window.getComputedStyle(button).display);
//         console.log('按鈕事件:', getEventListeners ? getEventListeners(button) : '無法檢查事件');
    }
}

/**
 * 刷新dashboard統計數據 - 新增
 */
window.refreshDashboardStats = function() {
//     console.log('📊 刷新dashboard統計數據');
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

// ========== 營業時間設定函數 ==========
let businessHours = null;
let timeSlots = [];

/**
 * 載入營業時間數據
 */
async function loadBusinessHoursData() {
    try {
        const response = await fetch('/api/business-hours/get/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        if (response.ok) {
            const result = await response.json();
//             console.log('📥 API 載入響應:', result);
            if (result.success && result.business_hours) {
                businessHours = result.business_hours;
//                 console.log('✅ 營業時間數據載入成功:', businessHours);
//                 console.log('📊 載入數據結構檢查:');
                Object.keys(businessHours).forEach(day => {
//                     console.log(`  Day ${day}: ${businessHours[day].length} 個時間段`);
                    businessHours[day].forEach((slot, index) => {
//                         console.log(`    ${index}: ${slot.startTime} - ${slot.endTime}`);
                    });
                });
            } else {
                businessHours = null;
//                 console.log('ℹ️ 沒有找到營業時間數據，使用空白設定');
//                 console.log('📥 完整響應內容:', result);
            }
        } else {
            businessHours = null;
            console.warn('⚠️ 載入營業時間失敗，HTTP狀態:', response.status);
            console.warn('⚠️ 響應內容:', await response.text());
        }
    } catch (error) {
        console.error('❌ 載入營業時間數據錯誤:', error);
        businessHours = null;
    }
}

/**
 * 初始化營業時間表單
 */
async function loadBusinessHoursForm(skipApiLoad = false) {
    const container = document.getElementById('businessHoursRows');
    if (!container) return;

    // 只有在不跳過 API 載入時才載入數據
    if (!skipApiLoad) {
        await loadBusinessHoursData();
    }

    const weekdays = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    
    container.innerHTML = '';

    for (let day = 0; day < 7; day++) {
        const dayHours = businessHours ? businessHours[day] : [];
        const hasHours = dayHours && dayHours.length > 0;
        
        const row = document.createElement('div');
        row.className = 'hours-row';
        row.innerHTML = `
            <div class="day-name">${weekdays[day]}</div>
            <div class="status-toggle">
                <label class="toggle-switch">
                    <input type="checkbox" ${hasHours ? 'checked' : ''} 
                           onchange="toggleDayStatus(${day})" id="day-${day}-status">
                    <span class="toggle-slider"></span>
                </label>
                <span class="status-text">${hasHours ? '營業' : '休息'}</span>
            </div>
            <div class="time-inputs" id="day-${day}-times">
                ${createTimeInputs(day, dayHours)}
            </div>
            <div class="actions">
                <button type="button" class="btn-modern btn-sm btn-success-modern" 
                        onclick="addTimeSlot(${day})" ${!hasHours ? 'disabled style="display: none;"' : ''}>
                    <i class="fas fa-plus"></i> 新增時段
                </button>
            </div>
        `;
        container.appendChild(row);
    }
}

/**
 * 創建時間輸入欄位
 */
function createTimeInputs(day, dayHours) {
    if (!dayHours || dayHours.length === 0) {
        return `
            <div class="time-slot" style="display: none;">
                <input type="time" class="form-control" value="09:00" name="start-${day}-0">
                <span>至</span>
                <input type="time" class="form-control" value="17:00" name="end-${day}-0">
                <button type="button" class="btn-modern btn-sm btn-danger-modern" 
                        onclick="removeTimeSlot(this)" disabled>
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }

    return dayHours.map((hour, index) => `
        <div class="time-slot">
            <input type="time" class="form-control" value="${hour.startTime}" name="start-${day}-${index}">
            <span>至</span>
            <input type="time" class="form-control" value="${hour.endTime}" name="end-${day}-${index}">
            <button type="button" class="btn-modern btn-sm btn-danger-modern" 
                    onclick="removeTimeSlot(this)" ${dayHours.length <= 1 ? 'disabled' : ''}>
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

/**
 * 切換日期狀態
 */
function toggleDayStatus(day) {
//     console.log('toggleDayStatus called for day:', day);
    
    const checkbox = document.getElementById(`day-${day}-status`);
    const timesContainer = document.getElementById(`day-${day}-times`);
    const statusText = checkbox?.closest('.status-toggle')?.querySelector('.status-text');
    const addButton = checkbox?.closest('.hours-row')?.querySelector('button');
    
    if (!checkbox || !timesContainer) {
        console.error('Required elements not found for day:', day);
        return;
    }
    
    if (checkbox.checked) {
        if (statusText) statusText.textContent = '營業';
        timesContainer.style.display = 'block';
        timesContainer.querySelectorAll('.time-slot').forEach(slot => {
            slot.style.display = 'flex';
        });
        if (addButton) {
            addButton.disabled = false;
            addButton.style.display = 'block';
        }
    } else {
        if (statusText) statusText.textContent = '休息';
        timesContainer.style.display = 'none';
        if (addButton) {
            addButton.disabled = true;
            addButton.style.display = 'none'; // 休息時隱藏新增按鈕
        }
    }
}

/**
 * 新增時間段
 */
function addTimeSlot(day) {
    const container = document.getElementById(`day-${day}-times`);
    const existingSlots = container.querySelectorAll('.time-slot');
    const index = existingSlots.length;
    
    const newSlot = document.createElement('div');
    newSlot.className = 'time-slot';
    newSlot.innerHTML = `
        <input type="time" class="form-control" value="13:00" name="start-${day}-${index}">
        <span>至</span>
        <input type="time" class="form-control" value="17:00" name="end-${day}-${index}">
        <button type="button" class="btn-modern btn-sm btn-danger-modern" onclick="removeTimeSlot(this)">
            <i class="fas fa-trash"></i>
        </button>
    `;
    container.appendChild(newSlot);
    
    // 啟用所有刪除按鈕
    container.querySelectorAll('.btn-danger-modern').forEach(btn => btn.disabled = false);
}

/**
 * 移除時間段
 */
function removeTimeSlot(button) {
    const slot = button.closest('.time-slot');
    const container = slot.parentElement;
    slot.remove();
    
    // 如果只剩一個時間段，禁用刪除按鈕
    const remainingSlots = container.querySelectorAll('.time-slot');
    if (remainingSlots.length <= 1) {
        remainingSlots.forEach(slot => {
            slot.querySelector('.btn-danger-modern').disabled = true;
        });
    }
}

/**
 * 套用營業時間模板
 */
async function applyBusinessTemplate(templateType) {
//     console.log('🎯 套用營業時間模板:', templateType);
    
    const templates = {
        'weekday_only': {
            0: [{ startTime: '09:00', endTime: '18:00' }], // 週一
            1: [{ startTime: '09:00', endTime: '18:00' }], // 週二
            2: [{ startTime: '09:00', endTime: '18:00' }], // 週三
            3: [{ startTime: '09:00', endTime: '18:00' }], // 週四
            4: [{ startTime: '09:00', endTime: '18:00' }], // 週五
            5: [], // 週六
            6: []  // 週日
        },
        'weekend_half': {
            0: [{ startTime: '09:00', endTime: '18:00' }],
            1: [{ startTime: '09:00', endTime: '18:00' }],
            2: [{ startTime: '09:00', endTime: '18:00' }],
            3: [{ startTime: '09:00', endTime: '18:00' }],
            4: [{ startTime: '09:00', endTime: '18:00' }],
            5: [{ startTime: '09:00', endTime: '12:00' }], // 週六上午
            6: []
        },
        'full_week': {
            0: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            1: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            2: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            3: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            4: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            5: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }],
            6: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '13:00', endTime: '17:00' }]
        }
    };
    
    const template = templates[templateType];
    if (template) {
        businessHours = template;
        
        // 重新載入表單以顯示模板數據（跳過 API 載入）
        await loadBusinessHoursForm(true);
        
        const templateNames = {
            'weekday_only': '平日營業 (週一至週五)',
            'weekend_half': '週末半天 (週六上午)',
            'full_week': '全週營業'
        };
        
        showSuccessMessage(`已套用「${templateNames[templateType]}」模板`);
//         console.log('✅ 模板套用成功:', template);
    } else {
        console.error('❌ 找不到模板:', templateType);
        showErrorMessage('模板套用失敗');
    }
}

/**
 * 同步包裝函數以支持 onclick 調用
 */
function applyBusinessTemplateSync(templateType) {
    applyBusinessTemplate(templateType).catch(error => {
        console.error('❌ 套用模板錯誤:', error);
        showErrorMessage('套用模板時發生錯誤');
    });
}

/**
 * 收集營業時間數據
 */
function collectBusinessHoursData() {
//     console.log('📊 開始收集營業時間數據...');
    const hoursData = {};
    
    for (let day = 0; day < 7; day++) {
        const checkbox = document.getElementById(`day-${day}-status`);
        const timesContainer = document.getElementById(`day-${day}-times`);
        
//         console.log(`Day ${day}: checkbox=${!!checkbox}, checked=${checkbox?.checked}, container=${!!timesContainer}`);
        
        if (checkbox && checkbox.checked && timesContainer) {
            const timeSlots = timesContainer.querySelectorAll('.time-slot');
            hoursData[day] = [];
            
//             console.log(`Day ${day}: 找到 ${timeSlots.length} 個時間段`);
            
            timeSlots.forEach((slot, index) => {
                const startInput = slot.querySelector(`[name="start-${day}-${index}"]`);
                const endInput = slot.querySelector(`[name="end-${day}-${index}"]`);
                
                if (startInput && endInput && startInput.value && endInput.value) {
                    hoursData[day].push({
                        startTime: startInput.value,
                        endTime: endInput.value
                    });
//                     console.log(`  時間段 ${index}: ${startInput.value} - ${endInput.value}`);
                }
            });
        } else {
//             console.log(`Day ${day}: 休息日或未勾選`);
        }
    }
    
//     console.log('📊 收集到的營業時間數據:', hoursData);
    return hoursData;
}

/**
 * 儲存營業時間
 */
async function saveBusinessHours() {
    const hoursData = collectBusinessHoursData();
    
//     console.log('🔄 準備儲存營業時間數據:', hoursData);
//     console.log('📊 數據結構檢查:');
    Object.keys(hoursData).forEach(day => {
//         console.log(`  Day ${day}: ${hoursData[day].length} 個時間段`);
        hoursData[day].forEach((slot, index) => {
//             console.log(`    ${index}: ${slot.startTime} - ${slot.endTime}`);
        });
    });
    
    try {
        showInfoMessage('保存營業時間中...');
        
        const requestData = { business_hours: hoursData };
//         console.log('📤 發送請求數據:', requestData);
        
        const response = await fetch('/api/business-hours/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(requestData)
        });
        
//         console.log('📥 API 響應狀態:', response.status);
        
        const result = await response.json();
//         console.log('📥 API 響應數據:', result);
        
        if (response.ok && result.success) {
            showSuccessMessage('營業時間保存成功！');
            businessHours = hoursData;
            // 不要重新載入表單，避免覆蓋當前設定，直接使用已更新的 businessHours
//             console.log('✅ 營業時間已更新到內存中，無需重新載入表單');
            // 延遲關閉設定頁面
            setTimeout(() => {
                closeSettingsModal();
            }, 1500);
        } else {
            showErrorMessage(result.message || '保存失敗');
        }
    } catch (error) {
        console.error('保存營業時間錯誤:', error);
        showErrorMessage('保存時發生錯誤');
    }
}

/**
 * 獲取 CSRF Token
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
           getCookie('csrftoken');
}

/**
 * 獲取 Cookie 值
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

// 初始化診所設定tabs和營業時間編輯器
document.addEventListener('DOMContentLoaded', function() {
//     console.log('🔄 初始化診所設定系統...');
    
    // 添加 tab 切換邏輯
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
//     console.log(`找到 ${tabButtons.length} 個 tab 按鈕, ${tabContents.length} 個內容區域`);
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.dataset.tab;
//             console.log('🔄 切換到 tab:', targetTab);
            
            // 移除所有 active 狀態
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // 添加當前 active 狀態
            this.classList.add('active');
            const targetContent = document.getElementById(targetTab + 'Tab');
            if (targetContent) {
                targetContent.classList.add('active');
                
                // 如果切換到營業時間 tab，載入表單
                if (targetTab === 'business') {
                    setTimeout(async () => {
                        await loadBusinessHoursForm();
                    }, 100);
                }
            }
        });
    });
    
    // 頁面載入時預先載入營業時間數據
//     console.log('🔄 頁面載入時初始化營業時間數據...');
    loadBusinessHoursData().then(() => {
//         console.log('✅ 頁面載入時營業時間數據初始化完成');
    }).catch(error => {
        console.error('❌ 頁面載入時營業時間數據初始化失敗:', error);
    });
    
    // 如果默認顯示營業時間 tab，也要載入表單
    const businessContent = document.getElementById('businessTab');
    if (businessContent && businessContent.classList.contains('active')) {
        setTimeout(async () => {
            await loadBusinessHoursForm();
        }, 100);
    }
});

// 導出營業時間相關函數
window.loadBusinessHoursForm = loadBusinessHoursForm;
window.toggleDayStatus = toggleDayStatus;
window.addTimeSlot = addTimeSlot;
window.removeTimeSlot = removeTimeSlot;
window.applyBusinessTemplate = applyBusinessTemplate;
window.applyBusinessTemplateSync = applyBusinessTemplateSync;
window.saveBusinessHours = saveBusinessHours;

// console.log('✅ 修正版診所管理中心 JavaScript 載入完成（支援營業狀態同步）');