/**
 * 排班管理系統 - 前端交互邏輯
 * 支援單一獸醫和團隊診所的專業排班管理
 */

// 全域變數
let currentModal = null;
let scheduleData = {};
let conflictCheckInterval = null;

/**
 * 初始化排班儀表板
 */
function initScheduleDashboard() {
    // 初始化元素
    initializeElements();
    
    // 綁定事件
    bindEvents();
    
    // 載入初始資料
    loadInitialData();
    
    // 啟動即時更新
    startRealTimeUpdates();
    
//     console.log('排班儀表板已初始化');
}

/**
 * 初始化頁面元素
 */
function initializeElements() {
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化下拉選單
    initializeDropdowns();
    
    // 初始化載入動畫
    initializeLoadingStates();
    
    // 初始化鍵盤快捷鍵
    initializeKeyboardShortcuts();
}

/**
 * 綁定事件處理器
 */
function bindEvents() {
    // 統計卡片點擊事件
    bindStatCardEvents();
    
    // 排班卡片操作事件
    bindScheduleCardEvents();
    
    // 醫師篩選事件
    bindFilterEvents();
    
    // 浮動按鈕事件
    bindFabEvents();
    
    // 頁面可見性變化事件
    bindVisibilityChangeEvents();
}

/**
 * 統計卡片事件綁定
 */
function bindStatCardEvents() {
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('click', function() {
            const cardType = this.classList.contains('personal') ? 'personal' :
                           this.classList.contains('team') ? 'team' :
                           this.classList.contains('requests') ? 'requests' : 'coverage';
            
            handleStatCardClick(cardType);
        });
        
        // 添加懸停效果
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-2px)';
        });
    });
}

/**
 * 處理統計卡片點擊
 */
function handleStatCardClick(cardType) {
    switch(cardType) {
        case 'personal':
            // 跳轉到個人排班列表
            window.location.href = '/vet/schedule/list/?filter=personal';
            break;
        case 'team':
            // 跳轉到醫師管理頁面
            window.location.href = '/clinic/doctors/';
            break;
        case 'requests':
            // 跳轉到異動申請頁面
            window.location.href = '/vet/change-requests/';
            break;
        case 'coverage':
            // 顯示覆蓋率詳情
            showCoverageDetails();
            break;
    }
}

/**
 * 排班卡片事件綁定
 */
function bindScheduleCardEvents() {
    document.querySelectorAll('.schedule-card').forEach(card => {
        // 添加點擊展開/收合功能
        const header = card.querySelector('.schedule-header');
        if (header) {
            header.addEventListener('click', function(e) {
                if (e.target.closest('.schedule-actions')) return;
                toggleScheduleCard(card);
            });
        }
        
        // 衝突警告點擊事件
        const conflictBadge = card.querySelector('.badge-warning');
        if (conflictBadge) {
            conflictBadge.addEventListener('click', function(e) {
                e.stopPropagation();
                const scheduleId = card.dataset.scheduleId;
                showConflictDetails(scheduleId);
            });
        }
    });
}

/**
 * 切換排班卡片展開狀態
 */
function toggleScheduleCard(card) {
    const details = card.querySelector('.schedule-details');
    const actions = card.querySelector('.schedule-actions');
    
    if (card.classList.contains('expanded')) {
        // 收合
        card.classList.remove('expanded');
        details.style.maxHeight = '0';
        actions.style.maxHeight = '0';
    } else {
        // 展開
        card.classList.add('expanded');
        details.style.maxHeight = details.scrollHeight + 'px';
        actions.style.maxHeight = actions.scrollHeight + 'px';
    }
}

/**
 * 篩選事件綁定
 */
function bindFilterEvents() {
    const doctorFilter = document.getElementById('doctorFilter');
    if (doctorFilter) {
//         console.log('綁定醫師篩選事件');
        doctorFilter.addEventListener('change', function() {
            const selectedDoctorId = this.value;
//             console.log('選擇醫師ID:', selectedDoctorId);
            filterClinicSchedules(selectedDoctorId);
        });
    } else {
//         console.log('單醫師模式或非管理員，跳過醫師篩選器綁定');
    }
    
    // 即時搜尋功能
    const searchInput = document.getElementById('scheduleSearch');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performScheduleSearch(this.value);
            }, 300);
        });
    }
}

/**
 * 篩選診所排班
 */
