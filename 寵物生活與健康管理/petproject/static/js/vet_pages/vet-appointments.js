// static/js/vet_pages/vet-appointments.js
// 獸醫師預約管理系統 - 專業版

// ========== 全域變數 ==========
let appointmentsData = {};
let filteredAppointments = [];
let currentFilter = 'all';
let searchQuery = '';
let isInitialized = false;

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    if (!isInitialized) {
        initializeVetAppointments();
        isInitialized = true;
    }
});

// ========== 主要初始化函數 ==========
function initializeVetAppointments() {
    console.log('初始化獸醫師預約管理系統...');
    
    try {
        loadAppointmentsData();
        initializeSearchFunctionality();
        initializeFilterFunctionality();
        initializeTableInteractions();
        initializeFormHandling();
        initializeKeyboardShortcuts();
        updateAppointmentCounts();
        
        console.log('獸醫師預約管理系統初始化完成');
    } catch (error) {
        console.error('初始化失敗:', error);
        showErrorMessage('系統初始化失敗，請重新整理頁面');
    }
}

// ========== 載入頁面數據 ==========
function loadAppointmentsData() {
    if (window.vetAppointmentsData) {
        appointmentsData = window.vetAppointmentsData;
        console.log('載入預約數據:', appointmentsData);
    }
}

// ========== 搜尋功能 ==========
function initializeSearchFunctionality() {
    try {
        const searchInput = document.getElementById('searchInput');
        
        if (searchInput) {
            // 即時搜尋
            searchInput.addEventListener('input', debounce(function(e) {
                searchQuery = e.target.value.trim();
                performSearch();
            }, 300));
            
            // Enter 鍵搜尋
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    searchAppointments();
                }
            });
        }
        
        console.log('搜尋功能初始化完成');
    } catch (error) {
        console.error('搜尋功能初始化失敗:', error);
    }
}

function searchAppointments() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchQuery = searchInput.value.trim();
        performSearch();
    }
}

function performSearch() {
    const rows = document.querySelectorAll('.appointment-row');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const petName = row.querySelector('.pet-name-link')?.textContent?.toLowerCase() || '';
        const ownerName = row.cells[3]?.textContent?.toLowerCase() || '';
        const reason = row.cells[4]?.textContent?.toLowerCase() || '';
        
        const matchesSearch = !searchQuery || 
            petName.includes(searchQuery.toLowerCase()) ||
            ownerName.includes(searchQuery.toLowerCase()) ||
            reason.includes(searchQuery.toLowerCase());
        
        if (matchesSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // 處理日期分組行的顯示
    updateDateGroupVisibility();
    
    // 顯示搜尋結果
    if (searchQuery && visibleCount === 0) {
        showNoResultsMessage();
    }
    
    console.log(`搜尋 "${searchQuery}" 找到 ${visibleCount} 筆結果`);
}

function updateDateGroupVisibility() {
    const dateGroups = document.querySelectorAll('.date-group-row');
    
    dateGroups.forEach(dateGroup => {
        const nextRows = [];
        let nextSibling = dateGroup.nextElementSibling;
        
        // 收集同一日期組下的所有預約行
        while (nextSibling && !nextSibling.classList.contains('date-group-row')) {
            if (nextSibling.classList.contains('appointment-row')) {
                nextRows.push(nextSibling);
            }
            nextSibling = nextSibling.nextElementSibling;
        }
        
        // 檢查是否有可見的預約行
        const hasVisibleRows = nextRows.some(row => row.style.display !== 'none');
        
        // 顯示或隱藏日期分組行
        dateGroup.style.display = hasVisibleRows ? '' : 'none';
    });
}

function showNoResultsMessage() {
    const tbody = document.getElementById('appointmentsTableBody');
    if (tbody && !document.querySelector('.no-results-row')) {
        const noResultsRow = document.createElement('tr');
        noResultsRow.className = 'no-results-row';
        noResultsRow.innerHTML = `
            <td colspan="7" class="empty-appointments">
                <i class="bi bi-search"></i>
                <h3>找不到相符的預約</h3>
                <p>請嘗試使用不同的關鍵字搜尋</p>
                <button class="btn-vet btn-vet-secondary btn-vet-sm" onclick="clearSearch()">
                    <i class="bi bi-x"></i>
                    清除搜尋
                </button>
            </td>
        `;
        tbody.appendChild(noResultsRow);
    }
}

function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = '';
        searchQuery = '';
        performSearch();
    }
    
    // 移除無結果訊息
    const noResultsRow = document.querySelector('.no-results-row');
    if (noResultsRow) {
        noResultsRow.remove();
    }
}

