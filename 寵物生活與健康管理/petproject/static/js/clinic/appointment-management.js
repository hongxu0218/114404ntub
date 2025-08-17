// static/js/clinic/appointment-management.js

// ========== 全域變數 ==========
let appointmentsData = [];
let filteredAppointments = [];
let currentView = 'cards';
let currentFilters = {
  date: 'today',
  status: 'all',
  doctor: 'all'
};
let searchQuery = '';
let pageData = {};

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
  initializeAppointmentManagement();
});

// ========== 主要初始化函數 ==========
function initializeAppointmentManagement() {
  console.log('🚀 初始化預約管理系統...');
  
  // 載入頁面數據
  loadPageData();
  
  // 初始化各種功能
  initializeFilters();
  initializeSearch();
  initializeViewToggle();
  initializeModals();
  initializeKeyboardShortcuts();
  initializeAutoRefresh();
  
  // 載入並渲染預約資料
  loadAppointmentsData();
  renderAppointments();
  updateStatistics();
  
  console.log('✅ 預約管理系統初始化完成');
}

// ========== 載入頁面數據 ==========
function loadPageData() {
  if (window.appointmentPageData) {
    pageData = window.appointmentPageData;
    appointmentsData = pageData.appointments || [];
    currentFilters = pageData.currentFilters || currentFilters;
    filteredAppointments = [...appointmentsData];
    console.log('📊 載入頁面數據:', pageData);
  }
}

// ========== 篩選功能 ==========
function initializeFilters() {
  // 篩選按鈕事件
  const filterChips = document.querySelectorAll('.filter-chip');
  
  filterChips.forEach(chip => {
    chip.addEventListener('click', function() {
      const filterType = this.dataset.filter;
      const filterValue = this.dataset.value;
      
      // 更新同類型篩選器的活動狀態
      document.querySelectorAll(`[data-filter="${filterType}"]`).forEach(c => {
        c.classList.remove('active');
      });
      this.classList.add('active');
      
      // 更新篩選條件
      currentFilters[filterType] = filterValue;
      
      // 應用篩選
      applyFilters();
      
      // 視覺回饋
      animateFilterChange(this);
      
      console.log(`🔍 篩選更新: ${filterType} = ${filterValue}`);
    });
  });
  
  // 醫師篩選下拉選單
  initializeDoctorFilter();
}

function initializeDoctorFilter() {
  const doctorFilterItems = document.querySelectorAll('.doctor-filter-item');
  const selectedDoctorText = document.getElementById('selectedDoctorText');
  
  doctorFilterItems.forEach(item => {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      
      const doctorId = this.dataset.doctor;
      const doctorName = this.textContent.trim();
      
      // 更新篩選條件
      currentFilters.doctor = doctorId;
      
      // 更新顯示文字
      selectedDoctorText.textContent = doctorName;
      
      // 關閉下拉選單
      const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('doctorFilterDropdown'));
      if (dropdown) dropdown.hide();
      
      // 應用篩選
      applyFilters();
      
      console.log(`👨‍⚕️ 醫師篩選: ${doctorName} (${doctorId})`);
    });
  });
}

function applyFilters() {
  filteredAppointments = appointmentsData.filter(appointment => {
    // 日期篩選
    if (!passesDateFilter(appointment)) return false;
    
    // 狀態篩選
    if (!passesStatusFilter(appointment)) return false;
    
    // 醫師篩選
    if (!passesDoctorFilter(appointment)) return false;
    
    // 搜尋篩選
    if (!passesSearchFilter(appointment)) return false;
    
    return true;
  });
  
  renderAppointments();
  updateStatistics();
  updateFilterCounts();
  
  console.log(`📊 篩選結果: ${filteredAppointments.length}/${appointmentsData.length}`);
}

function passesDateFilter(appointment) {
  const { date: filterDate } = currentFilters;
  const appointmentDate = new Date(appointment.date);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  
  switch (filterDate) {
    case 'today':
      return appointmentDate.toDateString() === today.toDateString();
    case 'tomorrow':
      return appointmentDate.toDateString() === tomorrow.toDateString();
    case 'week':
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() - today.getDay());
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      return appointmentDate >= weekStart && appointmentDate <= weekEnd;
    case 'all':
      return true;
    default:
      return true;
  }
}

