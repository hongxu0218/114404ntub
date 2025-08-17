// static/js/vet/vet-home.js
// 獸醫師主頁管理系統 - 專業版

// ========== 全域變數 ==========
let vetData = {};
let scheduleData = [];
let patientsData = [];
let currentPatientFilter = 'all';
let refreshInterval = null;
let isInitialized = false;

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    if (!isInitialized) {
        initializeVetHome();
        isInitialized = true;
    }
});

// ========== 主要初始化函數 ==========
function initializeVetHome() {
    console.log('初始化獸醫師主頁...');
    
    try {
        loadVetData();
        initializeStatsCards();
        initializeTodaySchedule();
        initializeQuickActions();
        initializePatientsOverview();
        initializeFilters();
        initializeRefreshTimer();
        initializeKeyboardShortcuts();
        
        // 立即顯示空狀態，不載入任何示例數據
        setTimeout(() => {
            if (!scheduleData || scheduleData.length === 0) {
                showScheduleEmpty('今日暫無安排');
            }
            if (!patientsData || patientsData.length === 0) {
                showPatientsEmpty('暫無病患資料');
            }
        }, 100);
        
        console.log('獸醫師主頁初始化完成');
    } catch (error) {
        console.error('初始化失敗:', error);
        showErrorMessage('系統初始化失敗，請重新整理頁面');
    }
}

// ========== 載入頁面數據 ==========
function loadVetData() {
    if (window.vetData) {
        vetData = window.vetData;
        console.log('載入獸醫師數據:', vetData);
    }
}

// ========== 統計卡片功能 ==========
function initializeStatsCards() {
    try {
        addStatsCardClickHandlers();
        animateStatsCards();
        console.log('統計卡片初始化完成');
    } catch (error) {
        console.error('統計卡片初始化失敗:', error);
    }
}

function addStatsCardClickHandlers() {
    const appointmentsCard = document.querySelector('.vet-stat-card.stat-appointments');
    if (appointmentsCard) {
        appointmentsCard.style.cursor = 'pointer';
        appointmentsCard.addEventListener('click', () => {
            viewTodayAppointments();
        });
        appointmentsCard.title = '點擊查看今日預約詳情';
    }
    
    const patientsCard = document.querySelector('.vet-stat-card.stat-patients');
    if (patientsCard) {
        patientsCard.style.cursor = 'pointer';
        patientsCard.addEventListener('click', () => {
            viewMyPatients();
        });
        patientsCard.title = '點擊查看我的病患';
    }
    
    const recordsCard = document.querySelector('.vet-stat-card.stat-records');
    if (recordsCard) {
        recordsCard.style.cursor = 'pointer';
        recordsCard.addEventListener('click', () => {
            viewMedicalRecords();
        });
        recordsCard.title = '點擊查看醫療記錄';
    }
    
    const scheduleCard = document.querySelector('.vet-stat-card.stat-schedule');
    if (scheduleCard) {
        scheduleCard.style.cursor = 'pointer';
        scheduleCard.addEventListener('click', () => {
            viewScheduleManagement();
        });
        scheduleCard.title = '點擊管理我的排班';
    }
}

function animateStatsCards() {
    const statCards = document.querySelectorAll('.vet-stat-card');
    statCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.animation = 'slideInUp 0.6s ease-out forwards';
        }, index * 100);
    });
}

// ========== 今日行程功能 ==========
function initializeTodaySchedule() {
    try {
        loadTodaySchedule();
        console.log('今日行程初始化完成');
    } catch (error) {
        console.error('今日行程初始化失敗:', error);
    }
}

