// static/js/clinic/business-hours.js

// ========== 營業時間管理系統 ==========

// 全域變數
let businessHoursData = {};
let periodCounter = 0;

// 星期名稱對應
const dayNames = [
  '週一', '週二', '週三', '週四', '週五', '週六', '週日'
];

// ========== 初始化功能 ==========
function initializeBusinessHours() {
  console.log('🕐 初始化營業時間管理系統...');
  
  // 初始化資料結構
  initializeBusinessHoursData();
  
  // 綁定事件監聽器
  bindEventListeners();
  
  // 載入現有資料
  loadBusinessHours();
  
  console.log('✅ 營業時間管理系統初始化完成');
}

function initializeBusinessHoursData() {
  // 初始化每一天的資料結構
  for (let day = 0; day < 7; day++) {
    businessHoursData[day] = [];
  }
}

function bindEventListeners() {
  // 綁定營業狀態切換
  document.querySelectorAll('.day-enabled').forEach((checkbox, index) => {
    checkbox.addEventListener('change', function() {
      toggleDayStatus(index, this.checked);
    });
  });
  
  // 初始渲染所有天數
  for (let day = 0; day < 7; day++) {
    renderDayPeriods(day);
  }
}

// ========== 載入和儲存資料 ==========
function loadBusinessHours() {
  console.log('📖 載入營業時間資料...');
  
  // 🔧 TODO: 實際API調用
  /*
  fetch(`/api/clinic/business-hours/`, {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': dashboardData.csrfToken
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      businessHoursData = data.business_hours;
      renderAllDays();
      updatePreview();
    } else {
      showBusinessHoursError(data.message || '載入失敗');
    }
  })
  .catch(error => {
    console.error('載入營業時間錯誤:', error);
    showBusinessHoursError('載入失敗，請稍後重試');
  });
  */
  
  // 暫時載入預設資料
  businessHoursData = {
    0: [
      { id: 1, name: '上午診', openTime: '09:00', closeTime: '12:00' },
      { id: 2, name: '下午診', openTime: '14:00', closeTime: '17:00' }
    ],
    1: [
      { id: 3, name: '上午診', openTime: '09:00', closeTime: '12:00' },
      { id: 4, name: '下午診', openTime: '14:00', closeTime: '17:00' }
    ],
    2: [
      { id: 5, name: '上午診', openTime: '09:00', closeTime: '12:00' },
      { id: 6, name: '下午診', openTime: '14:00', closeTime: '17:00' }
    ],
    3: [
      { id: 7, name: '上午診', openTime: '09:00', closeTime: '12:00' },
      { id: 8, name: '下午診', openTime: '14:00', closeTime: '17:00' }
    ],
    4: [
      { id: 9, name: '上午診', openTime: '09:00', closeTime: '12:00' },
      { id: 10, name: '下午診', openTime: '14:00', closeTime: '17:00' }
    ],
    5: [
      { id: 11, name: '上午診', openTime: '09:00', closeTime: '12:00' }
    ],
    6: [] // 週日休息
  };
  
  renderAllDays();
  updatePreview();
}

function saveBusinessHours() {
  console.log('💾 儲存營業時間設定...');
  
  // 驗證資料
  const validationResult = validateBusinessHours();
  if (!validationResult.valid) {
    showBusinessHoursError(validationResult.message);
    return false;
  }
  
  showSaveLoading(true);
  
  const saveData = {
    business_hours: businessHoursData
  };
  
  // 🔧 TODO: 實際API調用
  /*
  fetch('/api/clinic/business-hours/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': dashboardData.csrfToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(saveData)
  })
  .then(response => response.json())
  .then(result => {
    if (result.success) {
      showSuccessMessage('營業時間設定已更新');
      updateBusinessStatusDisplay();
    } else {
      showErrorMessage(result.message || '儲存失敗');
    }
  })
  .catch(error => {
    console.error('儲存營業時間錯誤:', error);
    showErrorMessage('儲存失敗，請稍後重試');
  })
  .finally(() => {
    showSaveLoading(false);
  });
  */
  
  // 暫時模擬成功
  setTimeout(() => {
    showSuccessMessage('營業時間設定已更新（模擬）');
    showSaveLoading(false);
    updateBusinessStatusDisplay();
  }, 1500);
  
  return true;
}

