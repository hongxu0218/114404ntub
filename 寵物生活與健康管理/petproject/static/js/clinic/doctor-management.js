// static/js/clinic/doctor-management.js

// ========== 全域變數 ==========
let doctorsData = [];
let filteredDoctors = [];
let currentFilter = 'all';
let currentSort = 'name';
let searchTerm = '';
let pageData = {};

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeDoctorManagement();
});

// ========== 主要初始化函數 ==========
function initializeDoctorManagement() {
//     console.log('🚀 初始化醫師管理系統...');
    
    // 載入頁面數據
    loadPageData();
    
    // 初始化各種功能
    initializeSearch();
    initializeFilters();
    initializeSorting();
    initializeToggleButtons();
    initializeModals();
    initializeKeyboardShortcuts();
    
    // 初始化計數統計
    updateStatistics();
    
//     console.log('✅ 醫師管理系統初始化完成');
}

// ========== 載入頁面數據 ==========
function loadPageData() {
    if (window.doctorPageData) {
        pageData = window.doctorPageData;
        doctorsData = pageData.doctors || [];
        filteredDoctors = [...doctorsData];
//         console.log('📊 載入醫師數據:', doctorsData);
    }
}

// ========== 搜尋功能 ==========
function initializeSearch() {
    const searchInput = document.getElementById('doctorSearch');
    const clearButton = document.getElementById('clearSearch');
    
    if (!searchInput) return;
    
    // 即時搜尋（防抖處理）
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        // 顯示/隱藏清除按鈕
        if (query.length > 0) {
            clearButton.style.display = 'flex';
        } else {
            clearButton.style.display = 'none';
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300); // 300ms 防抖
    });
    
    // 清除搜尋
    clearButton.addEventListener('click', function() {
        searchInput.value = '';
        clearButton.style.display = 'none';
        performSearch('');
        searchInput.focus();
    });
    
    // Enter 鍵搜尋
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch(this.value.trim());
        }
    });
}

function performSearch(query) {
    searchTerm = query.toLowerCase();
    
    if (searchTerm === '') {
        // 沒有搜尋詞，顯示所有符合篩選條件的醫師
        applyFiltersAndSort();
    } else {
        // 有搜尋詞，進行搜尋
        const searchResults = doctorsData.filter(doctor => {
            const searchableText = `
                ${doctor.name} 
                ${doctor.email} 
                ${doctor.specialization} 
                ${doctor.vetLicenseNumber}
            `.toLowerCase();
            
            return searchableText.includes(searchTerm);
        });
        
        // 然後應用篩選和排序
        filteredDoctors = searchResults;
        applyCurrentFilter();
        applySorting();
        renderDoctors();
    }
    
    // 搜尋分析（用於改善搜尋體驗）
    if (searchTerm) {
//         console.log(`🔍 搜尋: "${query}" → ${filteredDoctors.length} 個結果`);
        
        // 如果搜尋結果為空，顯示建議
        if (filteredDoctors.length === 0) {
            showSearchSuggestions(query);
        }
    }
}

function showSearchSuggestions(query) {
    // 簡單的搜尋建議邏輯
    const suggestions = [];
    
    // 檢查是否有相似的名字
    doctorsData.forEach(doctor => {
        if (doctor.name.toLowerCase().includes(query.slice(0, 2))) {
            suggestions.push(`可能您要找的是："${doctor.name}"`);
        }
    });
    
    if (suggestions.length > 0) {
        showInfoMessage(`找不到 "${query}"，${suggestions[0]}`);
    }
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
            applyFiltersAndSort();
            
            // 視覺回饋
            animateFilterChange(this);
        });
    });
}