function passesStatusFilter(appointment) {
  const { status: filterStatus } = currentFilters;
  return filterStatus === 'all' || appointment.status === filterStatus;
}

function passesDoctorFilter(appointment) {
  const { doctor: filterDoctor } = currentFilters;
  return filterDoctor === 'all' || appointment.doctorId.toString() === filterDoctor;
}

function passesSearchFilter(appointment) {
  if (!searchQuery) return true;
  
  const searchTerms = [
    appointment.petName,
    appointment.ownerName,
    appointment.doctorName,
    appointment.reason,
    appointment.notes
  ].join(' ').toLowerCase();
  
  return searchTerms.includes(searchQuery.toLowerCase());
}

// ========== 搜尋功能 ==========
function initializeSearch() {
  const searchInput = document.getElementById('quickSearch');
  const searchBtn = document.querySelector('.search-btn');
  
  if (searchInput) {
    // 即時搜尋
    searchInput.addEventListener('input', function() {
      searchQuery = this.value.trim();
      applyFilters();
    });
    
    // 清空搜尋
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        this.value = '';
        searchQuery = '';
        applyFilters();
      }
    });
  }
  
  if (searchBtn) {
    searchBtn.addEventListener('click', function() {
      searchInput.focus();
    });
  }
}

// ========== 檢視切換 ==========
function initializeViewToggle() {
  const viewButtons = document.querySelectorAll('.view-btn');
  
  viewButtons.forEach(button => {
    button.addEventListener('click', function() {
      const view = this.dataset.view;
      switchView(view);
      
      // 更新按鈕狀態
      viewButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');
    });
  });
}

function switchView(view) {
  currentView = view;
  
  // 隱藏所有檢視
  document.querySelectorAll('.appointments-view').forEach(v => {
    v.classList.remove('active');
  });
  
  // 顯示目標檢視
  const targetView = document.getElementById(view + 'View');
  if (targetView) {
    targetView.classList.add('active');
  }
  
  console.log(`🔄 切換到 ${view} 檢視`);
}

// ========== 渲染預約列表 ==========
function renderAppointments() {
  if (currentView === 'cards') {
    renderCardsView();
  } else {
    renderListView();
  }
}

function renderCardsView() {
  const container = document.getElementById('appointmentsGrid');
  if (!container) return;
  
  // 顯示/隱藏現有卡片
  const cards = container.querySelectorAll('.appointment-card-modern');
  
  cards.forEach(card => {
    const appointmentId = parseInt(card.dataset.appointmentId);
    const shouldShow = filteredAppointments.some(apt => apt.id === appointmentId);
    
    if (shouldShow) {
      showAppointmentCard(card);
    } else {
      hideAppointmentCard(card);
    }
  });
  
  console.log('🎨 渲染卡片檢視完成');
}

function renderListView() {
  const tbody = document.getElementById('appointmentsTableBody');
  if (!tbody) return;
  
  // 顯示/隱藏表格行
  const rows = tbody.querySelectorAll('.appointment-row');
  
  rows.forEach(row => {
    const appointmentId = parseInt(row.dataset.appointmentId);
    const shouldShow = filteredAppointments.some(apt => apt.id === appointmentId);
    
    if (shouldShow) {
      row.style.display = 'table-row';
    } else {
      row.style.display = 'none';
    }
  });
  
  console.log('📋 渲染列表檢視完成');
}

function showAppointmentCard(card) {
  card.style.display = 'block';
  card.style.animation = 'fadeInUp 0.3s ease-out';
}

function hideAppointmentCard(card) {
  card.style.animation = 'fadeOut 0.3s ease-out';
  setTimeout(() => {
    card.style.display = 'none';
  }, 300);
}

// ========== 統計資料更新 ==========
function updateStatistics() {
  // 計算各種統計
  const stats = {
    total: appointmentsData.length,
    confirmed: appointmentsData.filter(apt => apt.status === 'confirmed').length,
    pending: appointmentsData.filter(apt => apt.status === 'pending').length,
    today: appointmentsData.filter(apt => {
      const today = new Date().toDateString();
      return new Date(apt.date).toDateString() === today;
    }).length
  };
  
  // 更新統計顯示
  updateStatElement('confirmedCount', stats.confirmed);
  updateStatElement('pendingCount', stats.pending);
  updateStatElement('todayCount', stats.today);
  
  console.log('📊 統計資料已更新:', stats);
}

