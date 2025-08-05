// static/js/clinic/schedule-management.js

// ========== 全域變數 ==========
let schedulesData = [];
let filteredSchedules = [];
let currentView = 'calendar';
let currentFilter = 'all';
let editingScheduleId = null;
let pageData = {};

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeScheduleManagement();
});

// ========== 主要初始化函數 ==========
function initializeScheduleManagement() {
    console.log('🚀 初始化排班管理系統...');
    
    // 載入頁面數據
    loadPageData();
    
    // 初始化各種功能
    initializeViewToggle();
    initializeFilters();
    initializeCalendarView();
    initializeListView();
    initializeModals();
    initializeFormValidation();
    initializeActionButtons();
    initializeKeyboardShortcuts();
    
    // 載入並渲染排班資料
    loadSchedulesData();
    renderSchedules();
    
    console.log('✅ 排班管理系統初始化完成');
}

// ========== 載入頁面數據 ==========
function loadPageData() {
    if (window.schedulePageData) {
        pageData = window.schedulePageData;
        schedulesData = pageData.schedules || [];
        filteredSchedules = [...schedulesData];
        console.log('📊 載入頁面數據:', pageData);
    }
}

// ========== 檢視切換功能 ==========
function initializeViewToggle() {
    const viewToggles = document.querySelectorAll('.view-toggle');
    
    viewToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const view = this.dataset.view;
            switchView(view);
            
            // 更新按鈕狀態
            viewToggles.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function switchView(view) {
    currentView = view;
    
    // 隱藏所有檢視
    document.querySelectorAll('.schedule-view').forEach(v => v.classList.remove('active'));
    
    // 顯示目標檢視
    const targetView = document.getElementById(view + 'View');
    if (targetView) {
        targetView.classList.add('active');
        
        // 根據檢視類型渲染內容
        if (view === 'calendar') {
            renderCalendarView();
        } else if (view === 'list') {
            renderListView();
        }
    }
    
    console.log(`🔄 切換到 ${view} 檢視`);
}

// ========== 篩選功能 ==========
function initializeFilters() {
    const filterChips = document.querySelectorAll('.filter-chip');
    
    filterChips.forEach(chip => {
        chip.addEventListener('click', function() {
            // 移除其他 active 狀態
            filterChips.forEach(c => c.classList.remove('active'));
            
            // 設定當前 active
            this.classList.add('active');
            
            // 更新篩選條件
            currentFilter = this.dataset.filter;
            
            // 應用篩選
            filterSchedules();
            
            // 視覺回饋
            animateFilterChange(this);
        });
    });
}

function filterSchedules() {
    filteredSchedules = schedulesData.filter(schedule => {
        if (currentFilter === 'all') return true;
        if (currentFilter === 'active') return schedule.isActive;
        if (currentFilter === 'morning') return isTimeInPeriod(schedule.startTime, 'morning');
        if (currentFilter === 'evening') return isTimeInPeriod(schedule.startTime, 'afternoon');
        return true;
    });
    
    renderSchedules();
    updateScheduleStats();
    
    console.log(`🔍 篩選結果: ${filteredSchedules.length}/${schedulesData.length}`);
}

function isTimeInPeriod(timeString, period) {
    const hour = parseInt(timeString.split(':')[0]);
    
    if (period === 'morning') {
        return hour >= 6 && hour < 12;
    } else if (period === 'afternoon') {
        return hour >= 12 && hour < 18;
    } else if (period === 'evening') {
        return hour >= 18 && hour < 22;
    }
    
    return false;
}

// ========== 行事曆檢視 ==========
function initializeCalendarView() {
    // 初始化行事曆相關事件監聽
    console.log('📅 初始化行事曆檢視');
}

function renderCalendarView() {
    console.log('🎨 渲染行事曆檢視');
    
    // 清除現有的排班區塊
    clearCalendarSchedules();
    
    // 更新日期統計
    updateDayCounters();
    
    // 渲染排班區塊
    filteredSchedules.forEach(schedule => {
        renderScheduleBlock(schedule);
    });
}

function clearCalendarSchedules() {
    document.querySelectorAll('.schedule-block').forEach(block => {
        block.remove();
    });
}

function renderScheduleBlock(schedule) {
    const timeCell = findTimeCellForSchedule(schedule);
    if (!timeCell) return;
    
    const block = document.createElement('div');
    block.className = `schedule-block ${schedule.isActive ? '' : 'inactive'}`;
    block.dataset.scheduleId = schedule.id;
    
    block.innerHTML = `
        <div class="schedule-time">${schedule.startTime}-${schedule.endTime}</div>
        <div>${schedule.appointmentDuration}min</div>
    `;
    
    // 計算高度（基於持續時間）
    const duration = calculateDurationMinutes(schedule.startTime, schedule.endTime);
    const slotHeight = 60; // 每小時的像素高度
    const height = (duration / 60) * slotHeight - 4; // 減去 margin
    
    block.style.height = `${height}px`;
    
    // 添加點擊事件
    block.addEventListener('click', () => {
        if (pageData.canEdit) {
            editSchedule(schedule.id);
        }
    });
    
    timeCell.appendChild(block);
}

function findTimeCellForSchedule(schedule) {
    const hour = schedule.startTime.split(':')[0].padStart(2, '0') + ':00';
    return document.querySelector(`[data-weekday="${schedule.weekday}"][data-time="${hour}"]`);
}

function calculateDurationMinutes(startTime, endTime) {
    const [startHour, startMin] = startTime.split(':').map(Number);
    const [endHour, endMin] = endTime.split(':').map(Number);
    
    return (endHour * 60 + endMin) - (startHour * 60 + startMin);
}

function updateDayCounters() {
    for (let day = 0; day <= 6; day++) {
        const daySchedules = filteredSchedules.filter(s => s.weekday === day);
        const counter = document.getElementById(`dayCount${day}`);
        if (counter) {
            counter.textContent = `${daySchedules.length} 個排班`;
        }
    }
}

// ========== 列表檢視 ==========
function initializeListView() {
    console.log('📋 初始化列表檢視');
}

function renderListView() {
    console.log('🎨 渲染列表檢視');
    // 列表檢視由伺服器端渲染，這裡主要處理篩選顯示
    
    const scheduleCards = document.querySelectorAll('.schedule-card-modern');
    
    scheduleCards.forEach(card => {
        const scheduleId = parseInt(card.dataset.scheduleId);
        const shouldShow = filteredSchedules.some(s => s.id === scheduleId);
        
        if (shouldShow) {
            showScheduleCard(card);
        } else {
            hideScheduleCard(card);
        }
    });
}

function showScheduleCard(card) {
    card.style.display = 'block';
    card.style.animation = 'fadeInUp 0.3s ease-out';
}

function hideScheduleCard(card) {
    card.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => {
        card.style.display = 'none';
    }, 300);
}