function loadTodaySchedule() {
    console.log('載入今日行程...');
    
    try {
        // 顯示載入狀態
        showScheduleLoading();
        
        // 嘗試調用 API
        if (vetData.urls && vetData.urls.todaySchedule) {
            fetch(`/api/vet/today-schedule/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': vetData.csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.schedule && data.schedule.length > 0) {
                    displaySchedule(data.schedule);
                } else {
                    showScheduleEmpty('今日暫無安排');
                }
            })
            .catch(error => {
                console.error('載入行程錯誤:', error);
                showScheduleEmpty('今日暫無安排');
            });
        } else {
            // 沒有 API 配置，直接顯示空狀態
            setTimeout(() => {
                showScheduleEmpty('今日暫無安排');
            }, 800);
        }
        
    } catch (error) {
        console.error('載入今日行程失敗:', error);
        showScheduleEmpty('今日暫無安排');
    }
}

function showScheduleLoading() {
    const scheduleTimeline = document.querySelector('.schedule-timeline');
    if (scheduleTimeline) {
        scheduleTimeline.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <span>載入今日行程中...</span>
            </div>
        `;
    }
}

function showScheduleEmpty(message = '今日暫無安排') {
    const scheduleTimeline = document.querySelector('.schedule-timeline');
    if (scheduleTimeline) {
        scheduleTimeline.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-calendar-x"></i>
                <h4>${message}</h4>
                <p>您今天沒有預約或排班安排</p>
                <button class="btn-vet-modern btn-vet-outline btn-sm mt-2" onclick="loadTodaySchedule()">
                    <i class="bi bi-arrow-clockwise"></i>
                    重新載入
                </button>
            </div>
        `;
    }
}

function displaySchedule(schedule) {
    const scheduleTimeline = document.querySelector('.schedule-timeline');
    if (!scheduleTimeline) return;
    
    if (!schedule || schedule.length === 0) {
        showScheduleEmpty();
        return;
    }
    
    const scheduleHTML = schedule.map(item => `
        <div class="schedule-item ${item.type} ${item.status}" onclick="viewScheduleDetail('${item.id}', '${item.type}')">
            <div class="schedule-time">${item.time}</div>
            <div class="schedule-title">${item.title}</div>
            <div class="schedule-details">
                ${item.patient ? `
                    <div class="schedule-patient">
                        <i class="bi bi-person"></i>
                        <span>${item.patient.ownerName} - ${item.patient.petName}</span>
                    </div>
                ` : ''}
                ${item.room ? `
                    <div class="schedule-room">
                        <i class="bi bi-geo-alt"></i>
                        <span>${item.room}</span>
                    </div>
                ` : ''}
                <span class="schedule-status ${item.status}">${getStatusText(item.status)}</span>
            </div>
        </div>
    `).join('');
    
    scheduleTimeline.innerHTML = scheduleHTML;
}

function getStatusText(status) {
    const statusMap = {
        'confirmed': '已確認',
        'pending': '待確認',
        'completed': '已完成',
        'cancelled': '已取消',
        'scheduled': '已安排'
    };
    return statusMap[status] || status;
}

function viewScheduleDetail(id, type) {
    console.log(`查看行程詳情: ${type} - ${id}`);
    
    if (type === 'appointment') {
        if (vetData.urls && vetData.urls.appointments) {
            window.location.href = `${vetData.urls.appointments}#appointment-${id}`;
        }
    } else if (type === 'break') {
        showInfoMessage('這是您的休息時間');
    }
}

// ========== 快速操作功能 ==========
function initializeQuickActions() {
    try {
        const quickActionCards = document.querySelectorAll('.quick-action-card');
        quickActionCards.forEach(card => {
            const actionType = card.dataset.action;
            
            card.addEventListener('click', function() {
                switch(actionType) {
                    case 'patients':
                        viewMyPatients();
                        break;
                    case 'records':
                        createMedicalRecord();
                        break;
                    case 'appointments':
                        viewTodayAppointments();
                        break;
                    case 'profile':
                        editVetProfile();
                        break;
                    default:
                        console.warn('未知的快速操作類型:', actionType);
                }
            });
        });
        
        console.log('快速操作初始化完成');
    } catch (error) {
        console.error('快速操作初始化失敗:', error);
    }
}

// ========== 病患概覽功能 ==========
function initializePatientsOverview() {
    try {
        loadPatientsOverview();
        console.log('病患概覽初始化完成');
    } catch (error) {
        console.error('病患概覽初始化失敗:', error);
    }
}

function initializeFilters() {
    try {
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                filterButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                currentPatientFilter = this.dataset.filter;
                filterPatients(currentPatientFilter);
            });
        });
        
        console.log('篩選器初始化完成');
    } catch (error) {
        console.error('篩選器初始化失敗:', error);
    }
}