function updateStatElement(elementId, value) {
  const element = document.getElementById(elementId);
  if (element) {
    // 動畫效果
    element.style.transform = 'scale(1.1)';
    element.textContent = value;
    
    setTimeout(() => {
      element.style.transform = 'scale(1)';
    }, 150);
  }
}

function updateFilterCounts() {
  // 可以在這裡更新篩選器旁邊顯示的數量
  console.log(`📈 當前顯示: ${filteredAppointments.length} 個預約`);
}

// ========== 預約操作功能 ==========
function viewAppointmentDetail(appointmentId) {
  console.log(`👁️ 查看預約詳情: ${appointmentId}`);
  
  // 從後端載入詳細資料
  loadAppointmentDetail(appointmentId);
}

function loadAppointmentDetail(appointmentId) {
  const url = pageData.urls.appointmentDetail.replace('{id}', appointmentId);
  
  fetch(url, {
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(response => response.text())
  .then(html => {
    document.getElementById('appointmentDetailContent').innerHTML = html;
    showModal(document.getElementById('appointmentDetailModal'));
  })
  .catch(error => {
    console.error('載入預約詳情失敗:', error);
    showErrorMessage('載入預約詳情失敗，請稍後再試');
  });
}

function confirmAppointment(appointmentId) {
  console.log(`✅ 確認預約: ${appointmentId}`);
  
  showConfirmDialog({
    title: '確認預約',
    message: '確定要確認此預約嗎？',
    confirmText: '確認',
    onConfirm: () => {
      executeConfirmAppointment(appointmentId);
    }
  });
}

function executeConfirmAppointment(appointmentId) {
  const url = pageData.urls.confirmAppointment.replace('{id}', appointmentId);
  
  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': pageData.csrfToken,
      'Content-Type': 'application/json',
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showSuccessMessage('預約已確認');
      
      // 更新本地資料
      updateAppointmentStatus(appointmentId, 'confirmed');
      
      // 重新渲染
      renderAppointments();
      updateStatistics();
    } else {
      showErrorMessage(data.message || '確認失敗');
    }
  })
  .catch(error => {
    console.error('確認預約失敗:', error);
    showErrorMessage('網路錯誤，請稍後再試');
  });
}

function showCancelModal(appointmentId) {
  const appointment = appointmentsData.find(apt => apt.id === appointmentId);
  if (!appointment) return;
  
  // 填入預約資訊
  document.getElementById('cancelAppointmentId').value = appointmentId;
  
  // 生成預約摘要
  const summary = `
    <div class="appointment-summary">
      <h6>${appointment.petName}</h6>
      <p>飼主：${appointment.ownerName}</p>
      <p>時間：${appointment.date} ${appointment.startTime}-${appointment.endTime}</p>
      <p>醫師：${appointment.doctorName}</p>
    </div>
  `;
  
  document.getElementById('cancelAppointmentSummary').innerHTML = summary;
  
  // 清空取消原因
  document.getElementById('cancelReason').value = '';
  
  // 顯示 Modal
  showModal(document.getElementById('cancelAppointmentModal'));
  
  console.log(`❌ 開啟取消預約 Modal: ${appointmentId}`);
}

function markCompleted(appointmentId) {
  console.log(`✔️ 標記完成: ${appointmentId}`);
  
  showConfirmDialog({
    title: '標記完成',
    message: '確定要將此預約標記為已完成嗎？',
    confirmText: '標記完成',
    onConfirm: () => {
      executeMarkCompleted(appointmentId);
    }
  });
}

function executeMarkCompleted(appointmentId) {
  const url = pageData.urls.completeAppointment.replace('{id}', appointmentId);
  
  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': pageData.csrfToken,
      'Content-Type': 'application/json',
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showSuccessMessage('預約已標記為完成');
      
      // 更新本地資料
      updateAppointmentStatus(appointmentId, 'completed');
      
      // 重新渲染
      renderAppointments();
      updateStatistics();
    } else {
      showErrorMessage(data.message || '操作失敗');
    }
  })
  .catch(error => {
    console.error('標記完成失敗:', error);
    showErrorMessage('網路錯誤，請稍後再試');
  });
}