// ========== Modal 管理 ==========
function initializeModals() {
    // Modal 外部點擊關閉
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeAllModals();
            }
        });
    });
    
    // ESC 鍵關閉 Modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

function showAddScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    const form = document.getElementById('scheduleForm');
    const title = document.getElementById('modalTitle');
    const saveButton = document.getElementById('saveButtonText');
    
    // 重設表單
    form.reset();
    document.getElementById('scheduleId').value = '';
    editingScheduleId = null;
    
    // 設定標題
    title.textContent = '新增排班';
    saveButton.textContent = '儲存排班';
    
    // 顯示 Modal
    showModal(modal);
    
    console.log('➕ 開啟新增排班 Modal');
}

function editSchedule(scheduleId) {
    const schedule = schedulesData.find(s => s.id === scheduleId);
    if (!schedule) return;
    
    const modal = document.getElementById('scheduleModal');
    const form = document.getElementById('scheduleForm');
    const title = document.getElementById('modalTitle');
    const saveButton = document.getElementById('saveButtonText');
    
    // 填入現有資料
    document.getElementById('scheduleId').value = schedule.id;
    document.getElementById('weekday').value = schedule.weekday;
    document.getElementById('startTime').value = schedule.startTime;
    document.getElementById('endTime').value = schedule.endTime;
    document.getElementById('appointmentDuration').value = schedule.appointmentDuration;
    document.getElementById('maxAppointments').value = schedule.maxAppointmentsPerSlot;
    document.getElementById('notes').value = schedule.notes || '';
    
    editingScheduleId = scheduleId;
    
    // 設定標題
    title.textContent = '編輯排班';
    saveButton.textContent = '更新排班';
    
    // 顯示預覽
    updateSchedulePreview();
    
    // 顯示 Modal
    showModal(modal);
    
    console.log('✏️ 開啟編輯排班 Modal:', schedule);
}