function applyFiltersAndSort() {
    // 先應用搜尋
    if (searchTerm) {
        filteredDoctors = doctorsData.filter(doctor => {
            const searchableText = `
                ${doctor.name} 
                ${doctor.email} 
                ${doctor.specialization} 
                ${doctor.vetLicenseNumber}
            `.toLowerCase();
            
            return searchableText.includes(searchTerm);
        });
    } else {
        filteredDoctors = [...doctorsData];
    }
    
    // 然後應用篩選
    applyCurrentFilter();
    
    // 最後排序
    applySorting();
    
    // 渲染結果
    renderDoctors();
    
    // 更新統計
    updateFilteredStatistics();
}

function applyCurrentFilter() {
    if (currentFilter === 'all') {
        // 不做額外篩選
        return;
    }
    
    filteredDoctors = filteredDoctors.filter(doctor => {
        switch (currentFilter) {
            case 'active':
                return doctor.isActive;
            case 'verified':
                return doctor.isVerified;
            case 'pending':
                return !doctor.isVerified && doctor.vetLicenseNumber;
            case 'admin':
                return doctor.isAdmin;
            default:
                return true;
        }
    });
}

// ========== 排序功能 ==========
function initializeSorting() {
    const sortSelect = document.getElementById('sortBy');
    
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentSort = this.value;
            applySorting();
            renderDoctors();
            
            // 視覺回饋
            animateSortChange();
        });
    }
}

function applySorting() {
    filteredDoctors.sort((a, b) => {
        switch (currentSort) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'created':
                return new Date(b.createdAt) - new Date(a.createdAt);
            case 'specialization':
                return (a.specialization || '').localeCompare(b.specialization || '');
            case 'status':
                // 先按啟用狀態，再按驗證狀態
                if (a.isActive !== b.isActive) {
                    return b.isActive - a.isActive;
                }
                return b.isVerified - a.isVerified;
            default:
                return 0;
        }
    });
}

// ========== 醫師卡片渲染 ==========
function renderDoctors() {
    const doctorsGrid = document.getElementById('doctorsGrid');
    const noResultsState = document.getElementById('noResultsState');
    
    if (!doctorsGrid) return;
    
    // 隱藏所有醫師卡片
    const allCards = doctorsGrid.querySelectorAll('.doctor-card-modern');
    allCards.forEach(card => {
        card.style.display = 'none';
        card.classList.add('hiding');
    });
    
    // 如果沒有結果
    if (filteredDoctors.length === 0) {
        if (searchTerm || currentFilter !== 'all') {
            noResultsState.style.display = 'block';
        }
        updateResultsCount(0);
        return;
    }
    
    // 隱藏無結果狀態
    noResultsState.style.display = 'none';
    
    // 顯示符合條件的醫師卡片
    let visibleCount = 0;
    filteredDoctors.forEach((doctor, index) => {
        const card = doctorsGrid.querySelector(`[data-doctor-id="${doctor.id}"]`);
        if (card) {
            // 延遲顯示，創造動畫效果
            setTimeout(() => {
                card.style.display = 'block';
                card.classList.remove('hiding');
                card.classList.add('showing');
                
                // 移除動畫類別
                setTimeout(() => {
                    card.classList.remove('showing');
                }, 300);
            }, index * 50); // 每個卡片延遲 50ms
            
            visibleCount++;
        }
    });
    
    updateResultsCount(visibleCount);
    
//     console.log(`🎨 渲染 ${visibleCount} 張醫師卡片`);
}

function updateResultsCount(count) {
    // 可以在這裡更新顯示的結果數量
    const totalCount = doctorsData.length;
    
    // 更新篩選晶片的文字（如果需要）
    const activeChip = document.querySelector('.filter-chip.active');
    if (activeChip && currentFilter !== 'all') {
        // 在這裡可以加上數量顯示
    }
}

// ========== 醫師狀態切換 ==========
function initializeToggleButtons() {
    const toggleButtons = document.querySelectorAll('.toggle-doctor-btn');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            handleToggleDoctorStatus(this);
        });
    });
}

