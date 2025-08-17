// ========== 改良版編輯醫師 JavaScript ==========

// ========== 全域變數 ==========
let currentTab = 'basic';
let formChanged = false;
let autoSaveTimeout = null;
let isSubmitting = false;
let licenseNumberVisible = false;

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeEditDoctorForm();
});

// ========== 主要初始化函數 ==========
function initializeEditDoctorForm() {
    console.log('🚀 初始化編輯醫師表單...');
    
    // 初始化各種功能
    initializeTabNavigation();
    initializeFormValidation();
    initializeAutoSave();
    initializeCharacterCounter();
    initializeLicenseManagement();
    initializeSecurityActions();
    initializeFormSubmission();
    initializePrivacyProtection();
    
    // 檢查執照驗證功能支援
    if (window.doctorData && !window.doctorData.isVerified) {
        setTimeout(() => {
            checkLicenseVerificationSupport();
        }, 1000);
    }
    
    // 設定初始狀態
    updateTabDisplay();
    
    console.log('✅ 編輯醫師表單初始化完成');
}

// ========== 隱私保護功能 ==========
function initializePrivacyProtection() {
    // 添加顯示/隱藏執照號碼功能
    const showLicenseBtn = document.getElementById('toggleLicenseVisibility');
    if (showLicenseBtn) {
        showLicenseBtn.addEventListener('click', toggleLicenseVisibility);
    }
}

function toggleLicenseVisibility() {
    const doctorData = window.doctorData;
    if (!doctorData || !doctorData.licenseNumber) {
        showErrorMessage('無法獲取執照資訊');
        return;
    }
    
    const toggleBtn = document.getElementById('toggleLicenseVisibility');
    const licenseContainer = document.querySelector('.license-number-protected');
    
    if (!toggleBtn || !licenseContainer) {
        console.error('找不到執照顯示元素');
        return;
    }
    
    if (!licenseNumberVisible) {
        // 顯示完整執照號碼
        showFullLicenseNumber(doctorData.licenseNumber, toggleBtn, licenseContainer);
        licenseNumberVisible = true;
        
        // 3秒後自動隱藏
        setTimeout(() => {
            if (licenseNumberVisible) {
                hideFullLicenseNumber(doctorData.licenseNumber, toggleBtn, licenseContainer);
                licenseNumberVisible = false;
            }
        }, 3000);
        
        showInfoMessage('執照號碼將在3秒後自動隱藏', 'info');
    } else {
        // 隱藏執照號碼
        hideFullLicenseNumber(doctorData.licenseNumber, toggleBtn, licenseContainer);
        licenseNumberVisible = false;
    }
}

function showFullLicenseNumber(fullNumber, toggleBtn, container) {
    // 找到顯示遮罩號碼的元素
    const maskedElement = container.querySelector('.license-number-masked');
    if (maskedElement) {
        // 顯示完整號碼
        maskedElement.textContent = `執照號碼：${fullNumber}`;
        maskedElement.style.color = 'var(--danger-color)';
        maskedElement.style.fontWeight = 'bold';
    }
    
    // 更新按鈕
    toggleBtn.innerHTML = '<i class="bi bi-eye-slash"></i> 隱藏號碼';
    toggleBtn.classList.remove('btn-outline-secondary');
    toggleBtn.classList.add('btn-outline-danger');
}

function hideFullLicenseNumber(fullNumber, toggleBtn, container) {
    // 找到顯示號碼的元素
    const maskedElement = container.querySelector('.license-number-masked');
    if (maskedElement) {
        // 恢復遮罩顯示（優先使用預計算的遮罩）
        const maskedNumber = window.doctorData?.licenseNumberMasked || 
                           (fullNumber.length > 4 ? 
                            fullNumber.substring(0, 2) + '****' + fullNumber.substring(fullNumber.length - 2) : 
                            '****');
        maskedElement.textContent = `執照號碼：${maskedNumber}`;
        maskedElement.style.color = '';
        maskedElement.style.fontWeight = '';
    }
    
    // 更新按鈕
    toggleBtn.innerHTML = '<i class="bi bi-eye"></i> 顯示完整號碼';
    toggleBtn.classList.remove('btn-outline-danger');
    toggleBtn.classList.add('btn-outline-secondary');
}

