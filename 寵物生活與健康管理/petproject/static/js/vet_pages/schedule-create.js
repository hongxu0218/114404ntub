/**
 * 排班建立頁面 - 前端交互邏輯
 * 支援動態時段設定、即時預覽、衝突檢測等功能
 */

// 全域變數
let selectedWeekdays = new Set();
let timeSlotData = {};
let previewUpdateTimeout = null;
let conflictCheckTimeout = null;

/**
 * 初始化排班建立頁面
 */
function initScheduleCreatePage() {
    // 初始化事件監聽器
    initializeEventListeners();
    
    // 載入預設設定
    loadDefaultSettings();
    
    // 初始化時段設定
    initializeTimeSlots();
    
    // 設定表單驗證
    setupFormValidation();
}

/**
 * 載入既有排班資料 (用於編輯頁面)
 */
function loadExistingScheduleData(scheduleData) {
//     console.log('loadExistingScheduleData called with:', scheduleData);
    
    if (!scheduleData || typeof scheduleData !== 'object') {
//         console.log('No existing schedule data to load');
        return;
    }
    
    // 載入時段資料到全域變數
    timeSlotData = scheduleData || {};
//     console.log('timeSlotData set to:', timeSlotData);
    
    // 初始化已選工作日（從 DOM 中的 checked 複選框讀取）
    selectedWeekdays.clear();
    document.querySelectorAll('.weekdays-selection input[type="checkbox"]:checked').forEach(checkbox => {
        const day = parseInt(checkbox.value);
        selectedWeekdays.add(day);
//         console.log(`Added day ${day} to selectedWeekdays`);
    });
//     console.log('selectedWeekdays initialized to:', Array.from(selectedWeekdays));
    
    // 更新時段容器以顯示既有時段
    updateTimeSlotsContainer();
    
    // 為每個工作日載入既有時段
    Object.keys(timeSlotData).forEach(day => {
        const dayNum = parseInt(day);
        if (selectedWeekdays.has(dayNum)) {
            const slots = timeSlotData[day];
            if (slots && slots.length > 0) {
//                 console.log(`Loading ${slots.length} slots for day ${day}`);
                
                // 確保該日的容器存在
                const container = document.querySelector(`[data-day="${day}"]`);
                if (container) {
                    // 清空現有時段項目（保留容器結構）
                    container.querySelectorAll('.time-slot-item').forEach(item => item.remove());
                    
                    // 為每個時段添加 HTML
                    slots.forEach(slot => {
//                         console.log(`Adding slot ${slot.start}-${slot.end} for day ${day}`);
                        addTimeSlotToContainer(day, slot.start, slot.end);
                    });
                }
            }
        }
    });
    
    // 更新預覽
    updatePreview();
//     console.log('loadExistingScheduleData completed');
}

/**
 * 添加時段到指定容器
 */
function addTimeSlotToContainer(day, startTime, endTime) {
    const container = document.querySelector(`[data-day="${day}"]`);
    if (!container) {
        console.error(`Container not found for day ${day}`);
        return;
    }
    
    // 獲取時段項目模板
    const template = document.getElementById('timeSlotItemTemplate');
    if (!template) {
        console.error('Time slot item template not found');
        return;
    }
    
    // 複製模板
    const slotItem = template.content.cloneNode(true);
    
    // 設定時間值
    const startInput = slotItem.querySelector('.start-time');
    const endInput = slotItem.querySelector('.end-time');
    
    if (startInput && endInput) {
        startInput.value = startTime;
        endInput.value = endTime;
    }
    
    // 添加事件監聽器
    const slotElement = slotItem.querySelector('.time-slot-item');
    if (slotElement) {
        // 為時間輸入框添加事件監聽器
        slotElement.querySelectorAll('.start-time, .end-time').forEach(input => {
            input.addEventListener('change', () => {
                updateTimeSlotData(day);
                debouncePreviewUpdate();
            });
        });
        
        // 為刪除按鈕添加事件監聽器
        const removeBtn = slotElement.querySelector('.btn-danger');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                removeTimeSlot(this);
            });
        }
    }
    
    // 添加到容器
    container.appendChild(slotItem);
    
    // 更新時段資料到全域變數
    updateTimeSlotData(day);
    
//     console.log(`Added time slot ${startTime}-${endTime} to day ${day}`);
}

/**
 * 初始化批量時段設定功能
 */