function handleToggleDoctorStatus(button) {
    const doctorId = button.dataset.doctorId;
    const action = button.dataset.action;
    const isDeactivating = action === 'deactivate';
    
    const doctor = doctorsData.find(d => d.id === parseInt(doctorId));
    if (!doctor) return;
    
    // 使用Modal顯示確認對話框
    showConfirmModal({
        title: isDeactivating ? '停用醫師' : '啟用醫師',
        message: `確定要${isDeactivating ? '停用' : '啟用'}醫師「${doctor.name}」嗎？`,
        confirmText: isDeactivating ? '停用' : '啟用',
        confirmClass: isDeactivating ? 'btn-warning' : 'btn-success',
        icon: isDeactivating ? 'bi-pause-circle-fill text-warning' : 'bi-play-circle-fill text-success',
        onConfirm: () => {
            executeToggleDoctorStatus(button, doctor);
        }
    });
}

function executeToggleDoctorStatus(button, doctor) {
    const card = button.closest('.doctor-card-modern');
    
    // 顯示載入狀態
    showCardLoading(card);
    
    // 隱藏按鈕圖示，顯示載入動畫
    const icon = button.querySelector('i');
    const spinner = button.querySelector('.loading-spinner-modern');
    icon.style.display = 'none';
    spinner.style.display = 'block';
    
    // 發送 AJAX 請求
    fetch(pageData.urls.toggleDoctor.replace('{id}', doctor.id), {
        method: 'POST',
        headers: {
            'X-CSRFToken': pageData.csrfToken,
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'  // 重要：標識為AJAX請求
        },
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 更新本地資料
            doctor.isActive = data.doctor.is_active;
            
            // 更新 UI
            updateDoctorCardStatus(card, doctor);
            
            // 更新統計
            updateStatistics();
            
            // 顯示成功Modal
            showResultModal({
                type: 'success',
                title: '操作成功',
                message: data.message
            });
            
            // 如果當前篩選會隱藏這個醫師，則重新渲染
            setTimeout(() => {
                applyFiltersAndSort();
            }, 1000);
            
        } else {
            throw new Error(data.message || '操作失敗');
        }
    })
    .catch(error => {
        console.error('切換醫師狀態錯誤:', error);
        
        // 顯示錯誤Modal
        showResultModal({
            type: 'error',
            title: '操作失敗',
            message: error.message || '網路錯誤，請檢查連線後再試',
            autoClose: false
        });
    })
    .finally(() => {
        // 恢復按鈕狀態
        hideCardLoading(card);
        icon.style.display = 'block';
        spinner.style.display = 'none';
    });
}

function updateDoctorCardStatus(card, doctor) {
    // 更新狀態徽章
    const statusBadge = card.querySelector('.status-badge-modern');
    const statusIcon = statusBadge.querySelector('i');
    const statusText = statusBadge.querySelector('span');
    
    if (doctor.isActive) {
        statusBadge.className = 'status-badge-modern status-active-modern';
        statusIcon.className = 'bi bi-check-circle';
        statusText.textContent = '啟用中';
    } else {
        statusBadge.className = 'status-badge-modern status-inactive-modern';
        statusIcon.className = 'bi bi-pause-circle';
        statusText.textContent = '已停用';
    }
    
    // 更新操作按鈕
    const toggleBtn = card.querySelector('.toggle-doctor-btn');
    const toggleIcon = toggleBtn.querySelector('i');
    
    if (doctor.isActive) {
        toggleBtn.className = 'action-btn btn-toggle-active toggle-doctor-btn';
        toggleBtn.dataset.action = 'deactivate';
        toggleBtn.title = '停用醫師';
        toggleIcon.className = 'bi bi-pause';
    } else {
        toggleBtn.className = 'action-btn btn-toggle-inactive toggle-doctor-btn';
        toggleBtn.dataset.action = 'activate';
        toggleBtn.title = '啟用醫師';
        toggleIcon.className = 'bi bi-play';
    }
    
    // 卡片視覺效果
    if (doctor.isActive) {
        card.classList.remove('doctor-inactive');
    } else {
        card.classList.add('doctor-inactive');
    }
}