function showCopyWeekModal() {
    const modal = document.getElementById('copyWeekModal');
    showModal(modal);
    console.log('📋 開啟複製排班 Modal');
}

function showModal(modal) {
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    closeModal(modal);
}

function closeCopyWeekModal() {
    const modal = document.getElementById('copyWeekModal');
    closeModal(modal);
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

// ========== 表單驗證 ==========
function initializeFormValidation() {
    const form = document.getElementById('scheduleForm');
    
    // 即時預覽
    const timeInputs = form.querySelectorAll('input[type="time"], select');
    timeInputs.forEach(input => {
        input.addEventListener('change', updateSchedulePreview);
    });
    
    // 時間驗證
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    
    endTimeInput.addEventListener('change', function() {
        validateTimeRange();
    });
}

function validateTimeRange() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    
    if (startTime && endTime && startTime >= endTime) {
        showFormError('結束時間必須晚於開始時間');
        return false;
    }
    
    clearFormErrors();
    return true;
}

function updateSchedulePreview() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const duration = parseInt(document.getElementById('appointmentDuration').value);
    
    if (!startTime || !endTime || !duration) {
        hideSchedulePreview();
        return;
    }
    
    if (!validateTimeRange()) {
        hideSchedulePreview();
        return;
    }
    
    const slots = generateTimeSlots(startTime, endTime, duration);
    renderSchedulePreview(slots);
}

function generateTimeSlots(startTime, endTime, duration) {
    const slots = [];
    const [startHour, startMin] = startTime.split(':').map(Number);
    const [endHour, endMin] = endTime.split(':').map(Number);
    
    let currentMinutes = startHour * 60 + startMin;
    const endMinutes = endHour * 60 + endMin;
    
    while (currentMinutes + duration <= endMinutes) {
        const slotStart = formatMinutesToTime(currentMinutes);
        const slotEnd = formatMinutesToTime(currentMinutes + duration);
        
        slots.push(`${slotStart}-${slotEnd}`);
        currentMinutes += duration;
    }
    
    return slots;
}

function formatMinutesToTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

function renderSchedulePreview(slots) {
    const preview = document.getElementById('schedulePreview');
    const slotsContainer = document.getElementById('previewSlots');
    
    slotsContainer.innerHTML = '';
    
    slots.forEach(slot => {
        const slotElement = document.createElement('div');
        slotElement.className = 'preview-slot';
        slotElement.textContent = slot;
        slotsContainer.appendChild(slotElement);
    });
    
    preview.style.display = 'block';
}

function hideSchedulePreview() {
    const preview = document.getElementById('schedulePreview');
    preview.style.display = 'none';
}