// ========== 天數狀態管理 ==========
function toggleDayStatus(day, enabled) {
  const dayCard = document.querySelector(`.day-card[data-day="${day}"]`);
  const statusText = dayCard.querySelector('.status-text');
  
  if (enabled) {
    dayCard.classList.remove('disabled');
    statusText.textContent = '營業';
    
    // 如果該天沒有時段，新增一個預設時段
    if (!businessHoursData[day] || businessHoursData[day].length === 0) {
      addPeriod(day, { name: '營業時間', openTime: '09:00', closeTime: '17:00' });
    }
  } else {
    dayCard.classList.add('disabled');
    statusText.textContent = '休息';
    businessHoursData[day] = [];
  }
  
  renderDayPeriods(day);
  updatePreview();
}

// ========== 時段管理 ==========
function addPeriod(day, periodData = null) {
  console.log(`➕ 新增時段 (${dayNames[day]})`);
  
  const defaultPeriod = periodData || {
    id: ++periodCounter,
    name: '營業時間',
    openTime: '09:00',
    closeTime: '17:00'
  };
  
  if (!defaultPeriod.id) {
    defaultPeriod.id = ++periodCounter;
  }
  
  if (!businessHoursData[day]) {
    businessHoursData[day] = [];
  }
  
  businessHoursData[day].push(defaultPeriod);
  renderDayPeriods(day);
  updatePreview();
}

function deletePeriod(day, periodId) {
  console.log(`🗑️ 刪除時段 (${dayNames[day]}, ID: ${periodId})`);
  
  if (businessHoursData[day]) {
    businessHoursData[day] = businessHoursData[day].filter(period => period.id !== periodId);
    renderDayPeriods(day);
    updatePreview();
  }
}

function updatePeriod(day, periodId, field, value) {
  console.log(`🔄 更新時段 (${dayNames[day]}, ID: ${periodId}, ${field}: ${value})`);
  
  if (businessHoursData[day]) {
    const period = businessHoursData[day].find(p => p.id === periodId);
    if (period) {
      period[field] = value;
      
      // 驗證時間邏輯
      if (field === 'openTime' || field === 'closeTime') {
        if (period.openTime >= period.closeTime) {
          showBusinessHoursError('結束時間必須晚於開始時間');
          return;
        }
      }
      
      updatePreview();
    }
  }
}

// ========== 渲染功能 ==========
function renderAllDays() {
  for (let day = 0; day < 7; day++) {
    renderDayPeriods(day);
    
    // 更新營業狀態切換
    const checkbox = document.querySelector(`.day-card[data-day="${day}"] .day-enabled`);
    const hasBusinessHours = businessHoursData[day] && businessHoursData[day].length > 0;
    
    if (checkbox) {
      checkbox.checked = hasBusinessHours;
      toggleDayStatus(day, hasBusinessHours);
    }
  }
}

function renderDayPeriods(day) {
  const periodsContainer = document.querySelector(`.periods-container[data-day="${day}"]`);
  if (!periodsContainer) return;
  
  const periods = businessHoursData[day] || [];
  
  periodsContainer.innerHTML = periods.map(period => `
    <div class="period-item" data-period-id="${period.id}">
      <div class="period-header">
        <input 
          type="text" 
          class="period-name-input" 
          value="${period.name}" 
          onchange="updatePeriod(${day}, ${period.id}, 'name', this.value)"
          placeholder="時段名稱"
        >
        <div class="period-actions">
          <button 
            type="button" 
            class="delete-period-btn" 
            onclick="deletePeriod(${day}, ${period.id})"
            title="刪除時段"
          >
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
      
      <div class="period-form">
        <div class="time-input-group">
          <label>開始時間</label>
          <input 
            type="time" 
            value="${period.openTime}" 
            onchange="updatePeriod(${day}, ${period.id}, 'openTime', this.value)"
          >
        </div>
        
        <div class="time-input-group">
          <label>結束時間</label>
          <input 
            type="time" 
            value="${period.closeTime}" 
            onchange="updatePeriod(${day}, ${period.id}, 'closeTime', this.value)"
          >
        </div>
        
        <div class="time-display">
          <small class="text-muted">
            ${calculateDuration(period.openTime, period.closeTime)}
          </small>
        </div>
      </div>
    </div>
  `).join('');
}