function loadPatientsOverview() {
    console.log('載入病患概覽...');
    
    try {
        // 顯示載入狀態
        showPatientsLoading();
        
        // 嘗試調用 API
        if (vetData.urls && vetData.urls.myPatients) {
            fetch(`/api/vet/patients-overview/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': vetData.csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.patients && data.patients.length > 0) {
                    displayPatients(data.patients);
                } else {
                    showPatientsEmpty('暫無病患資料');
                }
            })
            .catch(error => {
                console.error('載入病患資料錯誤:', error);
                showPatientsEmpty('暫無病患資料');
            });
        } else {
            // 沒有 API 配置，直接顯示空狀態
            setTimeout(() => {
                showPatientsEmpty('暫無病患資料');
            }, 1000);
        }
        
    } catch (error) {
        console.error('載入病患概覽失敗:', error);
        showPatientsEmpty('暫無病患資料');
    }
}

function showPatientsLoading() {
    const patientsList = document.querySelector('.patients-list');
    if (patientsList) {
        patientsList.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <span>載入病患資料中...</span>
            </div>
        `;
    }
}

function showPatientsEmpty(message = '暫無病患資料') {
    const patientsList = document.querySelector('.patients-list');
    if (patientsList) {
        patientsList.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-heart"></i>
                <h4>${message}</h4>
                <p>您還沒有負責的病患</p>
                <button class="btn-vet-modern btn-vet-outline btn-sm mt-2" onclick="loadPatientsOverview()">
                    <i class="bi bi-arrow-clockwise"></i>
                    重新載入
                </button>
            </div>
        `;
    }
}

function displayPatients(patients) {
    const patientsList = document.querySelector('.patients-list');
    if (!patientsList) return;
    
    if (!patients || patients.length === 0) {
        showPatientsEmpty();
        return;
    }
    
    patientsData = patients;
    renderPatientsList(patients);
}

function renderPatientsList(patients) {
    const patientsList = document.querySelector('.patients-list');
    if (!patientsList) return;
    
    const patientsHTML = patients.map(patient => `
        <div class="patient-item" onclick="viewPatientDetail(${patient.id})">
            <div class="patient-header">
                <div class="patient-name">
                    ${patient.petName}
                    <span class="pet-species-badge">${patient.species}</span>
                </div>
                <div class="last-visit">
                    最後就診：${patient.lastVisit || '未就診'}
                </div>
            </div>
            <div class="patient-info">
                <div class="patient-info-item">
                    <i class="bi bi-person"></i>
                    <span>飼主：${patient.ownerName}</span>
                </div>
                <div class="patient-info-item">
                    <i class="bi bi-calendar"></i>
                    <span>年齡：${patient.age}</span>
                </div>
                <div class="patient-info-item">
                    <i class="bi bi-gender-ambiguous"></i>
                    <span>${patient.gender}</span>
                </div>
                <div class="patient-info-item">
                    <i class="bi bi-telephone"></i>
                    <span>${patient.ownerPhone}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    patientsList.innerHTML = patientsHTML;
}

function filterPatients(filter) {
    console.log(`篩選病患: ${filter}`);
    
    if (!patientsData || patientsData.length === 0) {
        return;
    }
    
    let filteredPatients = [...patientsData];
    
    switch(filter) {
        case 'recent':
            filteredPatients = patientsData.filter(p => p.category === 'recent');
            break;
        case 'followup':
            filteredPatients = patientsData.filter(p => p.category === 'followup');
            break;
        case 'new':
            filteredPatients = patientsData.filter(p => p.category === 'new');
            break;
        case 'all':
        default:
            // 顯示所有病患
            break;
    }
    
    renderPatientsList(filteredPatients);
}

function viewPatientDetail(patientId) {
    console.log(`查看病患詳情: ${patientId}`);
    
    if (vetData.urls && vetData.urls.patientDetail) {
        window.location.href = `${vetData.urls.patientDetail}${patientId}/`;
    } else {
        showInfoMessage('病患詳情功能開發中');
    }
}

// ========== 快速操作函數 ==========
function viewMyPatients() {
    console.log('查看我的病患');
    
    if (vetData.urls && vetData.urls.myPatients) {
        window.location.href = vetData.urls.myPatients;
    } else {
        showInfoMessage('我的病患功能開發中');
    }
}

function createMedicalRecord() {
    console.log('建立醫療記錄');
    
    if (vetData.urls && vetData.urls.createRecord) {
        window.location.href = vetData.urls.createRecord;
    } else {
        showInfoMessage('建立醫療記錄功能開發中');
    }
}

function viewTodayAppointments() {
    console.log('查看今日預約');
    
    if (vetData.urls && vetData.urls.appointments) {
        window.location.href = `${vetData.urls.appointments}?date=today`;
    } else {
        showInfoMessage('預約管理功能開發中');
    }
}

function viewMedicalRecords() {
    console.log('查看醫療記錄');
    
    if (vetData.urls && vetData.urls.medicalRecords) {
        window.location.href = vetData.urls.medicalRecords;
    } else {
        showInfoMessage('醫療記錄功能開發中');
    }
}

function viewScheduleManagement() {
    console.log('管理排班');
    
    if (vetData.urls && vetData.urls.scheduleManagement) {
        window.location.href = vetData.urls.scheduleManagement;
    } else {
        showInfoMessage('排班管理功能開發中');
    }
}

function editVetProfile() {
    console.log('編輯獸醫師檔案');
    
    if (vetData.urls && vetData.urls.profileEdit) {
        window.location.href = vetData.urls.profileEdit;
    } else {
        showInfoMessage('檔案編輯功能開發中');
    }
}

// ========== 其他初始化函數 ==========
function initializeRefreshTimer() {
    // 每 5 分鐘自動刷新數據
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(() => {
        refreshDashboardData();
    }, 300000); // 5 分鐘
    
    console.log('自動刷新功能初始化完成');
}

function initializeKeyboardShortcuts() {
    try {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + H - Home
            if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
                e.preventDefault();
                window.location.href = '/vet/home/';
            }
            
            // Ctrl/Cmd + P - Patients
            if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
                e.preventDefault();
                viewMyPatients();
            }
            
            // Ctrl/Cmd + A - Appointments
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                e.preventDefault();
                viewTodayAppointments();
            }
            
            // Ctrl/Cmd + R - Records
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                viewMedicalRecords();
            }
        });
        
        console.log('鍵盤快捷鍵初始化完成');
    } catch (error) {
        console.error('鍵盤快捷鍵初始化失敗:', error);
    }
}