// ========== 儲存排班 ==========
function saveSchedule() {
    const form = document.getElementById('scheduleForm');
    const formData = new FormData(form);
    
    // 驗證表單
    if (!validateScheduleForm()) {
        return;
    }
    
    // 顯示載入狀態
    showSaveLoading(true);
    
    // 準備 AJAX 資料
    const data = {
        weekday: formData.get('weekday'),
        start_time: formData.get('start_time'),
        end_time: formData.get('end_time'),
        appointment_duration: formData.get('appointment_duration'),
        max_appointments_per_slot: formData.get('max_appointments_per_slot'),
        notes: formData.get('notes') || ''
    };
    
    // 決定 URL 和方法
    const isEditing = !!editingScheduleId;
    const url = isEditing 
        ? pageData.urls.editSchedule.replace('{id}', editingScheduleId)
        : pageData.urls.addSchedule;
    
    console.log(`💾 ${isEditing ? '更新' : '新增'}排班:`, data);
    
    // 發送請求
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': pageData.csrfToken,
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showSuccessMessage(result.message);
            closeScheduleModal();
            
            // 重新載入頁面或更新資料
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(result.message || '操作失敗');
            if (result.errors) {
                showFormErrors(result.errors);
            }
        }
    })
    .catch(error => {
        console.error('儲存排班錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    })
    .finally(() => {
        showSaveLoading(false);
    });
}

function validateScheduleForm() {
    const requiredFields = ['weekday', 'start_time', 'end_time', 'appointment_duration', 'max_appointments_per_slot'];
    
    for (const field of requiredFields) {
        const element = document.getElementById(field.replace('_', ''));
        if (!element || !element.value) {
            showFormError(`請填寫${element?.labels?.[0]?.textContent || field}`);
            element?.focus();
            return false;
        }
    }
    
    return validateTimeRange();
}

function showSaveLoading(show) {
    const button = document.querySelector('#scheduleModal .btn-primary-modern');
    const buttonText = document.getElementById('saveButtonText');
    
    if (show) {
        button.disabled = true;
        buttonText.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>儲存中...';
    } else {
        button.disabled = false;
        buttonText.innerHTML = editingScheduleId ? 
            '<i class="bi bi-check me-2"></i>更新排班' : 
            '<i class="bi bi-check me-2"></i>儲存排班';
    }
}

// ========== 快速新增排班 ==========
function quickAddSchedule(weekday, timeString) {
    const hour = parseInt(timeString.split(':')[0]);
    const startTime = `${hour.toString().padStart(2, '0')}:00`;
    const endTime = `${(hour + 1).toString().padStart(2, '0')}:00`;
    
    // 開啟新增 Modal 並預填資料
    showAddScheduleModal();
    
    // 預填資料
    setTimeout(() => {
        document.getElementById('weekday').value = weekday;
        document.getElementById('startTime').value = startTime;
        document.getElementById('endTime').value = endTime;
        updateSchedulePreview();
    }, 100);
    
    console.log(`⚡ 快速新增排班: 星期${weekday + 1} ${startTime}-${endTime}`);
}

// ========== 操作按鈕功能 ==========
function initializeActionButtons() {
    // 啟用/停用排班按鈕
    initializeToggleButtons();
    
    // 其他操作按鈕
    initializeOtherActionButtons();
}

function initializeToggleButtons() {
    const toggleButtons = document.querySelectorAll('.toggle-schedule-btn');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            handleToggleScheduleStatus(this);
        });
    });
}

function handleToggleScheduleStatus(button) {
    const scheduleId = button.dataset.scheduleId;
    const action = button.dataset.action;
    const isDeactivating = action === 'deactivate';
    
    // 顯示確認對話框
    showConfirmDialog({
        title: isDeactivating ? '停用排班' : '啟用排班',
        message: `確定要${isDeactivating ? '停用' : '啟用'}此排班嗎？`,
        confirmText: isDeactivating ? '停用' : '啟用',
        confirmClass: isDeactivating ? 'btn-warning' : 'btn-success',
        onConfirm: () => {
            executeToggleScheduleStatus(button, scheduleId);
        }
    });
}