// ========== 篩選功能 ==========
function initializeFilterFunctionality() {
    try {
        const filterTags = document.querySelectorAll('.filter-tag');
        
        filterTags.forEach(tag => {
            tag.addEventListener('click', function() {
                // 移除其他標籤的 active 狀態
                filterTags.forEach(t => t.classList.remove('active'));
                
                // 設置當前標籤為 active
                this.classList.add('active');
                
                currentFilter = this.dataset.filter;
                applyFilter(currentFilter);
            });
        });
        
        console.log('篩選功能初始化完成');
    } catch (error) {
        console.error('篩選功能初始化失敗:', error);
    }
}

function applyFilter(filter) {
    const rows = document.querySelectorAll('.appointment-row');
    const today = new Date().toISOString().split('T')[0];
    const oneWeekFromNow = new Date();
    oneWeekFromNow.setDate(oneWeekFromNow.getDate() + 7);
    const weekEnd = oneWeekFromNow.toISOString().split('T')[0];
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        const status = row.dataset.status;
        const appointmentDate = row.dataset.date;
        let shouldShow = false;
        
        switch (filter) {
            case 'all':
                shouldShow = true;
                break;
            case 'today':
                shouldShow = appointmentDate === today;
                break;
            case 'week':
                shouldShow = appointmentDate >= today && appointmentDate <= weekEnd;
                break;
            case 'pending':
                shouldShow = status === 'pending';
                break;
            case 'confirmed':
                shouldShow = status === 'confirmed';
                break;
            case 'completed':
                shouldShow = status === 'completed';
                break;
            case 'cancelled':
                shouldShow = status === 'cancelled';
                break;
        }
        
        if (shouldShow) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // 更新日期分組顯示
    updateDateGroupVisibility();
    
    // 如果有搜尋條件，同時應用搜尋
    if (searchQuery) {
        performSearch();
    }
    
    console.log(`篩選 "${filter}" 顯示 ${visibleCount} 筆預約`);
}

// ========== 表格互動功能 ==========
function initializeTableInteractions() {
    try {
        // 預約行點擊事件
        const appointmentRows = document.querySelectorAll('.appointment-row');
        appointmentRows.forEach(row => {
            // 添加hover效果的輔助
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8fafc';
            });
            
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
        
        console.log('表格互動功能初始化完成');
    } catch (error) {
        console.error('表格互動功能初始化失敗:', error);
    }
}

// ========== 表單處理 ==========
function initializeFormHandling() {
    try {
        // 取消預約表單
        const cancelForms = document.querySelectorAll('.cancel-form');
        cancelForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                handleCancelAppointment(this);
            });
        });
        
        console.log('表單處理初始化完成');
    } catch (error) {
        console.error('表單處理初始化失敗:', error);
    }
}

function handleCancelAppointment(form) {
    const reasonInput = form.querySelector('.cancel-reason-input');
    const reason = reasonInput.value.trim();
    
    if (!reason) {
        showWarningMessage('請填寫取消原因');
        reasonInput.focus();
        return;
    }
    
    // 顯示載入狀態
    showLoadingModal();
    
    // 提交表單
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingModal();
        
        if (data.success) {
            showSuccessMessage('預約已成功取消');
            
            // 更新頁面顯示
            const appointmentRow = form.closest('.appointment-row');
            if (appointmentRow) {
                // 更新狀態
                const statusBadge = appointmentRow.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge cancelled';
                    statusBadge.textContent = '已取消';
                }
                
                // 隱藏操作按鈕
                const actionsCell = appointmentRow.querySelector('.appointment-actions');
                if (actionsCell) {
                    actionsCell.innerHTML = '<span class="text-muted">已取消</span>';
                }
            }
            
            // 更新統計數據
            updateAppointmentCounts();
            
        } else {
            showErrorMessage(data.message || '取消預約失敗');
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('取消預約錯誤:', error);
        showErrorMessage('取消預約失敗，請稍後重試');
    });
}