// ========== 標籤導航功能 ==========
function initializeTabNavigation() {
    const tabLinks = document.querySelectorAll('.nav-link-modern');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetTab = this.dataset.tab;
            if (targetTab !== currentTab) {
                switchTab(targetTab);
            }
        });
    });
}

function switchTab(targetTab) {
    // 如果有未儲存的變更，提示用戶
    if (formChanged) {
        if (!confirm('您有未儲存的變更，確定要切換標籤頁嗎？')) {
            return;
        }
    }
    
    currentTab = targetTab;
    updateTabDisplay();
    animateTabSwitch();
    
    // 記錄用戶行為
    console.log(`🔄 切換到標籤頁: ${targetTab}`);
}

function updateTabDisplay() {
    // 更新導航標籤
    const tabLinks = document.querySelectorAll('.nav-link-modern');
    tabLinks.forEach(link => {
        const isActive = link.dataset.tab === currentTab;
        link.classList.toggle('active', isActive);
        link.setAttribute('aria-selected', isActive);
    });
    
    // 更新內容區域
    const tabContents = document.querySelectorAll('.tab-content-modern');
    tabContents.forEach(content => {
        const isActive = content.dataset.content === currentTab;
        content.classList.toggle('active', isActive);
        content.setAttribute('aria-hidden', !isActive);
    });
}

function animateTabSwitch() {
    const activeContent = document.querySelector('.tab-content-modern.active');
    if (activeContent) {
        activeContent.style.opacity = '0';
        activeContent.style.transform = 'translateY(10px)';
        
        requestAnimationFrame(() => {
            activeContent.style.transition = 'all 0.3s ease-out';
            activeContent.style.opacity = '1';
            activeContent.style.transform = 'translateY(0)';
        });
    }
}

// ========== 表單驗證功能 ==========
function initializeFormValidation() {
    const form = document.getElementById('editDoctorForm');
    if (!form) return;
    
    // 即時驗證
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('blur', () => validateField(input));
        input.addEventListener('input', debounce(() => {
            clearFieldError(input);
            markFormChanged();
            validateField(input);
        }, 300));
    });
    
    // 特殊驗證處理
    const emailInput = document.querySelector('[name="email"]');
    if (emailInput) {
        emailInput.addEventListener('blur', debounce(validateEmailUniqueness, 500));
    }
}

function validateField(field) {
    const value = field.value.trim();
    
    // 必填驗證
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, '此欄位為必填');
        return false;
    }
    
    // 特定欄位驗證
    switch (field.type) {
        case 'email':
            if (value && !isValidEmail(value)) {
                showFieldError(field, '請輸入有效的電子郵件地址');
                return false;
            }
            break;
            
        case 'tel':
        case 'phone':
            if (field.name === 'phone_number' && value && !isValidPhone(value)) {
                showFieldError(field, '請輸入有效的台灣手機號碼（格式：09xxxxxxxx）');
                return false;
            }
            break;
            
        case 'number':
            if (field.name === 'years_of_experience' && value) {
                const years = parseInt(value);
                if (isNaN(years) || years < 0 || years > 50) {
                    showFieldError(field, '執業年資應在0-50年之間');
                    return false;
                }
            }
            break;
    }
    
    // 通過驗證
    clearFieldError(field);
    return true;
}