// ========== 數據刷新功能 ==========
function refreshDashboardData() {
    console.log('刷新獸醫師主頁數據');
    
    try {
        loadTodaySchedule();
        loadPatientsOverview();
        
        // 更新統計數據
        if (typeof updateVetStats === 'function') {
            updateVetStats();
        }
        
    } catch (error) {
        console.error('數據刷新失敗:', error);
    }
}

// ========== 訊息提示系統 ==========
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
    
    // 添加必要的樣式
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 1rem;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        z-index: 1000;
        max-width: 400px;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    
    const messageContent = messageEl.querySelector('.message-content');
    messageContent.style.cssText = `
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-right: 2rem;
    `;
    
    const closeBtn = messageEl.querySelector('.message-close');
    closeBtn.style.cssText = `
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: none;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        color: #64748b;
    `;
    
    // 根據類型設置顏色
    const colorMap = {
        'success': '#047857',
        'error': '#dc2626',
        'warning': '#d97706',
        'info': '#0369a1'
    };
    
    const icon = messageEl.querySelector('i');
    icon.style.color = colorMap[type] || '#0369a1';
    
    document.body.appendChild(messageEl);
    
    // 顯示動畫
    setTimeout(() => {
        messageEl.style.opacity = '1';
        messageEl.style.transform = 'translateX(0)';
    }, 10);
    
    // 自動消失
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.style.opacity = '0';
            messageEl.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (messageEl.parentNode) {
                    document.body.removeChild(messageEl);
                }
            }, 300);
        }
    }, 5000);
    
    // 手動關閉
    closeBtn.addEventListener('click', () => {
        messageEl.style.opacity = '0';
        messageEl.style.transform = 'translateX(100%)';
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
}

// ========== 調試函數 ==========
function debugVetHome() {
    console.log('調試獸醫師主頁...');
    
    console.log('獸醫師數據:', vetData);
    console.log('行程數據:', scheduleData);
    console.log('病患數據:', patientsData);
    console.log('當前篩選:', currentPatientFilter);
    console.log('刷新間隔:', refreshInterval);
    
    const keyElements = {
        statsCards: document.querySelectorAll('.vet-stat-card'),
        scheduleTimeline: document.querySelector('.schedule-timeline'),
        patientsList: document.querySelector('.patients-list'),
        quickActions: document.querySelectorAll('.quick-action-card')
    };
    
    console.log('關鍵元素:', keyElements);
}

/**
 * 全域更新獸醫師統計數據函數（供外部調用）
 */
window.updateVetStats = function() {
    console.log('更新獸醫師統計數據');
    // 這裡可以添加刷新統計數據的邏輯
};

/**
 * 全域刷新獸醫師主頁函數（供外部調用）
 */
window.refreshVetDashboard = function() {
    console.log('外部調用刷新獸醫師主頁');
    refreshDashboardData();
};

// 頁面卸載時清理
window.addEventListener('beforeunload', cleanup);

// 導出全域函數
window.viewMyPatients = viewMyPatients;
window.createMedicalRecord = createMedicalRecord;
window.viewTodayAppointments = viewTodayAppointments;
window.viewMedicalRecords = viewMedicalRecords;
window.viewScheduleManagement = viewScheduleManagement;
window.editVetProfile = editVetProfile;
window.loadTodaySchedule = loadTodaySchedule;
window.loadPatientsOverview = loadPatientsOverview;
window.filterPatients = filterPatients;
window.viewPatientDetail = viewPatientDetail;
window.viewScheduleDetail = viewScheduleDetail;
window.showSuccessMessage = showSuccessMessage;
window.showErrorMessage = showErrorMessage;
window.showWarningMessage = showWarningMessage;
window.showInfoMessage = showInfoMessage;
window.debugVetHome = debugVetHome;

console.log('獸醫師主頁 JavaScript 載入完成');