function executeToggleScheduleStatus(button, scheduleId) {
    const card = button.closest('.schedule-card-modern');
    
    // 顯示載入狀態
    showCardLoading(card);
    
    // 發送 AJAX 請求
    fetch(pageData.urls.toggleSchedule.replace('{id}', scheduleId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': pageData.csrfToken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message);
            
            // 更新本地資料
            updateScheduleStatusInData(scheduleId, data.is_active);
            
            // 重新渲染
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(data.message || '操作失敗');
        }
    })
    .catch(error => {
        console.error('切換排班狀態錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    })
    .finally(() => {
        hideCardLoading(card);
    });
}

function updateScheduleStatusInData(scheduleId, newStatus) {
    const schedule = schedulesData.find(s => s.id === parseInt(scheduleId));
    if (schedule) {
        schedule.isActive = newStatus;
    }
    
    // 重新篩選
    filterSchedules();
}

function initializeOtherActionButtons() {
    // 複製排班按鈕已在 HTML 中定義 onclick
    console.log('🔘 其他操作按鈕已初始化');
}

// ========== 複製排班功能 ==========
function copySchedule(scheduleId) {
    const schedule = schedulesData.find(s => s.id === scheduleId);
    if (!schedule) return;
    
    // 開啟新增 Modal 並複製資料
    showAddScheduleModal();
    
    setTimeout(() => {
        document.getElementById('weekday').value = schedule.weekday;
        document.getElementById('startTime').value = schedule.startTime;
        document.getElementById('endTime').value = schedule.endTime;
        document.getElementById('appointmentDuration').value = schedule.appointmentDuration;
        document.getElementById('maxAppointments').value = schedule.maxAppointmentsPerSlot;
        document.getElementById('notes').value = schedule.notes || '';
        
        updateSchedulePreview();
    }, 100);
    
    console.log('📋 複製排班:', schedule);
}

function executeCopyWeek() {
    const copySource = document.querySelector('input[name="copySource"]:checked')?.value;
    const overwrite = document.getElementById('overwriteExisting').checked;
    
    if (!copySource) {
        showErrorMessage('請選擇複製來源');
        return;
    }
    
    showConfirmDialog({
        title: '確認複製排班',
        message: `確定要複製${copySource === 'last_week' ? '上週排班' : '排班範本'}嗎？${overwrite ? '將覆蓋現有排班。' : ''}`,
        confirmText: '開始複製',
        onConfirm: () => {
            performCopyWeek(copySource, overwrite);
        }
    });
}

function performCopyWeek(source, overwrite) {
    closeCopyWeekModal();
    
    // 發送複製請求
    fetch(pageData.urls.copyWeek, {
        method: 'POST',
        headers: {
            'X-CSRFToken': pageData.csrfToken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            source: source,
            overwrite: overwrite
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message);
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(data.message || '複製失敗');
        }
    })
    .catch(error => {
        console.error('複製排班錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    });
}

// ========== 刪除排班 ==========
function deleteSchedule(scheduleId) {
    const schedule = schedulesData.find(s => s.id === scheduleId);
    if (!schedule) return;
    
    showConfirmDialog({
        title: '刪除排班',
        message: `確定要刪除「${schedule.weekdayDisplay} ${schedule.startTime}-${schedule.endTime}」的排班嗎？此操作無法復原。`,
        confirmText: '刪除',
        confirmClass: 'btn-danger',
        onConfirm: () => {
            executeDeleteSchedule(scheduleId);
        }
    });
}

function executeDeleteSchedule(scheduleId) {
    fetch(pageData.urls.deleteSchedule.replace('{id}', scheduleId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': pageData.csrfToken,
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message);
            
            // 移除本地資料
            schedulesData = schedulesData.filter(s => s.id !== parseInt(scheduleId));
            filterSchedules();
            
            // 移除 DOM 元素
            const card = document.querySelector(`[data-schedule-id="${scheduleId}"]`);
            if (card) {
                card.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    card.remove();
                }, 300);
            }
        } else {
            showErrorMessage(data.message || '刪除失敗');
        }
    })
    .catch(error => {
        console.error('刪除排班錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    });
}

// ========== 鍵盤快捷鍵 ==========
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + N: 新增排班
        if ((e.ctrlKey || e.metaKey) && e.key === 'n' && pageData.canEdit) {
            e.preventDefault();
            showAddScheduleModal();
        }
        
        // Ctrl/Cmd + 1/2: 切換檢視
        if ((e.ctrlKey || e.metaKey) && e.key === '1') {
            e.preventDefault();
            switchView('calendar');
            document.querySelector('[data-view="calendar"]').click();
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === '2') {
            e.preventDefault();
            switchView('list');
            document.querySelector('[data-view="list"]').click();
        }
    });
}

// ========== 工具函數 ==========

function loadSchedulesData() {
    // 資料已在頁面載入時注入，這裡處理資料初始化
    filteredSchedules = [...schedulesData];
    console.log('📊 載入排班資料:', schedulesData);
}

function renderSchedules() {
    if (currentView === 'calendar') {
        renderCalendarView();
    } else {
        renderListView();
    }
}