function updatePreview() {
  const previewContainer = document.getElementById('businessHoursPreview');
  if (!previewContainer) return;
  
  const previewHTML = dayNames.map((dayName, index) => {
    const periods = businessHoursData[index] || [];
    
    let hoursText = '';
    let statusClass = '';
    
    if (periods.length === 0) {
      hoursText = '休息';
      statusClass = 'closed';
    } else {
      hoursText = periods.map(period => 
        `${period.name}: ${period.openTime}-${period.closeTime}`
      ).join(', ');
      statusClass = 'open';
    }
    
    return `
      <div class="preview-day">
        <span class="preview-day-name">${dayName}</span>
        <span class="preview-hours ${statusClass}">${hoursText}</span>
      </div>
    `;
  }).join('');
  
  previewContainer.innerHTML = previewHTML;
}

// ========== 工具函數 ==========
function calculateDuration(startTime, endTime) {
  if (!startTime || !endTime) return '';
  
  const start = new Date(`2000-01-01T${startTime}`);
  const end = new Date(`2000-01-01T${endTime}`);
  
  if (end <= start) return '無效時間';
  
  const diffMs = end - start;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  
  if (diffHours === 0) {
    return `${diffMinutes}分鐘`;
  } else if (diffMinutes === 0) {
    return `${diffHours}小時`;
  } else {
    return `${diffHours}小時${diffMinutes}分鐘`;
  }
}

function validateBusinessHours() {
  // 檢查是否至少有一天營業
  const hasAnyBusinessDay = Object.values(businessHoursData).some(day => day && day.length > 0);
  
  if (!hasAnyBusinessDay) {
    return {
      valid: false,
      message: '請至少設定一天的營業時間'
    };
  }
  
  // 檢查時間邏輯
  for (let day = 0; day < 7; day++) {
    const periods = businessHoursData[day] || [];
    
    for (let i = 0; i < periods.length; i++) {
      const period = periods[i];
      
      // 檢查開始時間和結束時間
      if (period.openTime >= period.closeTime) {
        return {
          valid: false,
          message: `${dayNames[day]} 的「${period.name}」結束時間必須晚於開始時間`
        };
      }
      
      // 檢查時段重疊
      for (let j = i + 1; j < periods.length; j++) {
        const otherPeriod = periods[j];
        
        if (isTimeOverlap(period, otherPeriod)) {
          return {
            valid: false,
            message: `${dayNames[day]} 的時段「${period.name}」與「${otherPeriod.name}」時間重疊`
          };
        }
      }
    }
  }
  
  return { valid: true };
}

function isTimeOverlap(period1, period2) {
  return (period1.openTime < period2.closeTime && period1.closeTime > period2.openTime);
}

function updateBusinessStatusDisplay() {
  // 更新主 dashboard 的營業狀態顯示
  if (typeof updateBusinessStatusLocal === 'function') {
    updateBusinessStatusLocal();
  }
}

function showBusinessHoursError(message) {
  // 使用現有的訊息系統顯示錯誤
  if (typeof showErrorMessage === 'function') {
    showErrorMessage(message);
  } else {
    alert(message);
  }
}

// ========== 導出功能到全域 ==========
window.initializeBusinessHours = initializeBusinessHours;
window.addPeriod = addPeriod;
window.deletePeriod = deletePeriod;
window.updatePeriod = updatePeriod;
window.saveBusinessHours = saveBusinessHours;

console.log('✅ 營業時間管理 JavaScript 載入完成');