function initBatchTimeFeature() {
//     console.log('initBatchTimeFeature called');
    
    // 檢查批量時段設定面板是否存在
    const batchPanel = document.getElementById('batchTimePanel');
    if (!batchPanel) {
//         console.log('Batch time panel not found, skipping batch feature initialization');
        return;
    }
    
    // 模板選擇事件
    const templateButtons = document.querySelectorAll('.template-btn');
//     console.log(`Found ${templateButtons.length} template buttons`);
    
    templateButtons.forEach((btn, index) => {
//         console.log(`Template button ${index}:`, btn.dataset.template);
        btn.addEventListener('click', function() {
//             console.log('Template button clicked:', this.dataset.template);
            
            // 清除其他選中狀態
            document.querySelectorAll('.template-btn').forEach(b => b.classList.remove('selected'));
            
            // 設定當前選中
            this.classList.add('selected');
            selectedTemplate = this.dataset.template;
            
            // 顯示/隱藏自訂時段面板
            const customPanel = document.getElementById('customTemplate');
            if (customPanel) {
                if (selectedTemplate === 'custom') {
                    customPanel.style.display = 'block';
                } else {
                    customPanel.style.display = 'none';
                }
            }
            
//             console.log('Selected template:', selectedTemplate);
        });
    });
    
    // 批量套用按鈕事件 - 處理已選工作日按鈕
    const selectedDaysBtn = document.querySelector('[onclick*="applyToSelectedDays"]');
    if (selectedDaysBtn) {
        selectedDaysBtn.removeAttribute('onclick');
        selectedDaysBtn.addEventListener('click', applyToSelectedDays);
//         console.log('Added event listener to selected days button');
    }
    
    // 批量套用按鈕事件 - 處理週一至週五和週末按鈕
    const specificDaysButtons = document.querySelectorAll('[onclick*="applyToSpecificDays"]');
//     console.log(`Found ${specificDaysButtons.length} specific days buttons`);
    
    specificDaysButtons.forEach((btn, index) => {
        const onclickAttr = btn.getAttribute('onclick');
//         console.log(`Button ${index} onclick:`, onclickAttr);
        
        if (onclickAttr) {
            btn.removeAttribute('onclick');
            
            // 解析參數
            const match = onclickAttr.match(/applyToSpecificDays\(\[([^\]]+)\]\)/);
            if (match) {
                const days = match[1].split(',').map(d => parseInt(d.trim()));
                btn.addEventListener('click', () => {
//                     console.log(`Specific days button clicked with days:`, days);
                    applyToSpecificDays(days);
                });
//                 console.log(`Added event listener to specific days button for days:`, days);
            }
        }
    });
    
    // 默認選擇第一個模板
    if (templateButtons.length > 0) {
        templateButtons[0].click();
//         console.log('Auto-selected first template');
    }
    
//     console.log('initBatchTimeFeature completed');
}

// 全局變數用於模板選擇
let selectedTemplate = null;
let customSlotCounter = 1;

/**
 * 套用到指定工作日 (修正版 - 保存複選框狀態)
 */
function applyToSpecificDays(days) {
//     console.log('=== applyToSpecificDays DEBUG START ===');
//     console.log('Called with days:', days);
    
    // *** 關鍵修正：立即保存複選框狀態 ***
    const replaceCheckbox = document.getElementById('replaceExisting');
//     console.log('replaceCheckbox element:', replaceCheckbox);
//     console.log('replaceCheckbox exists:', !!replaceCheckbox);
    
    if (replaceCheckbox) {
//         console.log('replaceCheckbox.checked:', replaceCheckbox.checked);
//         console.log('replaceCheckbox.type:', replaceCheckbox.type);
//         console.log('replaceCheckbox.id:', replaceCheckbox.id);
    }
    
    const shouldReplace = replaceCheckbox ? replaceCheckbox.checked : false;
//     console.log('SAVED checkbox state (shouldReplace):', shouldReplace);
    
    const slots = getSelectedTimeSlots();
    if (!slots) {
//         console.log('No slots selected, aborting');
        return;
    }
    
//     console.log('selectedWeekdays before:', Array.from(selectedWeekdays));
    
    // 確保這些天數被選中
    days.forEach(day => {
        const checkbox = document.getElementById(`weekday_${day}`);
        if (checkbox) {
            if (!checkbox.checked) {
                checkbox.checked = true;
                selectedWeekdays.add(day);
//                 console.log(`Added day ${day} to selection`);
            }
            
            // 初始化該日的時段資料
            if (!timeSlotData[day]) {
                timeSlotData[day] = [];
            }
        } else {
//             console.log(`Checkbox for day ${day} not found`);
        }
    });
    
//     console.log('selectedWeekdays after:', Array.from(selectedWeekdays));
    
    // 不要調用 updateTimeSlotsContainer()，因為它會清空現有時段
    // updateTimeSlotsContainer();
    
    // 只確保目標日期的容器存在（如果不存在才創建）
    days.forEach(day => {
        const dayContainer = document.querySelector(`[data-day="${day}"]`);
        if (!dayContainer) {
//             console.log(`Day container not found for ${day}, need to call updateTimeSlotsContainer`);
            updateTimeSlotsContainer();
            return; // 如果需要重建，就重建後跳出
        }
    });
    
    // 短暫延遲確保容器更新完成，然後直接使用已選工作日的邏輯
    setTimeout(() => {
//         console.log('=== setTimeout CALLBACK START ===');
//         console.log('About to call applyTimeSlotsTodays with days:', days);
//         console.log('About to call applyTimeSlotsTodays with slots:', slots);
        applyTimeSlotsTodays(slots, days);
//         console.log('=== applyToSpecificDays DEBUG END ===');
    }, 100);
}