// ========== 其他功能函數 ==========
function refreshAppointments() {
    console.log('重新整理預約資料...');
    showLoadingModal();
    
    // 重新載入頁面
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

function exportAppointments() {
    console.log('匯出預約資料...');
    
    if (appointmentsData.urls && appointmentsData.urls.export) {
        // 建立匯出參數
        const params = new URLSearchParams({
            filter: currentFilter,
            search: searchQuery,
            history: appointmentsData.showHistory
        });
        
        // 開啟匯出 URL
        window.open(`${appointmentsData.urls.export}?${params.toString()}`, '_blank');
        
        showInfoMessage('開始匯出預約資料...');
    } else {
        showInfoMessage('匯出功能開發中');
    }
}

function updateAppointmentCounts() {
    try {
        const visibleRows = document.querySelectorAll('.appointment-row:not([style*="display: none"])');
        const totalElement = document.getElementById('totalAppointments');
        
        if (totalElement && currentFilter !== 'all') {
            totalElement.textContent = visibleRows.length;
        }
        
        // 更新其他統計數據
        const statusCounts = {
            pending: 0,
            confirmed: 0,
            completed: 0,
            cancelled: 0
        };
        
        visibleRows.forEach(row => {
            const status = row.dataset.status;
            if (statusCounts.hasOwnProperty(status)) {
                statusCounts[status]++;
            }
        });
        
        // 更新顯示
        const pendingElement = document.getElementById('pendingAppointments');
        if (pendingElement) {
            pendingElement.textContent = statusCounts.pending;
        }
        
        const completedElement = document.getElementById('completedAppointments');
        if (completedElement) {
            completedElement.textContent = statusCounts.completed;
        }
        
    } catch (error) {
        console.error('更新統計數據失敗:', error);
    }
}

// ========== 鍵盤快捷鍵 ==========
function initializeKeyboardShortcuts() {
    try {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + F - 搜尋
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape - 清除搜尋
            if (e.key === 'Escape') {
                clearSearch();
            }
            
            // Ctrl/Cmd + R - 重新整理
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                refreshAppointments();
            }
        });
        
        console.log('鍵盤快捷鍵初始化完成');
    } catch (error) {
        console.error('鍵盤快捷鍵初始化失敗:', error);
    }
}

// ========== 載入狀態管理 ==========
function showLoadingModal() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        const modal = new bootstrap.Modal(loadingModal);
        modal.show();
    }
}

function hideLoadingModal() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) {
            modal.hide();
        }
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

// ========== 調試函數 ==========
function debugAppointments() {
    console.log('調試獸醫師預約管理...');
    
    console.log('預約數據:', appointmentsData);
    console.log('當前篩選:', currentFilter);
    console.log('搜尋查詢:', searchQuery);
    
    const keyElements = {
        appointmentsTable: document.getElementById('appointmentsTable'),
        searchInput: document.getElementById('searchInput'),
        filterTags: document.querySelectorAll('.filter-tag'),
        appointmentRows: document.querySelectorAll('.appointment-row')
    };
    
    console.log('關鍵元素:', keyElements);
    
    const visibleRows = document.querySelectorAll('.appointment-row:not([style*="display: none"])');
    console.log('可見行數:', visibleRows.length);
}

// ========== 全域函數導出 ==========
window.searchAppointments = searchAppointments;
window.clearSearch = clearSearch;
window.refreshAppointments = refreshAppointments;
window.exportAppointments = exportAppointments;
window.showSuccessMessage = showSuccessMessage;
window.showErrorMessage = showErrorMessage;
window.showWarningMessage = showWarningMessage;
window.showInfoMessage = showInfoMessage;
window.debugAppointments = debugAppointments;

// 頁面卸載時清理
window.addEventListener('beforeunload', function() {
    // 清理事件監聽器等
    console.log('清理預約管理頁面資源');
});

console.log('獸醫師預約管理 JavaScript 載入完成');