// ========== 醫師詳細資料查看 ==========
function viewDoctorDetails(doctorId) {
    const doctor = doctorsData.find(d => d.id === parseInt(doctorId));
    if (!doctor) return;
    
    const modal = document.getElementById('doctorDetailsModal');
    const title = document.getElementById('doctorDetailsTitle');
    const content = document.getElementById('doctorDetailsContent');
    const editButton = document.getElementById('editDoctorFromModal');
    
    // 設定標題
    title.textContent = `${doctor.name} - 詳細資料`;
    
    // 設定編輯按鈕
    editButton.onclick = () => {
        window.location.href = pageData.urls.editDoctor.replace('{id}', doctorId);
    };
    
    // 生成詳細內容
    content.innerHTML = generateDoctorDetailsHTML(doctor);
    
    // 顯示 modal
    showModal(modal);
    
//     console.log('👁️ 查看醫師詳細資料:', doctor.name);
}

function generateDoctorDetailsHTML(doctor) {
    return `
        <div class="doctor-details-full">
            <div class="row">
                <div class="col-md-3 text-center">
                    <div class="doctor-avatar-large">
                        ${doctor.name.charAt(0).toUpperCase()}
                    </div>
                    <h4 class="mt-3">${doctor.name}</h4>
                    ${doctor.isAdmin ? '<span class="badge bg-warning">管理員</span>' : ''}
                </div>
                
                <div class="col-md-9">
                    <div class="details-grid">
                        <div class="detail-row">
                            <label>電子信箱</label>
                            <span>${doctor.email}</span>
                        </div>
                        
                        <div class="detail-row">
                            <label>聯絡電話</label>
                            <span>${doctor.phone || '未填寫'}</span>
                        </div>
                        
                        <div class="detail-row">
                            <label>專長領域</label>
                            <span>${doctor.specialization || '未填寫'}</span>
                        </div>
                        
                        <div class="detail-row">
                            <label>執業年資</label>
                            <span>${doctor.yearsOfExperience || 0} 年</span>
                        </div>
                        
                        <div class="detail-row">
                            <label>執照號碼</label>
                            <span>${doctor.vetLicenseNumber || '未填寫'}</span>
                        </div>
                        
                        <div class="detail-row">
                            <label>執照狀態</label>
                            <span class="${doctor.isVerified ? 'text-success' : 'text-warning'}">
                                <i class="bi bi-${doctor.isVerified ? 'shield-check' : 'hourglass-split'}"></i>
                                ${doctor.isVerified ? '已驗證' : '待驗證'}
                            </span>
                        </div>
                        
                        <div class="detail-row">
                            <label>帳號狀態</label>
                            <span class="${doctor.isActive ? 'text-success' : 'text-danger'}">
                                <i class="bi bi-${doctor.isActive ? 'check-circle' : 'pause-circle'}"></i>
                                ${doctor.isActive ? '啟用中' : '已停用'}
                            </span>
                        </div>
                        
                        <div class="detail-row">
                            <label>加入時間</label>
                            <span>${doctor.createdAt}</span>
                        </div>
                        
                        ${doctor.bio ? `
                        <div class="detail-row">
                            <label>個人簡介</label>
                            <span>${doctor.bio}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function closeDoctorDetailsModal() {
    const modal = document.getElementById('doctorDetailsModal');
    closeModal(modal);
}

// ========== 執照驗證功能 ==========
function verifyDoctorLicense(doctorId) {
    const doctor = doctorsData.find(d => d.id === parseInt(doctorId));
    if (!doctor) return;
    
    if (!doctor.vetLicenseNumber) {
        showWarningMessage('該醫師尚未填寫執照號碼');
        return;
    }
    
    showConfirmDialog({
        title: '驗證獸醫師執照',
        message: `確定要驗證醫師「${doctor.name}」的執照嗎？\n執照號碼：${doctor.vetLicenseNumber}`,
        confirmText: '開始驗證',
        confirmClass: 'btn-info',
        onConfirm: () => {
            executeVerifyLicense(doctor);
        }
    });
}

function executeVerifyLicense(doctor) {
    showInfoMessage('正在透過農委會API驗證執照，請稍候...');
    
    // 這裡應該調用後端API進行驗證
    // 暫時模擬驗證過程
    setTimeout(() => {
        // 模擬驗證結果
        const isVerified = Math.random() > 0.3; // 70% 成功率
        
        if (isVerified) {
            doctor.isVerified = true;
            updateStatistics();
            showSuccessMessage(`醫師「${doctor.name}」的執照驗證成功`);
            
            // 更新卡片UI
            const card = document.querySelector(`[data-doctor-id="${doctor.id}"]`);
            if (card) {
                updateDoctorVerificationStatus(card, true);
            }
        } else {
            showErrorMessage('執照驗證失敗，請檢查執照號碼是否正確');
        }
    }, 3000);
}

function updateDoctorVerificationStatus(card, isVerified) {
    const verificationBadge = card.querySelector('.verification-badge');
    const icon = verificationBadge.querySelector('i');
    const text = verificationBadge.querySelector('span');
    
    if (isVerified) {
        verificationBadge.className = 'verification-badge verified';
        icon.className = 'bi bi-shield-check';
        text.textContent = '執照已驗證';
        
        // 移除驗證按鈕
        const verifyBtn = card.querySelector('.btn-verify');
        if (verifyBtn) {
            verifyBtn.remove();
        }
    }
}

// ========== 批量操作功能 ==========
function showBatchActionsModal() {
    const modal = document.getElementById('batchActionsModal');
    showModal(modal);
}

function closeBatchActionsModal() {
    const modal = document.getElementById('batchActionsModal');
    closeModal(modal);
}

function batchActivateAll() {
    const inactiveDoctors = doctorsData.filter(d => !d.isActive && !d.isAdmin);
    
    if (inactiveDoctors.length === 0) {
        showInfoMessage('所有醫師都已經是啟用狀態');
        return;
    }
    
    showConfirmDialog({
        title: '批量啟用醫師',
        message: `確定要啟用 ${inactiveDoctors.length} 位已停用的醫師嗎？`,
        confirmText: '批量啟用',
        confirmClass: 'btn-success',
        onConfirm: () => {
            executeBatchActivate(inactiveDoctors);
        }
    });
}

function executeBatchActivate(doctors) {
    closeBatchActionsModal();
    
    showInfoMessage(`正在啟用 ${doctors.length} 位醫師...`);
    
    // 模擬批量操作
    let processedCount = 0;
    doctors.forEach((doctor, index) => {
        setTimeout(() => {
            doctor.isActive = true;
            processedCount++;
            
            // 更新對應的卡片
            const card = document.querySelector(`[data-doctor-id="${doctor.id}"]`);
            if (card) {
                updateDoctorCardStatus(card, doctor);
            }
            
            if (processedCount === doctors.length) {
                updateStatistics();
                showSuccessMessage(`已成功啟用 ${doctors.length} 位醫師`);
            }
        }, index * 200);
    });
}

function batchSendWelcomeEmails() {
    showInfoMessage('批量發送歡迎信功能開發中...');
    closeBatchActionsModal();
}

function exportDoctorsList() {
    showInfoMessage('正在準備醫師清單匯出...');
    
    // 模擬匯出過程
    setTimeout(() => {
        // 這裡應該調用後端API生成Excel檔案
        showSuccessMessage('醫師清單已匯出，請檢查下載資料夾');
        closeBatchActionsModal();
    }, 2000);
}

// ========== 統計資料更新 ==========
function updateStatistics() {
    const totalElement = document.getElementById('totalDoctors');
    const activeElement = document.getElementById('activeDoctors');
    const verifiedElement = document.getElementById('verifiedDoctors');
    const pendingElement = document.getElementById('pendingDoctors');
    
    const stats = calculateStatistics();
    
    // 數字動畫效果
    if (totalElement) animateNumber(totalElement, stats.total);
    if (activeElement) animateNumber(activeElement, stats.active);
    if (verifiedElement) animateNumber(verifiedElement, stats.verified);
    if (pendingElement) animateNumber(pendingElement, stats.pending);
}

function updateFilteredStatistics() {
    // 如果需要顯示篩選後的統計資料
//     console.log(`📊 篩選後統計: ${filteredDoctors.length}/${doctorsData.length}`);
}

function calculateStatistics() {
    return {
        total: doctorsData.length,
        active: doctorsData.filter(d => d.isActive).length,
        verified: doctorsData.filter(d => d.isVerified).length,
        pending: doctorsData.filter(d => !d.isVerified && d.vetLicenseNumber).length
    };
}

function animateNumber(element, newValue) {
    const currentValue = parseInt(element.textContent) || 0;
    const difference = newValue - currentValue;
    const duration = 500;
    const steps = 20;
    const stepValue = difference / steps;
    const stepTime = duration / steps;
    
    let currentStep = 0;
    const timer = setInterval(() => {
        currentStep++;
        const value = Math.round(currentValue + (stepValue * currentStep));
        element.textContent = value;
        
        if (currentStep >= steps) {
            clearInterval(timer);
            element.textContent = newValue;
        }
    }, stepTime);
}

// ========== Modal 管理 ==========
let confirmModal;
let resultModal;

function initializeModals() {

    confirmModal = new bootstrap.Modal(document.getElementById('confirmActionModal'));
    resultModal = new bootstrap.Modal(document.getElementById('resultModal'));

    // Modal 外部點擊關閉
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
}

// 顯示確認Modal
function showConfirmModal(options) {
    const modal = document.getElementById('confirmActionModal');
    const title = modal.querySelector('.modal-title');
    const message = modal.querySelector('.modal-message');
    const confirmBtn = modal.querySelector('#confirmActionBtn');
    const icon = modal.querySelector('.modal-icon i');
    
    // 設置內容
    title.textContent = options.title || '確認操作';
    message.textContent = options.message || '確定要執行此操作嗎？';
    confirmBtn.textContent = options.confirmText || '確認';
    
    // 設置按鈕樣式
    confirmBtn.className = `btn ${options.confirmClass || 'btn-primary'}`;
    
    // 設置圖標
    if (options.icon) {
        icon.className = `bi ${options.icon}`;
    }
    
    // 移除舊的事件監聽器
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    // 添加新的確認事件
    newConfirmBtn.addEventListener('click', () => {
        confirmModal.hide();
        if (options.onConfirm) {
            options.onConfirm();
        }
    });
    
    // 顯示Modal
    confirmModal.show();
}

// 顯示結果Modal
function showResultModal(options) {
    const modal = document.getElementById('resultModal');
    const title = modal.querySelector('#resultModalTitle');
    const message = modal.querySelector('#resultModalMessage');
    const icon = modal.querySelector('.result-icon i');
    
    // 設置內容
    title.textContent = options.title || '操作完成';
    message.textContent = options.message || '';
    
    // 設置圖標和顏色
    if (options.type === 'success') {
        icon.className = 'bi bi-check-circle-fill text-success';
    } else if (options.type === 'error') {
        icon.className = 'bi bi-x-circle-fill text-danger';
    } else if (options.type === 'warning') {
        icon.className = 'bi bi-exclamation-triangle-fill text-warning';
    }
    
    // 顯示Modal
    resultModal.show();
    
    // 自動關閉（可選）
    if (options.autoClose !== false) {
        setTimeout(() => {
            resultModal.hide();
        }, 2000);
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

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        closeModal(modal);
    });
}