function validateEmailUniqueness() {
    const emailInput = document.querySelector('[name="email"]');
    if (!emailInput || !emailInput.value) return;
    
    const originalEmail = window.doctorData?.email;
    if (emailInput.value === originalEmail) return;
    
    // 檢查信箱唯一性
    showFieldLoading(emailInput, true);
    
    fetch('/clinic/check-email/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'Accept': 'application/json, text/html',
        },
        body: JSON.stringify({ email: emailInput.value })
    })
    .then(response => {
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else if (response.ok) {
            // 如果返回 HTML 但狀態正常，假設信箱可用
            return { available: true };
        } else {
            throw new Error('信箱檢查失敗');
        }
    })
    .then(data => {
        if (data && !data.available) {
            showFieldError(emailInput, '此信箱已被使用');
        } else {
            clearFieldError(emailInput);
        }
    })
    .catch(error => {
        console.error('信箱檢查失敗:', error);
        // 不顯示錯誤訊息，允許用戶繼續操作
        clearFieldError(emailInput);
    })
    .finally(() => {
        showFieldLoading(emailInput, false);
    });
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    
    feedback.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
    feedback.style.display = 'flex';
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.style.display = 'none';
    }
}

function showFieldLoading(field, show) {
    let loader = field.parentNode.querySelector('.field-loader');
    
    if (show) {
        if (!loader) {
            loader = document.createElement('div');
            loader.className = 'field-loader';
            loader.innerHTML = '<i class="bi bi-hourglass-split"></i>';
            field.parentNode.appendChild(loader);
        }
        loader.style.display = 'block';
    } else if (loader) {
        loader.style.display = 'none';
    }
}

// ========== 自動儲存功能 ==========
function initializeAutoSave() {
    const form = document.getElementById('editDoctorForm');
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', debounce(() => {
            markFormChanged();
            scheduleAutoSave();
        }, 1000));
    });
}

function markFormChanged() {
    formChanged = true;
    updateSaveButtonState();
    
    // 顯示未儲存指示器
    showUnsavedIndicator(true);
}

function scheduleAutoSave() {
    // 清除之前的自動儲存計時器
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    
    // 設定新的自動儲存計時器（5秒後執行）
    autoSaveTimeout = setTimeout(() => {
        if (formChanged && !isSubmitting) {
            performAutoSave();
        }
    }, 5000);
}

function performAutoSave() {
    console.log('💾 執行自動儲存...');
    
    const formData = new FormData(document.getElementById('editDoctorForm'));
    formData.append('auto_save', 'true');
    
    // 顯示自動儲存狀態
    showAutoSaveStatus('saving');
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Accept': 'application/json, text/html',
        }
    })
    .then(response => {
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else if (response.ok) {
            // 如果成功但返回 HTML，假設儲存成功
            return { success: true };
        } else {
            throw new Error('自動儲存失敗');
        }
    })
    .then(data => {
        if (data && data.success) {
            showAutoSaveStatus('saved');
            formChanged = false;
            updateSaveButtonState();
            showUnsavedIndicator(false);
        } else {
            showAutoSaveStatus('error');
        }
    })
    .catch(error => {
        console.error('自動儲存失敗:', error);
        showAutoSaveStatus('error');
    });
}

function showAutoSaveStatus(status) {
    const saveStatus = document.getElementById('saveStatus');
    if (!saveStatus) return;
    
    const statusConfig = {
        saving: { icon: 'hourglass-split', text: '自動儲存中...', class: 'text-info' },
        saved: { icon: 'check-circle', text: '已自動儲存', class: 'text-success' },
        error: { icon: 'exclamation-triangle', text: '自動儲存失敗', class: 'text-warning' }
    };
    
    const config = statusConfig[status];
    if (config) {
        saveStatus.innerHTML = `<i class="bi bi-${config.icon} me-1"></i><span>${config.text}</span>`;
        saveStatus.className = `save-status ${config.class}`;
        saveStatus.style.display = 'flex';
        
        if (status === 'saved') {
            setTimeout(() => {
                saveStatus.style.display = 'none';
            }, 3000);
        }
    }
}

function showUnsavedIndicator(show) {
    const indicator = document.querySelector('.unsaved-indicator') || createUnsavedIndicator();
    indicator.style.display = show ? 'block' : 'none';
}

function createUnsavedIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'unsaved-indicator';
    indicator.innerHTML = '<i class="bi bi-circle-fill"></i>';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        color: var(--warning-color);
        font-size: 12px;
        z-index: 1000;
        display: none;
    `;
    document.body.appendChild(indicator);
    return indicator;
}

function updateSaveButtonState() {
    const saveBtn = document.getElementById('saveBtn');
    if (!saveBtn) return;
    
    const btnText = saveBtn.querySelector('span');
    if (formChanged) {
        saveBtn.classList.add('btn-warning-modern');
        saveBtn.classList.remove('btn-primary-modern');
        if (btnText) btnText.textContent = '儲存變更';
    } else {
        saveBtn.classList.remove('btn-warning-modern');
        saveBtn.classList.add('btn-primary-modern');
        if (btnText) btnText.textContent = '已儲存';
    }
}

// ========== 字元計數器 ==========
function initializeCharacterCounter() {
    const bioTextarea = document.querySelector('[name="bio"]');
    
    if (bioTextarea) {
        bioTextarea.addEventListener('input', updateCharacterCounter);
        updateCharacterCounter(); // 初始化顯示
    }
}

function updateCharacterCounter() {
    const textarea = document.querySelector('[name="bio"]');
    const counter = document.querySelector('.character-counter .current');
    
    if (!textarea || !counter) return;
    
    const currentLength = textarea.value.length;
    const maxLength = 500;
    const percentage = (currentLength / maxLength) * 100;
    
    counter.textContent = currentLength;
    
    // 根據使用比例改變顏色
    if (percentage > 95) {
        counter.style.color = 'var(--danger-color)';
        counter.parentNode.classList.add('text-danger');
    } else if (percentage > 80) {
        counter.style.color = 'var(--warning-color)';
        counter.parentNode.classList.add('text-warning');
    } else {
        counter.style.color = 'var(--gray-500)';
        counter.parentNode.classList.remove('text-danger', 'text-warning');
    }
}

// 添加備用的執照驗證方法
function showLicenseVerificationDialog() {
    const doctorName = window.doctorData?.name || '醫師';
    const licenseNumber = window.doctorData?.licenseNumber || '執照號碼未填寫';
    
    showConfirmDialog({
        title: '執照驗證確認',
        message: `準備驗證 ${doctorName} 的獸醫師執照\n\n執照號碼：${licenseNumber.length > 4 ? licenseNumber.substring(0, 2) + '****' + licenseNumber.substring(licenseNumber.length - 2) : licenseNumber}\n\n確定要透過農委會 API 進行驗證嗎？`,
        confirmText: '開始驗證',
        confirmClass: 'btn-primary',
        onConfirm: () => {
            handleLicenseVerification();
        }
    });
}

// 修改初始化函數，提供更多驗證選項
function initializeLicenseManagement() {
    // 處理未驗證執照的驗證按鈕
    const verifyBtn = document.getElementById('verifyLicenseBtn');
    const updateLicenseBtn = document.getElementById('updateLicenseBtn');
    
    if (verifyBtn) {
        verifyBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 如果有執照號碼，直接驗證；否則顯示對話框
            if (window.doctorData?.licenseNumber) {
                handleLicenseVerification();
            } else {
                showInfoMessage('請先填寫執照號碼再進行驗證');
                switchTab('professional');
            }
        });
    }
    
    if (updateLicenseBtn) {
        updateLicenseBtn.addEventListener('click', handleLicenseUpdate);
    }
    
    // 檢查執照狀態
    checkLicenseStatus();
}

function checkLicenseStatus() {
    const doctorData = window.doctorData;
    if (doctorData && doctorData.isVerified) {
        // 已驗證的執照顯示為只讀模式
        showVerifiedLicenseStatus();
    }
}

function showVerifiedLicenseStatus() {
    const licenseSection = document.querySelector('.license-verification-card');
    if (!licenseSection) return;
    
    // 添加已驗證狀態
    const verifiedBadge = document.createElement('div');
    verifiedBadge.className = 'license-status-verified';
    verifiedBadge.innerHTML = `
        <i class="bi bi-shield-check-fill me-2"></i>
        <span>執照已通過農委會驗證</span>
        <small class="ms-2 text-muted">
            驗證時間: ${window.doctorData.verificationDate || '未知'}
        </small>
    `;
    
    const licenseInput = document.querySelector('[name="vet_license_number"]');
    if (licenseInput) {
        licenseInput.setAttribute('readonly', true);
        licenseInput.parentNode.appendChild(verifiedBadge);
    }
}

function handleLicenseVerification() {
    const licenseInput = document.querySelector('[name="vet_license_number"]');
    const verifyBtn = document.getElementById('verifyLicenseBtn');
    
    if (!licenseInput || !licenseInput.value.trim()) {
        showErrorMessage('請先填寫執照號碼');
        licenseInput?.focus();
        return;
    }
    
    const licenseNumber = licenseInput.value.trim();
    
    // 隱私保護：在日誌中不顯示完整執照號碼
    const maskedNumber = licenseNumber.length > 4 ? 
        licenseNumber.substring(0, 2) + '****' + licenseNumber.substring(licenseNumber.length - 2) : 
        '****';
    
    console.log(`🔍 開始驗證執照: ${maskedNumber}`);
    
    // 顯示載入狀態
    setButtonLoading(verifyBtn, true, '驗證中...');
    
    // 修正：發送請求到當前編輯頁面，而不是驗證頁面
    const formData = new FormData();
    formData.append('action', 'verify_license');
    formData.append('vet_license_number', licenseNumber);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    // 使用當前頁面URL而不是 /clinic/verify-license/
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',  // 標示為AJAX請求
            'Accept': 'application/json'
        }
    })
    .then(response => {
        // 檢查響應類型
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // 如果收到HTML，說明有錯誤
            throw new Error('伺服器返回了HTML而不是JSON，可能是URL錯誤或權限問題');
        }
    })
    .then(data => {
        if (data.success) {
            showSuccessMessage('🎉 執照驗證成功！頁面將重新載入以顯示最新狀態。');
            
            // 更新本地狀態（隱私保護）
            if (window.doctorData) {
                window.doctorData.isVerified = true;
                window.doctorData.verificationDate = new Date().toLocaleString();
                // 不在客戶端儲存完整執照號碼
            }
            
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showErrorMessage(`驗證失敗：${data.message || '未知錯誤'}`);
        }
    })
    .catch(error => {
        console.error('驗證請求失敗:', error);
        
        if (error.message.includes('HTML')) {
            showErrorMessage('系統配置錯誤，請聯繫管理員檢查執照驗證功能');
        } else {
            showErrorMessage('網路錯誤或系統暫時無法處理請求，請稍後再試');
        }
    })
    .finally(() => {
        setButtonLoading(verifyBtn, false, '立即驗證');
    });
}

function handleLicenseUpdate() {
    showConfirmDialog({
        title: '更新執照號碼',
        message: '更新執照號碼後需要重新驗證，確定要繼續嗎？',
        confirmText: '確定更新',
        confirmClass: 'btn-warning',
        onConfirm: () => {
            enableLicenseEditing();
        }
    });
}

function enableLicenseEditing() {
    const licenseContainer = document.querySelector('.license-number-protected');
    const hiddenInput = document.querySelector('input[name="vet_license_number"]');
    
    if (!licenseContainer) {
        showErrorMessage('找不到執照顯示區域');
        return;
    }
    
    // 創建可編輯的輸入框
    const editableInput = document.createElement('input');
    editableInput.type = 'text';
    editableInput.name = 'vet_license_number';
    editableInput.className = 'form-control';
    editableInput.value = window.doctorData?.licenseNumber || '';
    editableInput.placeholder = '請輸入完整執照號碼，例如：**府農**字第****號';
    
    const inputGroup = document.createElement('div');
    inputGroup.className = 'form-group-modern';
    inputGroup.innerHTML = `
        <label class="form-label-modern">
            <i class="bi bi-card-text me-1"></i>
            獸醫師執照號碼
            <span class="required-mark">*</span>
        </label>
        <div class="input-container"></div>
        <div class="form-help privacy-protected">更新後需要重新驗證（隱私保護）</div>
        <div class="invalid-feedback"></div>
    `;
    
    inputGroup.querySelector('.input-container').appendChild(editableInput);
    
    // 替換原本的顯示區域
    licenseContainer.parentNode.replaceChild(inputGroup, licenseContainer);
    
    // 移除隱藏的 input（如果有的話）
    if (hiddenInput) {
        hiddenInput.remove();
    }
    
    // 聚焦到新輸入框
    editableInput.focus();
    
    // 添加驗證事件
    editableInput.addEventListener('blur', () => validateField(editableInput));
    editableInput.addEventListener('input', () => {
        clearFieldError(editableInput);
        markFormChanged();
    });
    
    // 顯示重新驗證提示
    showInfoMessage('執照號碼已可編輯，修改後需重新驗證', 'info');
}

// ========== 安全操作功能 ==========
function initializeSecurityActions() {
    // 密碼重設
    const resetPasswordBtn = document.getElementById('resetPasswordBtn');
    if (resetPasswordBtn) {
        resetPasswordBtn.addEventListener('click', handlePasswordReset);
    }
    
    // 帳號啟用/停用
    const activateBtn = document.getElementById('activateAccountBtn');
    const deactivateBtn = document.getElementById('deactivateAccountBtn');
    
    if (activateBtn) {
        activateBtn.addEventListener('click', () => handleAccountToggle(true));
    }
    
    if (deactivateBtn) {
        deactivateBtn.addEventListener('click', () => handleAccountToggle(false));
    }
}

function handlePasswordReset() {
    const doctorName = window.doctorData?.name || '此醫師';
    const doctorEmail = window.doctorData?.email || '';
    
    showConfirmDialog({
        title: '發送密碼重設信件',
        message: `確定要發送密碼重設信件給「${doctorName}」嗎？\n信件將發送到：${doctorEmail}`,
        confirmText: '發送信件',
        confirmClass: 'btn-primary',
        onConfirm: executePasswordReset
    });
}

function executePasswordReset() {
    const resetBtn = document.getElementById('resetPasswordBtn');
    
    setButtonLoading(resetBtn, true, '發送中...');
    
    const formData = new FormData();
    formData.append('action', 'reset_password');
    formData.append('doctor_id', window.doctorData?.id);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('密碼重設信件已發送');
        } else {
            showErrorMessage(data.message || '發送失敗');
        }
    })
    .catch(error => {
        console.error('密碼重設失敗:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    })
    .finally(() => {
        setButtonLoading(resetBtn, false, '發送密碼重設信件');
    });
}

function handleAccountToggle(activate) {
    const doctorName = window.doctorData?.name || '此醫師';
    const action = activate ? '啟用' : '停用';
    
    showConfirmDialog({
        title: `${action}醫師帳號`,
        message: `確定要${action}「${doctorName}」的帳號嗎？\n\n${activate ? 
            '啟用後醫師可以正常登入和使用系統功能' : 
            '停用後醫師將無法登入，且不會出現在預約選項中'}`,
        confirmText: action,
        confirmClass: activate ? 'btn-success' : 'btn-warning',
        onConfirm: () => executeAccountToggle(activate)
    });
}

function executeAccountToggle(activate) {
    const doctorId = window.doctorData?.id;
    
    if (!doctorId) {
        showErrorMessage('無法獲取醫師資訊');
        return;
    }
    
    fetch(`/clinic/doctors/${doctorId}/toggle/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ activate })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message);
            
            // 更新頁面狀態
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(data.message || '操作失敗');
        }
    })
    .catch(error => {
        console.error('帳號狀態切換失敗:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    });
}

// ========== 表單提交 ==========
function initializeFormSubmission() {
    const form = document.getElementById('editDoctorForm');
    const saveBtn = document.getElementById('saveBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    
    if (form && saveBtn) {
        saveBtn.addEventListener('click', handleFormSubmission);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', handleCancel);
    }
    
    // 防止意外離開頁面
    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '您有未儲存的變更，確定要離開嗎？';
        }
    });
}

