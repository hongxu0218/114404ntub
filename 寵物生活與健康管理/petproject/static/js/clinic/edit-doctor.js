// static/js/clinic/edit-doctor.js

// ========== 全域變數 ==========
let currentTab = 'basic';
let formChanged = false;
let autoSaveTimeout = null;
let isSubmitting = false;

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
    initializeLicenseVerification();
    initializeSecurityActions();
    initializeFormSubmission();
    
    // 設定初始狀態
    updateTabDisplay();
    
    console.log('✅ 編輯醫師表單初始化完成');
}

// ========== 標籤頁導航功能 ==========
function initializeTabNavigation() {
    const tabLinks = document.querySelectorAll('.nav-link-modern');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function() {
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
    
    // 添加切換動畫
    animateTabSwitch();
}

function updateTabDisplay() {
    // 更新導航標籤
    const tabLinks = document.querySelectorAll('.nav-link-modern');
    tabLinks.forEach(link => {
        const isActive = link.dataset.tab === currentTab;
        link.classList.toggle('active', isActive);
    });
    
    // 更新內容區域
    const tabContents = document.querySelectorAll('.tab-content-modern');
    tabContents.forEach(content => {
        const isActive = content.dataset.content === currentTab;
        content.classList.toggle('active', isActive);
    });
}

function animateTabSwitch() {
    const activeContent = document.querySelector('.tab-content-modern.active');
    if (activeContent) {
        activeContent.style.opacity = '0';
        activeContent.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            activeContent.style.opacity = '1';
            activeContent.style.transform = 'translateY(0)';
        }, 100);
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
        input.addEventListener('input', () => {
            clearFieldError(input);
            markFormChanged();
        });
    });
    
    // 特殊驗證處理
    const emailInput = document.querySelector('[name="email"]');
    if (emailInput) {
        emailInput.addEventListener('blur', validateEmailUniqueness);
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
    if (field.type === 'email' && value && !isValidEmail(value)) {
        showFieldError(field, '請輸入有效的電子郵件地址');
        return false;
    }
    
    if (field.name === 'phone_number' && value && !isValidPhone(value)) {
        showFieldError(field, '請輸入有效的台灣手機號碼（09xxxxxxxx）');
        return false;
    }
    
    if (field.name === 'years_of_experience' && value && (isNaN(value) || value < 0)) {
        showFieldError(field, '請輸入有效的年資數字');
        return false;
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
    
    // 模擬檢查信箱唯一性
    // 實際應用中應該發送 AJAX 請求到後端驗證
    setTimeout(() => {
        // 這裡可以添加實際的 API 檢查
        console.log('檢查信箱唯一性:', emailInput.value);
    }, 500);
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
    
    feedback.textContent = message;
    feedback.style.display = 'block';
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.style.display = 'none';
    }
}

// ========== 自動儲存功能 ==========
function initializeAutoSave() {
    const form = document.getElementById('editDoctorForm');
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', () => {
            markFormChanged();
            scheduleAutoSave();
        });
    });
}

function markFormChanged() {
    formChanged = true;
    updateSaveButtonState();
}

function scheduleAutoSave() {
    // 清除之前的自動儲存計時器
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    
    // 設定新的自動儲存計時器（3秒後執行）
    autoSaveTimeout = setTimeout(() => {
        if (formChanged && !isSubmitting) {
            performAutoSave();
        }
    }, 3000);
}

function performAutoSave() {
    console.log('🔄 執行自動儲存...');
    
    const formData = new FormData(document.getElementById('editDoctorForm'));
    formData.append('auto_save', 'true');
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken(),
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSaveStatus();
            formChanged = false;
            updateSaveButtonState();
        }
    })
    .catch(error => {
        console.error('自動儲存失敗:', error);
    });
}

function showSaveStatus() {
    const saveStatus = document.getElementById('saveStatus');
    if (saveStatus) {
        saveStatus.style.display = 'flex';
        
        setTimeout(() => {
            saveStatus.style.display = 'none';
        }, 3000);
    }
}

function updateSaveButtonState() {
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        if (formChanged) {
            saveBtn.classList.add('btn-warning-modern');
            saveBtn.classList.remove('btn-primary-modern');
            saveBtn.querySelector('span').textContent = '儲存變更';
        } else {
            saveBtn.classList.remove('btn-warning-modern');
            saveBtn.classList.add('btn-primary-modern');
            saveBtn.querySelector('span').textContent = '已儲存';
        }
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
    
    if (textarea && counter) {
        const currentLength = textarea.value.length;
        counter.textContent = currentLength;
        
        // 接近上限時改變顏色
        const maxLength = 500;
        const percentage = (currentLength / maxLength) * 100;
        
        if (percentage > 90) {
            counter.style.color = 'var(--danger-color)';
        } else if (percentage > 75) {
            counter.style.color = 'var(--warning-color)';
        } else {
            counter.style.color = 'var(--gray-500)';
        }
    }
}