function filterClinicSchedules(doctorId) {
    const doctorCards = document.querySelectorAll('.doctor-card');
    
    doctorCards.forEach(card => {
        if (!doctorId || card.dataset.doctorId === doctorId) {
            card.style.display = 'block';
            // 添加動畫效果
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        } else {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                card.style.display = 'none';
            }, 300);
        }
    });
    
    // 更新顯示計數
    updateFilterCounter(doctorId);
}

/**
 * 浮動按鈕事件綁定
 */
function bindFabEvents() {
    const fab = document.querySelector('.fab');
    if (fab) {
//         console.log('FAB按鈕找到，綁定點擊事件');
        fab.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
//             console.log('FAB按鈕被點擊');
            toggleFabMenu();
        });
    } else {
//         console.log('FAB按鈕未找到（可能是桌面版本）');
    }
    
    // 點擊外部關閉FAB選單
    document.addEventListener('click', function(e) {
        const fabContainer = e.target.closest('.floating-actions');
        if (!fabContainer) {
            closeFabMenu();
        }
    });
}

/**
 * 切換浮動按鈕選單
 */
function toggleFabMenu() {
    const fabMenu = document.getElementById('fabMenu');
    const fab = document.querySelector('.fab');
    
    if (fabMenu.classList.contains('active')) {
        closeFabMenu();
    } else {
        openFabMenu();
    }
}

/**
 * 開啟浮動按鈕選單
 */
function openFabMenu() {
    const fabMenu = document.getElementById('fabMenu');
    const fab = document.querySelector('.fab');
    
    fabMenu.classList.add('active');
    fab.style.transform = 'rotate(45deg)';
    
    // 依序顯示選單項目
    const items = fabMenu.querySelectorAll('.fab-item');
    items.forEach((item, index) => {
        setTimeout(() => {
            item.style.transform = 'scale(1) translateX(0)';
            item.style.opacity = '1';
        }, index * 50);
    });
}

/**
 * 關閉浮動按鈕選單
 */
function closeFabMenu() {
    const fabMenu = document.getElementById('fabMenu');
    const fab = document.querySelector('.fab');
    
    if (fabMenu && fabMenu.classList.contains('active')) {
        fabMenu.classList.remove('active');
        fab.style.transform = 'rotate(0deg)';
        
        // 重置選單項目動畫
        const items = fabMenu.querySelectorAll('.fab-item');
        items.forEach(item => {
            item.style.transform = 'scale(0.8) translateX(20px)';
            item.style.opacity = '0';
        });
    }
}

/**
 * 頁面可見性變化事件
 */
function bindVisibilityChangeEvents() {
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // 頁面不可見時暫停即時更新
            pauseRealTimeUpdates();
        } else {
            // 頁面可見時恢復即時更新
            resumeRealTimeUpdates();
            // 立即刷新資料
            refreshDashboardData();
        }
    });
}

/**
 * 載入初始資料
 */
function loadInitialData() {
    // 載入統計資料
    loadStatistics();
    
    // 載入排班資料
    loadScheduleData();
    
    // 載入團隊資料（如果是團隊模式）
    if (isTeamMode()) {
        loadTeamData();
    }
    
    // 檢查排班衝突
    checkScheduleConflicts();
}

/**
 * 載入統計資料
 */
async function loadStatistics() {
    try {
        showLoadingState('.stats-grid');
        
        const response = await fetch('/api/dashboard/schedule-stats/', {
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateStatistics(data.stats);
            }
        } else {
            console.warn('統計API暫時不可用，使用預設值');
            updateStatistics({
                weekly_schedules: 0,
                monthly_hours: 0,
                pending_requests: 0,
                team_size: 1
            });
        }
        
    } catch (error) {
        console.error('載入統計資料失敗:', error);
        // 使用預設值，不顯示錯誤提示
        updateStatistics({
            weekly_schedules: 0,
            monthly_hours: 0,
            pending_requests: 0,
            team_size: 1
        });
    } finally {
        hideLoadingState('.stats-grid');
    }
}

/**
 * 更新統計資料
 */
function updateStatistics(data) {
    // 更新週排班數
    updateStatCard('.stat-card.personal', data.weekly_schedules || 0);
    
    // 更新團隊人數
    if (data.team_size !== undefined) {
        updateStatCard('.stat-card.team', data.team_size);
    }
    
    // 更新待審核申請數
    if (data.pending_requests !== undefined) {
        updateStatCard('.stat-card.requests', data.pending_requests);
    }
    
    // 更新月工時
    if (data.monthly_hours !== undefined) {
        updateStatCard('.stat-card.coverage', data.monthly_hours, '小時');
    }
}