/**
 * 取得選定的時段模板
 */
function getSelectedTimeSlots() {
//     console.log('getSelectedTimeSlots called, selectedTemplate:', selectedTemplate);
    
    if (!selectedTemplate) {
//         console.log('No template selected, showing alert');
        alert('請先選擇時段模板');
        return null;
    }
    
    const templates = {
        'full-day': [
            { start: '09:00', end: '17:00' }
        ],
        'morning-only': [
            { start: '08:30', end: '12:00' }
        ],
        'afternoon-only': [
            { start: '14:00', end: '18:00' }
        ],
        'evening': [
            { start: '18:00', end: '21:00' }
        ],
        'custom': getCustomTimeSlots()
    };
    
    const slots = templates[selectedTemplate];
//     console.log('Selected slots:', slots);
    
    if (!slots || slots.length === 0) {
//         console.log('No valid slots found for template:', selectedTemplate);
        alert('所選模板沒有有效的時段設定');
        return null;
    }
    
    return slots;
}

/**
 * 取得自訂時段
 */
function getCustomTimeSlots() {
    const slots = [];
    document.querySelectorAll('.custom-slot').forEach(slot => {
        const start = slot.querySelector('input[type="time"]:first-of-type').value;
        const end = slot.querySelector('input[type="time"]:last-of-type').value;
        
        if (start && end && start < end) {
            slots.push({ start, end });
        }
    });
    
    return slots.length > 0 ? slots : null;
}

/**
 * 套用時段到指定天數
 */
function applyTimeSlotsTodays(slots, days) {
    const replaceCheckbox = document.getElementById('replaceExisting');
    const replaceExisting = replaceCheckbox ? replaceCheckbox.checked : false;
    
    // 調試信息
//     console.log('applyTimeSlotsTodays called');
//     console.log('replaceCheckbox exists:', !!replaceCheckbox);
//     console.log('replaceExisting value:', replaceExisting);
//     console.log('days:', days);
//     console.log('slots:', slots);
    
    days.forEach(day => {
        const dayContainer = document.querySelector(`[data-day="${day}"]`);
        if (!dayContainer) {
//             console.log(`Day container not found for day ${day}`);
            return;
        }
        
//         console.log(`Processing day ${day}, replaceExisting: ${replaceExisting}`);
        
        // 如果要替換現有時段，先清空所有時段
        if (replaceExisting) {
            // 移除所有現有時段
            const existingSlots = dayContainer.querySelectorAll('.time-slot-item');
//             console.log(`Removing ${existingSlots.length} existing slots for day ${day}`);
            existingSlots.forEach(slot => slot.remove());
            
            // 清空時段資料
            if (timeSlotData[day]) {
                timeSlotData[day] = [];
//                 console.log(`Cleared timeSlotData for day ${day}`);
            }
        } else {
            const existingSlots = dayContainer.querySelectorAll('.time-slot-item');
//             console.log(`Keeping ${existingSlots.length} existing slots for day ${day}`);
        }
        
        // 添加新時段
//         console.log(`Adding ${slots.length} new slots to day ${day}`);
        slots.forEach(slot => {
            addTimeSlotToContainer(day, slot.start, slot.end);
        });
    });
    
    // 確保所有天數的資料都已更新
    days.forEach(day => {
        updateTimeSlotData(day);
    });
    
    // 更新預覽
    setTimeout(() => {
        updatePreview();
    }, 100);
    
    // 顯示成功訊息
    const dayNames = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    const dayNamesStr = days.map(d => dayNames[d]).join('、');
    const action = replaceExisting ? '替換' : '新增';
//     console.log(`Showing toast: 已${action}時段到 ${dayNamesStr}`);
    showToast(`已${action}時段到 ${dayNamesStr}`, 'success');
}

/**
 * 套用到已選工作日
 */
function applyToSelectedDays() {
    const slots = getSelectedTimeSlots();
    if (!slots) return;
    
    const selectedDays = Array.from(selectedWeekdays);
    if (selectedDays.length === 0) {
        alert('請先選擇工作日');
        return;
    }
    
    applyTimeSlotsTodays(slots, selectedDays);
}

/**
 * 新增自訂時段
 */