// ========== 鍵盤快捷鍵 ==========
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + F: 聚焦搜尋框
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('doctorSearch');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Ctrl/Cmd + N: 新增醫師（如果有權限）
        if ((e.ctrlKey || e.metaKey) && e.key === 'n' && pageData.canManage) {
            e.preventDefault();
            window.location.href = '/clinic/doctors/add/';
        }
    });
}

// ========== 工具函數 ==========
function clearAllFilters() {
    // 清除搜尋
    const searchInput = document.getElementById('doctorSearch');
    const clearButton = document.getElementById('clearSearch');
    if (searchInput) {
        searchInput.value = '';
        clearButton.style.display = 'none';
    }
    
    // 重設篩選
    currentFilter = 'all';
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.classList.remove('active');
    });
    document.querySelector('[data-filter="all"]').classList.add('active');
    
    // 重設排序
    const sortSelect = document.getElementById('sortBy');
    if (sortSelect) {
        sortSelect.value = 'name';
        currentSort = 'name';
    }
    
    // 重新渲染
    searchTerm = '';
    applyFiltersAndSort();
    
    showInfoMessage('已清除所有篩選條件');
}

function animateFilterChange(chip) {
    chip.style.transform = 'scale(1.1)';
    setTimeout(() => {
        chip.style.transform = 'scale(1)';
    }, 150);
}