function handleFormSubmission(e) {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    // 驗證所有必填欄位
    if (!validateAllTabs()) {
        showErrorMessage('請檢查並修正表單中的錯誤');
        return;
    }
    
    isSubmitting = true;
    const saveBtn = document.getElementById('saveBtn');
    
    // 顯示載入狀態
    setButtonLoading(saveBtn, true, '儲存中...');
    
    // 收集表單資料
    const formData = new FormData(document.getElementById('editDoctorForm'));
    
    // 添加管理員權限（修正：允許同時是獸醫師和管理員）
    const adminCheckbox = document.getElementById('isClinicAdmin');
    if (adminCheckbox && adminCheckbox.checked) {
        formData.append('is_clinic_admin', 'on');
    }
    
    // 發送請求
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Accept': 'application/json, text/html',
        }
    })
    .then(response => {
        // 檢查響應類型
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            // JSON 響應
            return response.json();
        } else if (contentType && contentType.includes('text/html')) {
            // HTML 響應 - 可能是重定向或錯誤頁面
            if (response.ok) {
                // 成功但返回 HTML，可能是重定向
                showSuccessMessage('醫師資料已更新！頁面將重新載入...');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return { success: true };
            } else {
                // 錯誤頁面
                throw new Error(`伺服器返回錯誤: ${response.status} ${response.statusText}`);
            }
        } else {
            // 其他類型響應
            throw new Error('未知的響應格式');
        }
    })
    .then(data => {
        if (data && data.success) {
            showSuccessMessage('醫師資料已更新！');
            formChanged = false;
            updateSaveButtonState();
            showUnsavedIndicator(false);
            
            // 更新本地數據
            if (window.doctorData && data.updated_data) {
                Object.assign(window.doctorData, data.updated_data);
            }
        } else if (data && data.errors) {
            handleFormErrors(data.errors);
            showErrorMessage(data.message || '更新失敗，請檢查輸入資料');
        }
    })
    .catch(error => {
        console.error('提交錯誤:', error);
        
        if (error.message.includes('JSON')) {
            // JSON 解析錯誤，可能是後端返回了 HTML
            showErrorMessage('系統響應格式錯誤，請重新整理頁面後再試');
        } else {
            showErrorMessage('網路錯誤或系統暫時無法處理請求，請稍後再試');
        }
    })
    .finally(() => {
        isSubmitting = false;
        setButtonLoading(saveBtn, false, '儲存變更');
    });
}