function addCustomSlot() {
    customSlotCounter++;
    const customSlots = document.querySelector('.custom-slots');
    if (!customSlots) return;
    
    const newSlot = document.createElement('div');
    newSlot.className = 'custom-slot';
    newSlot.innerHTML = `
        <label>時段 ${customSlotCounter}：</label>
        <input type="time" value="09:00">
        <span>到</span>
        <input type="time" value="17:00">
        <button type="button" class="btn-sm btn-outline" onclick="removeCustomSlot(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    customSlots.appendChild(newSlot);
}

/**
 * 移除自訂時段
 */
function removeCustomSlot(button) {
    const slot = button.closest('.custom-slot');
    const customSlots = document.querySelector('.custom-slots');
    
    if (customSlots && customSlots.children.length > 1) {
        slot.remove();
    } else {
        alert('至少需要保留一個時段');
    }
}

/**
 * 顯示提示訊息
 */
function showToast(message, type = 'info') {
    // 簡單的 toast 通知實作
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        z-index: 9999;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * 初始化時段設定
 */
function initializeTimeSlots() {
    // 為已選中的工作日初始化時段設定區域
    updateTimeSlotsContainer();
    
    // 更新預覽
    updatePreview();
}

/**
 * 初始化事件監聽器
 */
function initializeEventListeners() {
    // 工作日選擇事件
    document.querySelectorAll('.weekdays-selection input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleWeekdayChange);
    });
    
    // 表單提交事件
    const form = document.getElementById('scheduleForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // 預約設定變更事件
    document.querySelectorAll('#appointment_duration, #max_appointments_per_slot, #buffer_time').forEach(input => {
        input.addEventListener('change', updatePreview);
    });
    
    // 表單資料變更事件
    document.querySelectorAll('input, select, textarea').forEach(element => {
        element.addEventListener('input', debouncePreviewUpdate);
        element.addEventListener('change', debouncePreviewUpdate);
    });
    
    // 日期驗證
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (startDateInput) {
        startDateInput.addEventListener('change', validateDateRange);
    }
    
    if (endDateInput) {
        endDateInput.addEventListener('change', validateDateRange);
    }
}

/**
 * 載入預設設定
 */
function loadDefaultSettings() {
    // 預設選擇週一至週五
    const defaultWeekdays = [0, 1, 2, 3, 4]; // 週一到週五
    defaultWeekdays.forEach(day => {
        const checkbox = document.getElementById(`weekday_${day}`);
        if (checkbox) {
            checkbox.checked = true;
            selectedWeekdays.add(day);
        }
    });
    
    // 設定預設開始日期為今天
    const today = new Date();
    const startDateInput = document.getElementById('start_date');
    if (startDateInput && !startDateInput.value) {
        startDateInput.value = today.toISOString().split('T')[0];
    }
    
    // 初始化時段資料結構
    selectedWeekdays.forEach(day => {
        timeSlotData[day] = [];
    });
}

/**
 * 處理工作日選擇變更
 */
function handleWeekdayChange(event) {
    const dayValue = parseInt(event.target.value);
    
    if (event.target.checked) {
        selectedWeekdays.add(dayValue);
        // 初始化該日的時段資料
        if (!timeSlotData[dayValue]) {
            timeSlotData[dayValue] = [];
        }
    } else {
        selectedWeekdays.delete(dayValue);
        // 移除該日的時段資料
        delete timeSlotData[dayValue];
    }
    
    // 更新時段設定區域
    updateTimeSlotsContainer();
    
    // 更新預覽
    updatePreview();
}

/**
 * 更新時段設定容器
 */
function updateTimeSlotsContainer() {
    const container = document.getElementById('timeSlotsContainer');
    if (!container) return;
    
    // 清空容器
    container.innerHTML = '';
    
    // 為每個選中的工作日創建時段設定區域
    const sortedDays = Array.from(selectedWeekdays).sort();
    const dayNames = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    
    if (sortedDays.length === 0) {
        container.innerHTML = `
            <div class="no-weekdays-selected">
                <div class="empty-icon">
                    <i class="fas fa-calendar-times"></i>
                </div>
                <p>請先選擇工作日</p>
            </div>
        `;
        return;
    }
    
    sortedDays.forEach(day => {
        const dayElement = createTimeSlotDay(day, dayNames[day]);
        container.appendChild(dayElement);
        
        // 如果該日沒有時段，添加一個預設時段
        if (!timeSlotData[day] || timeSlotData[day].length === 0) {
            addDefaultTimeSlot(day);
        }
    });
}

/**
 * 創建時段設定日期區域
 */
function createTimeSlotDay(dayValue, dayName) {
    const template = document.getElementById('timeSlotTemplate');
    const dayElement = template.content.cloneNode(true);
    
    // 設定日期名稱
    const dayNameElement = dayElement.querySelector('.day-name');
    dayNameElement.textContent = dayName;
    
    // 設定資料屬性
    const timeSlotsContainer = dayElement.querySelector('.time-slots');
    timeSlotsContainer.setAttribute('data-day', dayValue);
    
    // 綁定新增時段按鈕事件
    const addButton = dayElement.querySelector('button');
    addButton.addEventListener('click', () => addTimeSlot(dayValue));
    
    return dayElement;
}

/**
 * 添加預設時段
 */
function addDefaultTimeSlot(day) {
    const defaultStart = '09:00';
    const defaultEnd = '17:00';
    
    if (!timeSlotData[day]) {
        timeSlotData[day] = [];
    }
    
    timeSlotData[day].push({
        start: defaultStart,
        end: defaultEnd
    });
    
    // 更新 UI
    const container = document.querySelector(`[data-day="${day}"]`);
    if (container) {
        addTimeSlotElement(container, defaultStart, defaultEnd);
    }
}

/**
 * 新增時段
 */
function addTimeSlot(day) {
    const container = document.querySelector(`[data-day="${day}"]`);
    if (!container) return;
    
    // 取得最後一個時段的結束時間作為新時段的開始時間
    let startTime = '09:00';
    const existingSlots = container.querySelectorAll('.time-slot-item');
    if (existingSlots.length > 0) {
        const lastSlot = existingSlots[existingSlots.length - 1];
        const lastEndTime = lastSlot.querySelector('.end-time').value;
        if (lastEndTime) {
            // 在最後結束時間基礎上加1小時
            const endTime = new Date(`2000-01-01 ${lastEndTime}`);
            endTime.setHours(endTime.getHours() + 1);
            startTime = endTime.toTimeString().slice(0, 5);
        }
    }
    
    const endTime = addHoursToTime(startTime, 1);
    
    // 添加到資料結構
    if (!timeSlotData[day]) {
        timeSlotData[day] = [];
    }
    timeSlotData[day].push({
        start: startTime,
        end: endTime
    });
    
    // 添加到 UI
    addTimeSlotElement(container, startTime, endTime);
    
    // 更新預覽
    updatePreview();
}

/**
 * 添加時段元素到 UI
 */
function addTimeSlotElement(container, startTime = '', endTime = '') {
    const template = document.getElementById('timeSlotItemTemplate');
    const slotElement = template.content.cloneNode(true);
    
    const startInput = slotElement.querySelector('.start-time');
    const endInput = slotElement.querySelector('.end-time');
    
    // 確保時間輸入欄位可以正常使用
    startInput.value = startTime;
    endInput.value = endTime;
    
    // 綁定事件
    startInput.addEventListener('change', handleTimeSlotChange);
    startInput.addEventListener('input', handleTimeSlotChange);
    endInput.addEventListener('change', handleTimeSlotChange);
    endInput.addEventListener('input', handleTimeSlotChange);
    
    // 綁定刪除按鈕事件
    const deleteButton = slotElement.querySelector('.btn-danger');
    deleteButton.addEventListener('click', function() {
        removeTimeSlot(this);
    });
    
    container.appendChild(slotElement);
    
    // 添加動畫效果
    const addedSlot = container.lastElementChild;
    addedSlot.style.opacity = '0';
    addedSlot.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        addedSlot.style.transition = 'all 0.3s ease';
        addedSlot.style.opacity = '1';
        addedSlot.style.transform = 'translateY(0)';
    }, 50);
}

/**
 * 處理時段時間變更
 */
function handleTimeSlotChange(event) {
    const slotItem = event.target.closest('.time-slot-item');
    const container = slotItem.closest('.time-slots');
    const day = parseInt(container.getAttribute('data-day'));
    
    // 更新資料結構
    updateTimeSlotData(day);
    
    // 驗證時間
    validateTimeSlot(slotItem);
    
    // 更新預覽
    debouncePreviewUpdate();
}


/**
 * 更新時段資料
 */
function updateTimeSlotData(day) {
    const container = document.querySelector(`[data-day="${day}"]`);
    if (!container) {
//         console.log(`updateTimeSlotData: container not found for day ${day}`);
        return;
    }
    
    const slots = [];
    const slotItems = container.querySelectorAll('.time-slot-item');
    
//     console.log(`updateTimeSlotData: found ${slotItems.length} slot items for day ${day}`);
    
    slotItems.forEach(item => {
        const startTime = item.querySelector('.start-time').value;
        const endTime = item.querySelector('.end-time').value;
        
        if (startTime && endTime) {
            slots.push({
                start: startTime,
                end: endTime
            });
//             console.log(`updateTimeSlotData: added slot ${startTime}-${endTime} for day ${day}`);
        }
    });
    
    timeSlotData[day] = slots;
//     console.log(`updateTimeSlotData: timeSlotData[${day}] =`, timeSlotData[day]);
//     console.log(`updateTimeSlotData: full timeSlotData =`, timeSlotData);
}

/**
 * 驗證時段
 */
function validateTimeSlot(slotItem) {
    const startInput = slotItem.querySelector('.start-time');
    const endInput = slotItem.querySelector('.end-time');
    
    const startTime = startInput.value;
    const endTime = endInput.value;
    
    // 清除之前的錯誤狀態
    startInput.classList.remove('error');
    endInput.classList.remove('error');
    
    if (startTime && endTime) {
        if (startTime >= endTime) {
            endInput.classList.add('error');
            showValidationError(endInput, '結束時間必須晚於開始時間');
        } else {
            clearValidationError(endInput);
        }
    }
}

/**
 * 移除時段
 */
function removeTimeSlot(button) {
    const slotItem = button.closest('.time-slot-item');
    const container = slotItem.closest('.time-slots');
    const day = parseInt(container.getAttribute('data-day'));
    
    // 動畫移除
    slotItem.style.transition = 'all 0.3s ease';
    slotItem.style.opacity = '0';
    slotItem.style.transform = 'translateX(-100%)';
    
    setTimeout(() => {
        slotItem.remove();
        // 更新資料
        updateTimeSlotData(day);
        // 更新預覽
        updatePreview();
    }, 300);
}

/**
 * 防抖動更新預覽
 */
function debouncePreviewUpdate() {
    clearTimeout(previewUpdateTimeout);
    previewUpdateTimeout = setTimeout(updatePreview, 300);
}

/**
 * 更新排班預覽
 */
function updatePreview() {
    const previewContainer = document.getElementById('schedulePreview');
    if (!previewContainer) return;
    
    const title = document.getElementById('title').value;
    const appointmentDuration = parseInt(document.getElementById('appointment_duration').value) || 30;
    const maxAppointments = parseInt(document.getElementById('max_appointments_per_slot').value) || 1;
    
    if (selectedWeekdays.size === 0 || Object.keys(timeSlotData).length === 0) {
        previewContainer.innerHTML = `
            <div class="preview-placeholder">
                <i class="fas fa-calendar-day"></i>
                <p>請先選擇工作日和設定時段，這裡將顯示排班預覽</p>
            </div>
        `;
        return;
    }
    
    // 生成預覽日曆
    const previewHTML = generatePreviewCalendar(title, appointmentDuration, maxAppointments);
    previewContainer.innerHTML = previewHTML;
    
    // 檢查衝突
    debounceConflictCheck();
}

/**
 * 生成預覽日曆
 */
function generatePreviewCalendar(title, appointmentDuration, maxAppointments) {
    const dayNames = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    const sortedDays = Array.from(selectedWeekdays).sort();
    
    let totalWeeklyHours = 0;
    let totalWeeklySlots = 0;
    
    const calendarHTML = `
        <div class="preview-header">
            <h3>${title || '新排班'}</h3>
            <div class="preview-stats">
                <span class="stat">
                    <i class="fas fa-calendar-week"></i>
                    ${sortedDays.length} 個工作日
                </span>
            </div>
        </div>
        
        <div class="preview-calendar">
            ${sortedDays.map(day => {
                const slots = timeSlotData[day] || [];
                let dailyHours = 0;
                let dailySlots = 0;
                
                const slotsHTML = slots.map(slot => {
                    const startTime = new Date(`2000-01-01 ${slot.start}`);
                    const endTime = new Date(`2000-01-01 ${slot.end}`);
                    const durationHours = (endTime - startTime) / (1000 * 60 * 60);
                    const slotCount = Math.floor(durationHours * (60 / appointmentDuration)) * maxAppointments;
                    
                    dailyHours += durationHours;
                    dailySlots += slotCount;
                    
                    return `
                        <div class="preview-time-slot">
                            ${slot.start} - ${slot.end}
                            <small>(${slotCount} 預約位)</small>
                        </div>
                    `;
                }).join('');
                
                totalWeeklyHours += dailyHours;
                totalWeeklySlots += dailySlots;
                
                return `
                    <div class="preview-day active">
                        <div class="preview-day-name">${dayNames[day]}</div>
                        <div class="preview-time-slots">
                            ${slotsHTML}
                        </div>
                        <div class="preview-day-stats">
                            <small>${dailyHours.toFixed(1)}h / ${dailySlots}位</small>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
        
        <div class="preview-summary">
            <div class="summary-stat">
                <i class="fas fa-clock"></i>
                <span>每週總工時：${totalWeeklyHours.toFixed(1)} 小時</span>
            </div>
            <div class="summary-stat">
                <i class="fas fa-users"></i>
                <span>每週預約容量：${totalWeeklySlots} 個時段</span>
            </div>
        </div>
    `;
    
    return calendarHTML;
}

/**
 * 防抖動衝突檢查
 */
function debounceConflictCheck() {
    clearTimeout(conflictCheckTimeout);
    conflictCheckTimeout = setTimeout(checkConflicts, 1000);
}

/**
 * 檢查排班衝突
 */
async function checkConflicts() {
    try {
        const formData = getFormData();
        
        const response = await fetch('/api/schedule/check-conflicts/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            const result = await response.json();
            displayConflictWarnings(result.conflicts || []);
        }
    } catch (error) {
        // 衝突檢查失敗，靜默處理
    }
}

/**
 * 顯示衝突警告
 */
function displayConflictWarnings(conflicts) {
    // 移除現有的警告
    document.querySelectorAll('.conflict-warning').forEach(warning => {
        warning.remove();
    });
    
    if (conflicts.length === 0) return;
    
    // 在預覽區域顯示衝突警告
    const previewContainer = document.getElementById('schedulePreview');
    const warningHTML = `
        <div class="conflict-warning">
            <div class="warning-header">
                <i class="fas fa-exclamation-triangle"></i>
                發現 ${conflicts.length} 個潛在衝突
            </div>
            <div class="warning-details">
                ${conflicts.map(conflict => `
                    <div class="conflict-item">
                        <strong>${conflict.type_display}:</strong>
                        ${conflict.message}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    previewContainer.insertAdjacentHTML('afterbegin', warningHTML);
}

/**
 * 處理表單提交
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    
    // 調試：顯示提交前的時段資料
//     console.log('=== FORM SUBMIT DEBUG ===');
//     console.log('Current timeSlotData:', timeSlotData);
//     console.log('Selected weekdays:', Array.from(selectedWeekdays));
    
    // 在提交前手動更新所有時段資料
    selectedWeekdays.forEach(day => {
//         console.log(`Manually updating timeSlotData for day ${day}`);
        updateTimeSlotData(day);
    });
    
//     console.log('Updated timeSlotData:', timeSlotData);
    
    // 驗證表單
    if (!validateForm()) {
        return;
    }
    
    // 準備表單資料
    const formData = getFormData();
    
    // 添加時段資料
    Object.keys(timeSlotData).forEach(day => {
        const slots = timeSlotData[day];
        formData[`time_slots_${day}`] = JSON.stringify(slots);
    });
    
    try {
        // 顯示載入狀態
        setSubmitButtonLoading(true);
        
        // 提交表單
        const formElement = document.getElementById('scheduleForm');
        const formDataToSend = new FormData(formElement);
        
        // 添加時段資料到 FormData
        Object.keys(timeSlotData).forEach(day => {
            const slots = timeSlotData[day];
            formDataToSend.set(`time_slots_${day}`, JSON.stringify(slots));
        });
        
        // 添加 AJAX 標識
        formDataToSend.set('ajax', '1');
        
        // 詳細請求調試
//         console.log('=== REQUEST DEBUG ===');
//         console.log('About to send request...');
//         console.log('Request URL:', window.location.href);
//         console.log('Request method: POST');
//         console.log('CSRF token:', getCsrfToken());
        
//         console.log('Form data contents:');
        for (let [key, value] of formDataToSend.entries()) {
            if (key.startsWith('time_slots_')) {
//                 console.log(`  ${key}: ${value} (parsed:`, JSON.parse(value), ')');
            } else {
//                 console.log(`  ${key}: ${value}`);
            }
        }
        
        const response = await fetch('', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            },
            body: formDataToSend
        });
        
//         console.log('=== RESPONSE DEBUG ===');
//         console.log('Response status:', response.status);
//         console.log('Response status text:', response.statusText);
//         console.log('Response headers:', [...response.headers.entries()]);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Response error body:', errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // 檢查響應是否為JSON
        const contentType = response.headers.get('content-type');
//         console.log('Response content-type:', contentType);
//         console.log('Response status:', response.status);
        if (!contentType || !contentType.includes('application/json')) {
            const responseText = await response.text();
//             console.log('Non-JSON response body:', responseText);
            throw new Error(`服務器返回格式錯誤 (Content-Type: ${contentType})`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            if (result.conflicts && result.conflicts.length > 0) {
                // 有衝突，顯示衝突詳情
                showConflictModal(result.conflicts, result.schedule_id);
            } else {
                // 成功建立
                showToast('排班建立成功', 'success');
                setTimeout(() => {
                    window.location.href = `/vet/schedule/${result.schedule_id}/`;
                }, 1000);
            }
        } else {
            showToast(result.message || '建立失敗', 'error');
        }
        
    } catch (error) {
        console.error('Form submission error:', error);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        showToast(`網路錯誤，請重試: ${error.message}`, 'error');
    } finally {
        setSubmitButtonLoading(false);
    }
}

/**
 * 驗證表單
 */
function validateForm() {
    let isValid = true;
    
    // 驗證標題
    const title = document.getElementById('title').value.trim();
    if (!title) {
        showValidationError(document.getElementById('title'), '請輸入排班名稱');
        isValid = false;
    }
    
    // 驗證開始日期
    const startDate = document.getElementById('start_date').value;
    if (!startDate) {
        showValidationError(document.getElementById('start_date'), '請選擇開始日期');
        isValid = false;
    }
    
    // 驗證工作日
    if (selectedWeekdays.size === 0) {
        showToast('請至少選擇一個工作日', 'error');
        isValid = false;
    }
    
    // 驗證時段設定
    let hasValidSlots = false;
    Object.keys(timeSlotData).forEach(day => {
        const slots = timeSlotData[day];
        if (slots && slots.length > 0) {
            hasValidSlots = true;
        }
    });
    
    if (!hasValidSlots) {
        showToast('請為工作日設定至少一個時段', 'error');
        isValid = false;
    }
    
    return isValid;
}

/**
 * 取得表單資料
 */
function getFormData() {
    const form = document.getElementById('scheduleForm');
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    // 添加工作日資料
    data.weekdays = Array.from(selectedWeekdays);
    data.time_slots = timeSlotData;
    
    return data;
}

/**
 * 日期範圍驗證
 */
function validateDateRange() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    
    if (startDate && endDate) {
        if (new Date(startDate) > new Date(endDate)) {
            showValidationError(document.getElementById('end_date'), '結束日期不能早於開始日期');
        } else {
            clearValidationError(document.getElementById('end_date'));
        }
    }
}

/**
 * 顯示驗證錯誤
 */
function showValidationError(element, message) {
    clearValidationError(element);
    
    element.classList.add('error');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'validation-error';
    errorElement.textContent = message;
    
    element.parentNode.appendChild(errorElement);
}

/**
 * 清除驗證錯誤
 */
function clearValidationError(element) {
    element.classList.remove('error');
    
    const errorElement = element.parentNode.querySelector('.validation-error');
    if (errorElement) {
        errorElement.remove();
    }
}

/**
 * 設定提交按鈕載入狀態
 */
function setSubmitButtonLoading(loading) {
    const submitButton = document.querySelector('button[type="submit"]');
    if (!submitButton) return;
    
    if (loading) {
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <i class="fas fa-spinner fa-spin"></i>
            建立中...
        `;
    } else {
        submitButton.disabled = false;
        submitButton.innerHTML = `
            <i class="fas fa-check"></i>
            建立排班
        `;
    }
}

/**
 * 顯示衝突模態框
 */
function showConflictModal(conflicts, scheduleId) {
    const modal = document.getElementById('conflictModal');
    const conflictDetails = document.getElementById('conflictDetails');
    
    conflictDetails.innerHTML = conflicts.map(conflict => `
        <div class="conflict-item">
            <div class="conflict-type">
                <i class="fas fa-times-circle text-danger"></i>
                ${conflict.type_display || '排班衝突'}
            </div>
            <div class="conflict-message">${conflict.message}</div>
            ${conflict.schedule_title ? `
                <div class="conflict-related">
                    相關排班：${conflict.schedule_title}
                </div>
            ` : ''}
        </div>
    `).join('');
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

/**
 * 工具函數
 */

/**
 * 時間加法
 */
function addHoursToTime(timeString, hours) {
    const time = new Date(`2000-01-01 ${timeString}`);
    time.setHours(time.getHours() + hours);
    return time.toTimeString().slice(0, 5);
}

/**
 * 取得 CSRF Token
 */
function getCsrfToken() {
    // 先嘗試從隱藏的input獲取
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput && csrfInput.value) {
//         console.log('CSRF token found in form:', csrfInput.value);
        return csrfInput.value;
    }
    
    // 備用：從cookie獲取
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    
    if (cookieValue) {
//         console.log('CSRF token found in cookie:', cookieValue);
        return cookieValue;
    }
    
    console.error('CSRF token not found!');
    return '';
}

/**
 * 顯示 Toast 通知
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * 取得 Toast 圖示
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
 * 設定表單驗證樣式
 */
function setupFormValidation() {
    const style = document.createElement('style');
    style.textContent = `
        .form-control.error {
            border-color: var(--medical-danger);
            box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
        }
        
        .validation-error {
            color: var(--medical-danger);
            font-size: 0.75rem;
            margin-top: var(--spacing-xs);
        }
        
        .conflict-warning {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border: 1px solid #f59e0b;
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
            margin-bottom: var(--spacing-md);
        }
        
        .warning-header {
            font-weight: 600;
            color: var(--medical-warning);
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
            margin-bottom: var(--spacing-sm);
        }
        
        .warning-details {
            font-size: 0.875rem;
        }
        
        .conflict-item {
            margin-bottom: var(--spacing-xs);
        }
        
        .preview-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--spacing-md);
            padding-bottom: var(--spacing-sm);
            border-bottom: 1px solid var(--border-light);
        }
        
        .preview-header h3 {
            margin: 0;
            color: var(--text-primary);
        }
        
        .preview-stats {
            display: flex;
            gap: var(--spacing-md);
        }
        
        .stat {
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        
        .preview-day-stats {
            margin-top: var(--spacing-xs);
            padding-top: var(--spacing-xs);
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .preview-summary {
            display: flex;
            justify-content: space-around;
            margin-top: var(--spacing-md);
            padding-top: var(--spacing-md);
            border-top: 1px solid var(--border-light);
        }
        
        .summary-stat {
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
            font-size: 0.875rem;
            color: var(--text-secondary);
            font-weight: 600;
        }
        
        .no-weekdays-selected {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 150px;
            color: var(--text-muted);
            text-align: center;
            gap: var(--spacing-md);
        }
        
        .empty-icon {
            font-size: 3rem;
            opacity: 0.5;
        }
    `;
    
    document.head.appendChild(style);
}