/**
 * 更新統計卡片
 */
function updateStatCard(selector, value, suffix = '') {
    const card = document.querySelector(selector);
    if (card) {
        const valueElement = card.querySelector('h3');
        if (valueElement) {
            // 添加數字動畫效果
            animateNumber(valueElement, parseFloat(valueElement.textContent) || 0, value, suffix);
        }
    }
}

/**
 * 數字動畫效果
 */
function animateNumber(element, start, end, suffix = '') {
    const duration = 1000; // 1秒
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 使用緩動函數
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = Math.round(start + (end - start) * easeOutQuart);
        
        element.textContent = currentValue + suffix;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

/**
 * 載入排班資料
 */
async function loadScheduleData() {
    try {
        const response = await fetch('/api/dashboard/schedules/', {
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                scheduleData = data;
                updateScheduleTimeline(data.schedules);
            }
        } else {
            console.warn('排班資料API暫時不可用');
            // 使用空資料，避免錯誤
            scheduleData = { schedules: [] };
            updateScheduleTimeline([]);
        }
        
    } catch (error) {
        console.error('載入排班資料失敗:', error);
        // 使用空資料，不顯示錯誤提示
        scheduleData = { schedules: [] };
        updateScheduleTimeline([]);
    }
}

/**
 * 更新排班時間軸
 */
function updateScheduleTimeline(schedules) {
    const timeline = document.querySelector('.schedule-timeline');
    if (!timeline) return;
    
    // 如果沒有排班，顯示空狀態
    if (!schedules || schedules.length === 0) {
        timeline.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <i class="fas fa-calendar-times"></i>
                </div>
                <h3>本週尚無排班</h3>
                <p>開始建立您的工作排班，管理您的診療時間</p>
                <a href="/vet/schedule/create/" class="btn btn-primary">
                    <i class="fas fa-plus"></i>
                    建立第一個排班
                </a>
            </div>
        `;
        return;
    }
    
    // 生成時間軸項目
    const timelineHTML = schedules.map(schedule => generateTimelineItem(schedule)).join('');
    timeline.innerHTML = timelineHTML;
    
    // 重新綁定事件
    bindScheduleCardEvents();
}

/**
 * 生成時間軸項目HTML
 */
function generateTimelineItem(schedule) {
    const date = new Date(schedule.start_date);
    const day = date.getDate();
    const month = date.getMonth() + 1;
    
    const conflictClass = schedule.has_conflicts ? 'conflict' : '';
    const statusBadge = `<span class="badge badge-${schedule.status}">${schedule.status_display}</span>`;
    const conflictBadge = schedule.has_conflicts ? '<span class="badge badge-warning">衝突</span>' : '';
    
    const weekdays = schedule.weekdays.map(w => ['一', '二', '三', '四', '五', '六', '日'][w]).join(', ');
    
    return `
        <div class="timeline-item ${conflictClass}" data-schedule-id="${schedule.id}">
            <div class="timeline-date">
                <span class="day">${day}</span>
                <span class="month">${month}月</span>
            </div>
            
            <div class="timeline-content">
                <div class="schedule-card">
                    <div class="schedule-header">
                        <h4>${schedule.title}</h4>
                        <div class="schedule-badges">
                            ${statusBadge}
                            ${conflictBadge}
                        </div>
                    </div>
                    
                    <div class="schedule-details">
                        <div class="detail-item">
                            <i class="fas fa-calendar-day"></i>
                            <span>工作日：週${weekdays}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-clock"></i>
                            <span>總工時：${schedule.total_work_hours} 小時/週</span>
                        </div>
                        ${schedule.notes ? `
                        <div class="detail-item">
                            <i class="fas fa-sticky-note"></i>
                            <span>${schedule.notes.substring(0, 50)}${schedule.notes.length > 50 ? '...' : ''}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="schedule-actions">
                        <a href="/vet/schedule/${schedule.id}/" class="btn-text">
                            <i class="fas fa-eye"></i>
                            檢視詳情
                        </a>
                        ${schedule.can_delete ? `
                        <button class="btn-text text-danger" onclick="deleteSchedule(${schedule.id})">
                            <i class="fas fa-trash"></i>
                            刪除
                        </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * 檢查排班衝突
 */
async function checkScheduleConflicts() {
    if (!scheduleData.schedules) return;
    
    for (const schedule of scheduleData.schedules) {
        if (schedule.has_conflicts) {
            try {
                const response = await fetch(`/api/schedule/${schedule.id}/conflicts/`);
                if (response.ok) {
                    const conflictData = await response.json();
                    updateConflictDisplay(schedule.id, conflictData);
                }
            } catch (error) {
                console.error(`檢查排班 ${schedule.id} 衝突失敗:`, error);
            }
        }
    }
}

/**
 * 更新衝突顯示
 */
function updateConflictDisplay(scheduleId, conflictData) {
    const timelineItem = document.querySelector(`[data-schedule-id="${scheduleId}"]`);
    if (!timelineItem) return;
    
    const conflictBadge = timelineItem.querySelector('.badge-warning');
    if (conflictBadge && conflictData.conflicts.length > 0) {
        conflictBadge.textContent = `${conflictData.conflicts.length} 個衝突`;
        conflictBadge.title = conflictData.conflicts.map(c => c.message).join('\n');
    }
}

/**
 * 顯示衝突詳情
 */
async function showConflictDetails(scheduleId) {
    try {
        const response = await fetch(`/api/schedule/${scheduleId}/conflicts/`);
        if (response.ok) {
            const conflictData = await response.json();
            displayConflictModal(conflictData);
        }
    } catch (error) {
        console.error('載入衝突詳情失敗:', error);
        showToast('載入衝突詳情失敗', 'error');
    }
}

/**
 * 顯示衝突詳情彈窗
 */
function displayConflictModal(conflictData) {
    const modalHTML = `
        <div class="modal fade" id="conflictModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle text-warning"></i>
                            排班衝突詳情
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="conflict-list">
                            ${conflictData.conflicts.map(conflict => `
                                <div class="conflict-item">
                                    <div class="conflict-type">
                                        <i class="fas fa-times-circle text-danger"></i>
                                        ${getConflictTypeDisplay(conflict.type)}
                                    </div>
                                    <div class="conflict-message">${conflict.message}</div>
                                    ${conflict.schedule_title ? `
                                        <div class="conflict-related">
                                            相關排班：${conflict.schedule_title}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                        <div class="conflict-actions mt-4">
                            <p class="text-muted">
                                <i class="fas fa-info-circle"></i>
                                請修改排班設定以解決衝突，或聯絡管理員協助處理。
                            </p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">關閉</button>
                        <button type="button" class="btn btn-primary" onclick="editSchedule(${conflictData.schedule_id})">
                            <i class="fas fa-edit"></i>
                            編輯排班
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除現有的衝突彈窗
    const existingModal = document.getElementById('conflictModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新的彈窗
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // 顯示彈窗
    const modal = new bootstrap.Modal(document.getElementById('conflictModal'));
    modal.show();
}

/**
 * 取得衝突類型顯示文字
 */
function getConflictTypeDisplay(type) {
    const typeMap = {
        'doctor_time_overlap': '醫師時間重疊',
        'clinic_mode_violation': '診所模式違規',
        'resource_conflict': '資源衝突',
        'business_hours_conflict': '營業時間衝突'
    };
    
    return typeMap[type] || '未知衝突類型';
}

/**
 * 啟動即時更新
 */
function startRealTimeUpdates() {
    // 每5分鐘更新統計資料
    conflictCheckInterval = setInterval(() => {
        if (!document.hidden) {
            loadStatistics();
            checkScheduleConflicts();
        }
    }, 5 * 60 * 1000);
    
//     console.log('即時更新已啟動');
}

/**
 * 暫停即時更新
 */
function pauseRealTimeUpdates() {
    if (conflictCheckInterval) {
        clearInterval(conflictCheckInterval);
    }
}

/**
 * 恢復即時更新
 */
function resumeRealTimeUpdates() {
    if (!conflictCheckInterval) {
        startRealTimeUpdates();
    }
}

/**
 * 刷新儀表板資料
 */
function refreshDashboardData() {
    loadStatistics();
    loadScheduleData();
    if (isTeamMode()) {
        loadTeamData();
    }
}

/**
 * 工具函數
 */

/**
 * 檢查是否為團隊模式
 */
function isTeamMode() {
    return document.querySelector('.mode-badge.team') !== null;
}

/**
 * 顯示載入狀態
 */
function showLoadingState(selector) {
    const element = document.querySelector(selector);
    if (element) {
        element.classList.add('loading');
    }
}

/**
 * 隱藏載入狀態
 */
function hideLoadingState(selector) {
    const element = document.querySelector(selector);
    if (element) {
        element.classList.remove('loading');
    }
}

/**
 * 初始化工具提示
 */
function initializeTooltips() {
    // 初始化 Bootstrap 工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 初始化下拉選單
 */
function initializeDropdowns() {
//     console.log('🔧 初始化排班頁面下拉選單...');
    
    // 只處理排班頁面內的自定義下拉選單，不干預導航列的 Bootstrap 下拉選單
    const scheduleDropdowns = document.querySelectorAll('.schedule-dashboard .dropdown-toggle');
    
//     console.log(`📋 找到 ${scheduleDropdowns.length} 個排班頁面下拉選單`);
    
    scheduleDropdowns.forEach(toggle => {
        // 檢查是否已經有 Bootstrap 屬性，如果有就跳過
        if (toggle.hasAttribute('data-bs-toggle')) {
//             console.log('⏭️ 跳過 Bootstrap 下拉選單:', toggle.textContent.trim());
            return;
        }
        
//         console.log('🎯 初始化自定義下拉選單:', toggle.textContent.trim());
        
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const dropdown = this.nextElementSibling;
            if (dropdown && dropdown.classList.contains('dropdown-menu')) {
                // 關閉其他排班頁面的下拉選單
                document.querySelectorAll('.schedule-dashboard .dropdown-menu.show').forEach(menu => {
                    if (menu !== dropdown) {
                        menu.classList.remove('show');
                    }
                });
                
                // 切換當前下拉選單
                dropdown.classList.toggle('show');
//                 console.log('🔄 切換排班下拉選單:', this.textContent.trim());
            }
        });
    });
    
    // 點擊外部關閉排班頁面的下拉選單
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.schedule-dashboard .dropdown')) {
            document.querySelectorAll('.schedule-dashboard .dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
}

/**
 * 初始化載入動畫
 */
function initializeLoadingStates() {
    // 添加載入動畫CSS類
    const style = document.createElement('style');
    style.textContent = `
        .loading {
            position: relative;
            pointer-events: none;
        }
        
        .loading::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            margin: -10px 0 0 -10px;
            border: 2px solid var(--medical-primary);
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            z-index: 11;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

/**
 * 初始化鍵盤快捷鍵
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + N: 建立新排班
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/vet/schedule/create/';
        }
        
        // Ctrl/Cmd + W: 週檢視
        if ((e.ctrlKey || e.metaKey) && e.key === 'w') {
            e.preventDefault();
            window.location.href = '/vet/schedule/weekly/';
        }
        
        // ESC: 關閉彈窗和選單
        if (e.key === 'Escape') {
            closeFabMenu();
            // 關閉所有模態框
            document.querySelectorAll('.modal').forEach(modal => {
                if (modal.classList.contains('show')) {
                    bootstrap.Modal.getInstance(modal)?.hide();
                }
            });
        }
    });
}

/**
 * 通用工具函數
 */

/**
 * 取得CSRF Token
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
           '';
}

/**
 * 顯示吐司通知
 */
function showToast(message, type = 'info', duration = 3000) {
    // 創建吐司元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    // 添加到頁面
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // 顯示動畫
    setTimeout(() => toast.classList.add('show'), 100);
    
    // 自動消失
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
    
    // 點擊關閉
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    });
}

/**
 * 取得吐司圖示
 */
function getToastIcon(type) {
    const iconMap = {
        'success': 'check-circle',
        'error': 'times-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    return iconMap[type] || 'info-circle';
}

/**
 * 顯示確認彈窗
 */
function showConfirmModal(message, onConfirm, onCancel = null) {
    const modal = document.getElementById('confirmModal');
    if (!modal) return;
    
    const messageElement = document.getElementById('confirmMessage');
    const confirmButton = document.getElementById('confirmButton');
    
    messageElement.textContent = message;
    
    // 清除之前的事件監聽器
    const newConfirmButton = confirmButton.cloneNode(true);
    confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
    
    // 添加新的事件監聽器
    newConfirmButton.addEventListener('click', function() {
        if (onConfirm) onConfirm();
        bootstrap.Modal.getInstance(modal).hide();
    });
    
    // 顯示彈窗
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // 取消事件
    modal.addEventListener('hidden.bs.modal', function() {
        if (onCancel) onCancel();
    }, { once: true });
}

// 頁面卸載時清理
window.addEventListener('beforeunload', function() {
    pauseRealTimeUpdates();
});