function validateAllTabs() {
    const allInputs = document.querySelectorAll('#editDoctorForm input[required], #editDoctorForm textarea[required], #editDoctorForm select[required]');
    let isValid = true;
    let firstErrorTab = null;
    
    allInputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
            
            // 找到第一個錯誤所在的標籤頁
            if (!firstErrorTab) {
                const tabContent = input.closest('.tab-content-modern');
                if (tabContent) {
                    firstErrorTab = tabContent.dataset.content;
                }
            }
        }
    });
    
    // 如果有錯誤，切換到第一個錯誤的標籤頁
    if (!isValid && firstErrorTab && firstErrorTab !== currentTab) {
        switchTab(firstErrorTab);
    }
    
    return isValid;
}

function handleFormErrors(errors) {
    if (!errors) return;
    
    // 找到有錯誤的第一個標籤頁
    let errorTab = currentTab;
    
    for (const [fieldName, fieldErrors] of Object.entries(errors)) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            showFieldError(field, fieldErrors[0]);
            
            // 找到欄位所在的標籤頁
            const tabContent = field.closest('.tab-content-modern');
            if (tabContent) {
                errorTab = tabContent.dataset.content;
                break;
            }
        }
    }
    
    // 切換到錯誤標籤頁
    if (errorTab !== currentTab) {
        switchTab(errorTab);
    }
}