function updateAppointmentStatus(appointmentId, newStatus) {
  const appointment = appointmentsData.find(apt => apt.id === appointmentId);
  if (appointment) {
    appointment.status = newStatus;
    
    // 更新卡片和表格中的狀態顯示
    updateAppointmentDisplayStatus(appointmentId, newStatus);
  }
}

function updateAppointmentDisplayStatus(appointmentId, newStatus) {
  // 更新卡片中的狀態
  const card = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
  if (card) {
    card.dataset.status = newStatus;
    
    const statusBadge = card.querySelector('.status-badge-modern');
    if (statusBadge) {
      updateStatusBadge(statusBadge, newStatus);
    }
    
    // 更新操作按鈕
    updateCardActions(card, newStatus);
  }
}

function updateStatusBadge(badge, status) {
  // 移除舊的狀態類別
  badge.className = 'status-badge-modern';
  
  // 添加新的狀態類別和內容
  badge.classList.add(`status-${status}`);
  
  const statusTexts = {
    'confirmed': '<i class="bi bi-check-circle"></i>已確認',
    'pending': '<i class="bi bi-clock"></i>待確認',
    'cancelled': '<i class="bi bi-x-circle"></i>已取消',
    'completed': '<i class="bi bi-check2-circle"></i>已完成'
  };
  
  badge.innerHTML = statusTexts[status] || status;
}

function updateCardActions(card, status) {
  const actionsContainer = card.querySelector('.card-actions');
  if (!actionsContainer) return;
  
  // 重新生成操作按鈕
  let buttonsHTML = `
    <button class="action-btn btn-info" onclick="viewAppointmentDetail(${card.dataset.appointmentId})">
      <i class="bi bi-eye"></i>
      <span>查看詳情</span>
    </button>
  `;
  
  if (status === 'pending') {
    buttonsHTML += `
      <button class="action-btn btn-success" onclick="confirmAppointment(${card.dataset.appointmentId})">
        <i class="bi bi-check"></i>
        <span>確認預約</span>
      </button>
    `;
  }
  
  if (status === 'pending' || status === 'confirmed') {
    buttonsHTML += `
      <button class="action-btn btn-warning" onclick="showCancelModal(${card.dataset.appointmentId})">
        <i class="bi bi-x"></i>
        <span>取消預約</span>
      </button>
    `;
  }
  
  if (status === 'confirmed') {
    buttonsHTML += `
      <button class="action-btn btn-secondary" onclick="markCompleted(${card.dataset.appointmentId})">
        <i class="bi bi-check2"></i>
        <span>標記完成</span>
      </button>
    `;
  }
  
  actionsContainer.innerHTML = buttonsHTML;
}

// ========== Modal 管理 ==========
function initializeModals() {
  // Modal 外部點擊關閉
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', function(e) {
      if (e.target === this) {
        closeModal(this);
      }
    });
  });
  
  // 取消預約表單提交
  const cancelForm = document.getElementById('cancelAppointmentForm');
  if (cancelForm) {
    cancelForm.addEventListener('submit', function(e) {
      e.preventDefault();
      executeCancelAppointment();
    });
  }
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

function closeAppointmentDetailModal() {
  closeModal(document.getElementById('appointmentDetailModal'));
}

function closeCancelModal() {
  closeModal(document.getElementById('cancelAppointmentModal'));
}

function executeCancelAppointment() {
  const appointmentId = document.getElementById('cancelAppointmentId').value;
  const cancelReason = document.getElementById('cancelReason').value.trim();
  
  if (!cancelReason) {
    showErrorMessage('請填寫取消原因');
    return;
  }
  
  const url = pageData.urls.cancelAppointment.replace('{id}', appointmentId);
  
  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': pageData.csrfToken,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      'cancel_reason': cancelReason
    })
  })
  .then(response => {
    if (response.ok) {
      showSuccessMessage('預約已取消，已通知飼主');
      closeCancelModal();
      
      // 移除預約卡片
      removeAppointmentFromDisplay(appointmentId);
      
      // 從本地資料中移除
      appointmentsData = appointmentsData.filter(apt => apt.id !== parseInt(appointmentId));
      
      // 重新渲染
      applyFilters();
      updateStatistics();
    } else {
      throw new Error('取消失敗');
    }
  })
  .catch(error => {
    console.error('取消預約失敗:', error);
    showErrorMessage('取消失敗，請稍後再試');
  });
}