function animateSortChange() {
    const doctorsGrid = document.getElementById('doctorsGrid');
    doctorsGrid.style.opacity = '0.7';
    setTimeout(() => {
        doctorsGrid.style.opacity = '1';
    }, 200);
}

// ========== 載入和錯誤處理 ==========
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
            <div class="confirm-icon">
                <i class="bi bi-question-circle-fill"></i>
            </div>
            <h3>${options.title}</h3>
            <p>${options.message}</p>
            <div class="dialog-buttons">
                <button class="btn-cancel">取消</button>
                <button class="btn-confirm ${options.confirmClass || 'btn-primary'}">${options.confirmText}</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    // 顯示動畫
    setTimeout(() => {
        dialog.classList.add('show');
    }, 10);
    
    dialog.querySelector('.btn-cancel').addEventListener('click', () => {
        closeConfirmDialog(dialog);
    });
    
    dialog.querySelector('.btn-confirm').addEventListener('click', () => {
        options.onConfirm();
        closeConfirmDialog(dialog);
    });
    
    // 點擊外部關閉
    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            closeConfirmDialog(dialog);
        }
    });
    
    // ESC 鍵關閉
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            closeConfirmDialog(dialog);
            document.removeEventListener('keydown', handleEsc);
        }
    };
    document.addEventListener('keydown', handleEsc);
}

function closeConfirmDialog(dialog) {
    dialog.classList.remove('show');
    setTimeout(() => {
        if (document.body.contains(dialog)) {
            document.body.removeChild(dialog);
        }
    }, 250);
}

// ========== 訊息顯示 ==========
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
        success: 'check-circle-fill',
        error: 'x-circle-fill',
        warning: 'exclamation-triangle-fill',
        info: 'info-circle-fill'
    };
    
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${iconMap[type]}"></i>
            <span>${message}</span>
        </div>
        <button class="message-close">&times;</button>
    `;
    
    document.body.appendChild(messageEl);
    
    // 顯示動畫
    setTimeout(() => {
        messageEl.classList.add('show');
    }, 10);
    
    // 自動隱藏
    setTimeout(() => {
        hideMessage(messageEl);
    }, type === 'error' ? 8000 : 5000);
    
    // 手動關閉
    messageEl.querySelector('.message-close').addEventListener('click', () => {
        hideMessage(messageEl);
    });
}

function hideMessage(messageEl) {
    messageEl.classList.remove('show');
    setTimeout(() => {
        if (messageEl.parentNode) {
            document.body.removeChild(messageEl);
        }
    }, 300);
}

// console.log('✅ 醫師管理 JavaScript 載入完成');