function handleCancel() {
    if (formChanged) {
        showConfirmDialog({
            title: '放棄變更',
            message: '您有未儲存的變更，確定要放棄嗎？',
            confirmText: '放棄',
            confirmClass: 'btn-danger',
            onConfirm: () => {
                window.location.href = '/clinic/doctors/';
            }
        });
    } else {
        window.location.href = '/clinic/doctors/';
    }
}


// ========== 工具函數 ==========

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPhone(phone) {
    const phoneRegex = /^09\d{8}$/;
    return phoneRegex.test(phone);
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
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

function setButtonLoading(button, isLoading, text) {
    if (!button) return;
    
    const spinner = button.querySelector('.loading-spinner-modern');
    const textSpan = button.querySelector('span');
    
    if (isLoading) {
        button.disabled = true;
        button.classList.add('loading');
        if (textSpan) textSpan.textContent = text;
        if (spinner) spinner.style.display = 'inline-block';
    } else {
        button.disabled = false;
        button.classList.remove('loading');
        if (textSpan) textSpan.textContent = text;
        if (spinner) spinner.style.display = 'none';
    }
}

function showConfirmDialog(options) {
    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog-overlay';
    dialog.innerHTML = `
        <div class="confirm-dialog">
            <h3>${options.title}</h3>
            <p style="white-space: pre-line;">${options.message}</p>
            <div class="dialog-buttons">
                <button class="btn-cancel">取消</button>
                <button class="btn-confirm ${options.confirmClass || 'btn-primary'}">${options.confirmText}</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    // 按鈕事件
    dialog.querySelector('.btn-cancel').addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
    
    dialog.querySelector('.btn-confirm').addEventListener('click', () => {
        options.onConfirm();
        document.body.removeChild(dialog);
    });
    
    // 點擊外部關閉
    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    });
    
    // 聚焦到確認按鈕
    setTimeout(() => {
        dialog.querySelector('.btn-confirm').focus();
    }, 100);
}

function showMessage(message, type, duration = 5000) {
    const messageEl = document.createElement('div');
    messageEl.className = `message-toast message-${type}`;
    
    // 檢查 message 是否包含 HTML
    const isHTML = /<[^>]*>/.test(message);
    
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 
                              type === 'warning' ? 'exclamation-triangle' : 
                              type === 'info' ? 'info-circle' :
                              'x-circle'}"></i>
            <div class="message-text">${isHTML ? message : `<span>${message}</span>`}</div>
        </div>
        <button class="message-close" aria-label="關閉">&times;</button>
    `;
    
    document.body.appendChild(messageEl);
    
    // 自動移除
    const autoRemove = setTimeout(() => {
        removeMessage(messageEl);
    }, duration);
    
    // 手動關閉
    messageEl.querySelector('.message-close').addEventListener('click', () => {
        clearTimeout(autoRemove);
        removeMessage(messageEl);
    });
    
    // 無障礙支援
    messageEl.setAttribute('role', 'alert');
    messageEl.setAttribute('aria-live', 'polite');
}

function removeMessage(messageEl) {
    if (messageEl.parentNode) {
        messageEl.classList.add('fade-out');
        setTimeout(() => {
            if (messageEl.parentNode) {
                document.body.removeChild(messageEl);
            }
        }, 300);
    }
}

function showSuccessMessage(message) {
    showMessage(message, 'success');
}

function showErrorMessage(message) {
    showMessage(message, 'error');
}

function showInfoMessage(message) {
    showMessage(message, 'info');
}

console.log('✅ 改良版編輯醫師 JavaScript 載入完成');