function updateScheduleStats() {
    const statsElement = document.getElementById('scheduleStats');
    if (statsElement) {
        const total = schedulesData.length;
        const visible = filteredSchedules.length;
        
        let text = '';
        if (currentFilter !== 'all') {
            text = `顯示 ${visible} / ${total} 個排班`;
        } else {
            text = `共 ${total} 個排班`;
        }
        
        statsElement.textContent = text;
    }
}

function animateFilterChange(chip) {
    chip.style.transform = 'scale(1.1)';
    setTimeout(() => {
        chip.style.transform = 'scale(1)';
    }, 150);
}

// ========== 載入和錯誤處理（繼承自 doctor-management.js） ==========
function showCardLoading(card) {
    let overlay = card.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="loading-spinner-modern"></div>';
        card.appendChild(overlay);
    }
    overlay.classList.add('show');
}

function hideCardLoading(card) {
    const overlay = card.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

function showConfirmDialog(options) {
    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog-overlay';
    dialog.innerHTML = `
        <div class="confirm-dialog">
            <h3>${options.title}</h3>
            <p>${options.message}</p>
            <div class="dialog-buttons">
                <button class="btn-cancel">取消</button>
                <button class="btn-confirm ${options.confirmClass || 'btn-primary'}">${options.confirmText}</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    dialog.querySelector('.btn-cancel').addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
    
    dialog.querySelector('.btn-confirm').addEventListener('click', () => {
        options.onConfirm();
        document.body.removeChild(dialog);
    });
    
    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    });
}

function showSuccessMessage(message) {
    showMessage(message, 'success');
}

function showErrorMessage(message) {
    showMessage(message, 'error');
}

function showMessage(message, type) {
    const messageEl = document.createElement('div');
    messageEl.className = `message-toast message-${type}`;
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
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

function showFormError(message) {
    const errorEl = document.querySelector('.form-error') || document.createElement('div');
    errorEl.className = 'form-error';
    errorEl.textContent = message;
    errorEl.style.color = 'var(--danger-color)';
    errorEl.style.fontSize = '0.875rem';
    errorEl.style.marginTop = 'var(--spacing-sm)';
    
    if (!document.querySelector('.form-error')) {
        document.querySelector('.modal-body').appendChild(errorEl);
    }
}

function clearFormErrors() {
    const errorEl = document.querySelector('.form-error');
    if (errorEl) {
        errorEl.remove();
    }
}

function showFormErrors(errors) {
    Object.keys(errors).forEach(field => {
        const input = document.getElementById(field);
        if (input) {
            input.style.borderColor = 'var(--danger-color)';
            // 可以添加更多錯誤顯示邏輯
        }
    });
}

// ========== CSS 動畫注入（如果需要） ==========
const scheduleAnimationCSS = `
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeOut {
    from { opacity: 1; transform: scale(1); }
    to { opacity: 0; transform: scale(0.95); }
}

.fade-out {
    animation: fadeOut 0.3s ease-out forwards;
}

.confirm-dialog-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.5); display: flex;
    align-items: center; justify-content: center; z-index: 1000;
}

.confirm-dialog {
    background: white; padding: 2rem; border-radius: 1rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    max-width: 400px; width: 90%;
}

.dialog-buttons {
    display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1.5rem;
}

.message-toast {
    position: fixed; top: 2rem; right: 2rem; background: white;
    padding: 1rem 1.5rem; border-radius: 0.75rem;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    border-left: 4px solid; z-index: 1000;
    display: flex; align-items: center; gap: 1rem; max-width: 400px;
}

.message-success { border-left-color: #10b981; }
.message-error { border-left-color: #ef4444; }

.message-content { display: flex; align-items: center; gap: 0.5rem; }
.message-close { background: none; border: none; font-size: 1.25rem; cursor: pointer; opacity: 0.5; }
.message-close:hover { opacity: 1; }
`;

// 注入 CSS
if (!document.getElementById('schedule-animations')) {
    const style = document.createElement('style');
    style.id = 'schedule-animations';
    style.textContent = scheduleAnimationCSS;
    document.head.appendChild(style);
}

console.log('✅ 排班管理 JavaScript 載入完成');