// ========== 執照驗證功能 ==========
function initializeLicenseVerification() {
    const verifyBtn = document.getElementById('verifyLicenseBtn');
    
    if (verifyBtn) {
        verifyBtn.addEventListener('click', handleLicenseVerification);
    }
}

function handleLicenseVerification() {
    const licenseInput = document.querySelector('[name="vet_license_number"]');
    const verifyBtn = document.getElementById('verifyLicenseBtn');
    
    if (!licenseInput || !licenseInput.value.trim()) {
        showErrorMessage('請先填寫執照號碼');
        licenseInput.focus();
        return;
    }
    
    // 顯示載入狀態
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 驗證中...';
    
    // 發送驗證請求
    const formData = new FormData();
    formData.append('action', 'verify_license');
    formData.append('vet_license_number', licenseInput.value.trim());
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch('/clinic/verify-license/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('🎉 執照驗證成功！頁面將重新載入以顯示最新狀態。');
            
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showErrorMessage(`驗證失敗：${data.message}`);
            
            // 恢復按鈕狀態
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<i class="bi bi-shield-check"></i> 立即驗證';
        }
    })
    .catch(error => {
        console.error('驗證請求失敗:', error);
        showErrorMessage('網路錯誤，請稍後再試');
        
        // 恢復按鈕狀態
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = '<i class="bi bi-shield-check"></i> 立即驗證';
    });
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
        onConfirm: () => {
            executePasswordReset();
        }
    });
}

function executePasswordReset() {
    const resetBtn = document.getElementById('resetPasswordBtn');
    
    // 顯示載入狀態
    resetBtn.disabled = true;
    resetBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 發送中...';
    
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
        // 恢復按鈕狀態
        resetBtn.disabled = false;
        resetBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 發送密碼重設信件';
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
        onConfirm: () => {
            executeAccountToggle(activate);
        }
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
            e.returnValue = '';
        }
    });
}

function handleFormSubmission(e) {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    // 驗證當前標籤頁的必填欄位
    if (!validateCurrentTab()) {
        showErrorMessage('請檢查並修正表單中的錯誤');
        return;
    }
    
    isSubmitting = true;
    
    // 顯示載入狀態
    const saveBtn = document.getElementById('saveBtn');
    saveBtn.classList.add('loading');
    saveBtn.disabled = true;
    
    // 收集表單資料
    const formData = new FormData(document.getElementById('editDoctorForm'));
    
    // 添加管理員權限
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
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('醫師資料已更新！');
            formChanged = false;
            updateSaveButtonState();
        } else {
            handleFormErrors(data.errors);
            showErrorMessage(data.message || '更新失敗，請檢查輸入資料');
        }
    })
    .catch(error => {
        console.error('提交錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    })
    .finally(() => {
        isSubmitting = false;
        saveBtn.classList.remove('loading');
        saveBtn.disabled = false;
    });
}

function validateCurrentTab() {
    const currentContent = document.querySelector(`[data-content="${currentTab}"]`);
    if (!currentContent) return true;
    
    const requiredInputs = currentContent.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    
    requiredInputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
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
        currentTab = errorTab;
        updateTabDisplay();
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
}

function showMessage(message, type) {
    const messageEl = document.createElement('div');
    messageEl.className = `message-toast message-${type}`;
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 
                              type === 'warning' ? 'exclamation-triangle' : 
                              'x-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="message-close">&times;</button>
    `;
    
    document.body.appendChild(messageEl);
    
    // 自動移除
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

function showSuccessMessage(message) {
    showMessage(message, 'success');
}

function showErrorMessage(message) {
    showMessage(message, 'error');
}

function showFieldError(fieldName, message) {
    const field = document.querySelector(`[name="${fieldName}"]`);
    if (field) {
        showFieldError(field, message);
    }
}

// ========== 鍵盤快捷鍵 ==========
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S - 儲存
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn && !saveBtn.disabled) {
            saveBtn.click();
        }
    }
    
    // Ctrl/Cmd + 數字 - 切換標籤頁
    if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const tabs = ['basic', 'professional', 'permissions', 'security'];
        const targetTab = tabs[parseInt(e.key) - 1];
        if (targetTab) {
            switchTab(targetTab);
        }
    }
    
    // Escape - 取消/關閉對話框
    if (e.key === 'Escape') {
        const dialog = document.querySelector('.confirm-dialog-overlay');
        if (dialog) {
            document.body.removeChild(dialog);
        }
    }
});

console.log('✅ 編輯醫師 JavaScript 載入完成');