function removeAppointmentFromDisplay(appointmentId) {
  const card = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
  if (card) {
    card.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => {
      card.remove();
    }, 300);
  }
  
  const row = document.querySelector(`tr[data-appointment-id="${appointmentId}"]`);
  if (row) {
    row.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => {
      row.remove();
    }, 300);
  }
}

// ========== 重新整理功能 ==========
function refreshAppointments() {
  console.log('🔄 重新整理預約列表...');
  
  showSuccessMessage('正在重新整理...');
  
  // 重新載入頁面
  setTimeout(() => {
    window.location.reload();
  }, 1000);
}

// ========== 自動重新整理 ==========
function initializeAutoRefresh() {
  // 每5分鐘自動檢查更新
  setInterval(() => {
    if (document.visibilityState === 'visible') {
      checkForUpdates();
    }
  }, 300000); // 5分鐘
}

function checkForUpdates() {
  // 這裡可以實作檢查是否有新預約的邏輯
  console.log('🔍 檢查更新...');
}

// ========== 鍵盤快捷鍵 ==========
function initializeKeyboardShortcuts() {
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + R: 重新整理
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
      e.preventDefault();
      refreshAppointments();
    }
    
    // Ctrl/Cmd + F: 聚焦搜尋框
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault();
      const searchInput = document.getElementById('quickSearch');
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }
    
    // Ctrl/Cmd + 1/2: 切換檢視
    if ((e.ctrlKey || e.metaKey) && e.key === '1') {
      e.preventDefault();
      document.querySelector('[data-view="cards"]').click();
    }
    
    if ((e.ctrlKey || e.metaKey) && e.key === '2') {
      e.preventDefault();
      document.querySelector('[data-view="list"]').click();
    }
    
    // ESC: 關閉 Modal
    if (e.key === 'Escape') {
      closeAllModals();
    }
  });
}

function closeAllModals() {
  document.querySelectorAll('.modal-overlay.show').forEach(modal => {
    closeModal(modal);
  });
}

// ========== 工具函數 ==========
function loadAppointmentsData() {
  // 資料已在頁面載入時注入，這裡處理資料初始化
  filteredAppointments = [...appointmentsData];
  console.log('📊 載入預約資料:', appointmentsData);
}

function animateFilterChange(chip) {
  chip.style.transform = 'scale(1.1)';
  setTimeout(() => {
    chip.style.transform = 'scale(1)';
  }, 150);
}

// ========== 訊息顯示（繼承自其他模組） ==========
function showConfirmDialog(options) {
  const dialog = document.createElement('div');
  dialog.className = 'confirm-dialog-overlay';
  dialog.innerHTML = `
    <div class="confirm-dialog">
      <h3>${options.title}</h3>
      <p>${options.message}</p>
      <div class="dialog-buttons">
        <button class="btn-cancel">取消</button>
        <button class="btn-confirm">${options.confirmText}</button>
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

// ========== CSS 動畫注入 ==========
const appointmentAnimationCSS = `
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

.btn-cancel {
  background: var(--gray-100); color: var(--gray-700);
  border: 1px solid var(--gray-300); padding: 0.5rem 1rem;
  border-radius: 0.5rem; cursor: pointer;
}

.btn-confirm {
  background: var(--primary-color); color: white;
  border: none; padding: 0.5rem 1rem;
  border-radius: 0.5rem; cursor: pointer;
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
.message-close { 
  background: none; border: none; font-size: 1.25rem; 
  cursor: pointer; opacity: 0.5; margin-left: auto;
}
.message-close:hover { opacity: 1; }
`;

// 注入 CSS
if (!document.getElementById('appointment-animations')) {
  const style = document.createElement('style');
  style.id = 'appointment-animations';
  style.textContent = appointmentAnimationCSS;
  document.head.appendChild(style);
}

console.log('✅ 預約管理 JavaScript 載入完成');