// static/js/clinic/add-doctor.js

// ========== 全域變數 ==========
let currentStep = 1;
const totalSteps = 4;
let formData = {};
let isSubmitting = false;

// ========== DOM 載入完成後初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeAddDoctorForm();
});

// ========== 主要初始化函數 ==========
function initializeAddDoctorForm() {
    console.log('🚀 初始化新增醫師表單...');
    
    // 初始化各種功能
    initializeStepNavigation();
    initializeFormValidation();
    initializePasswordStrength();
    initializeCharacterCounter();
    initializePermissionHandlers();
    initializePreviewUpdates();
    initializeFormSubmission();
    
    // 設定初始狀態
    updateStepDisplay();
    updateProgressBar();
    
    console.log('✅ 新增醫師表單初始化完成');
}

// ========== 步驟導航功能 ==========
function initializeStepNavigation() {
    const nextBtn = document.getElementById('nextBtn');
    const prevBtn = document.getElementById('prevBtn');
    
    if (nextBtn) {
        nextBtn.addEventListener('click', handleNextStep);
    }
    
    if (prevBtn) {
        prevBtn.addEventListener('click', handlePrevStep);
    }
}

function handleNextStep() {
    if (validateCurrentStep()) {
        if (currentStep < totalSteps) {
            currentStep++;
            updateStepDisplay();
            updateProgressBar();
            updateNavigationButtons();
            updatePreviewData();
            
            // 添加步驟完成動畫
            animateStepTransition();
        }
    } else {
        // 顯示驗證錯誤
        showStepValidationErrors();
    }
}

function handlePrevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepDisplay();
        updateProgressBar();
        updateNavigationButtons();
        
        animateStepTransition();
    }
}

function updateStepDisplay() {
    // 更新步驟指示器
    const progressSteps = document.querySelectorAll('.progress-step');
    progressSteps.forEach((step, index) => {
        const stepNumber = index + 1;
        
        step.classList.remove('active', 'completed');
        
        if (stepNumber === currentStep) {
            step.classList.add('active');
        } else if (stepNumber < currentStep) {
            step.classList.add('completed');
        }
    });
    
    // 更新表單區域顯示
    const formSections = document.querySelectorAll('.form-section');
    formSections.forEach((section, index) => {
        const sectionNumber = index + 1;
        section.classList.toggle('active', sectionNumber === currentStep);
    });
}

function updateProgressBar() {
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
        const percentage = (currentStep / totalSteps) * 100;
        progressFill.style.width = `${percentage}%`;
    }
}

function updateNavigationButtons() {
    const nextBtn = document.getElementById('nextBtn');
    const prevBtn = document.getElementById('prevBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    // 上一步按鈕
    if (prevBtn) {
        prevBtn.style.display = currentStep > 1 ? 'flex' : 'none';
    }
    
    // 下一步/提交按鈕
    if (currentStep === totalSteps) {
        if (nextBtn) nextBtn.style.display = 'none';
        if (submitBtn) submitBtn.style.display = 'flex';
    } else {
        if (nextBtn) nextBtn.style.display = 'flex';
        if (submitBtn) submitBtn.style.display = 'none';
    }
}

function animateStepTransition() {
    const activeSection = document.querySelector('.form-section.active');
    if (activeSection) {
        activeSection.style.opacity = '0';
        activeSection.style.transform = 'translateX(20px)';
        
        setTimeout(() => {
            activeSection.style.opacity = '1';
            activeSection.style.transform = 'translateX(0)';
        }, 100);
    }
}

// ========== 表單驗證功能 ==========
function initializeFormValidation() {
    const form = document.getElementById('addDoctorForm');
    if (!form) return;
    
    // 即時驗證
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('blur', () => validateField(input));
        input.addEventListener('input', () => clearFieldError(input));
    });
}

function validateCurrentStep() {
    const currentSection = document.querySelector(`[data-section="${currentStep}"]`);
    if (!currentSection) return true;
    
    const inputs = currentSection.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
    // 特殊驗證規則
    if (currentStep === 1) {
        isValid = validateStep1() && isValid;
    } else if (currentStep === 4) {
        isValid = validateStep4() && isValid;
    }
    
    return isValid;
}

function validateStep1() {
    // 驗證密碼
    const password = document.querySelector('[name="password"]');
    const confirmPassword = document.querySelector('[name="password_confirm"]');
    
    if (password && password.value.length < 8) {
        showFieldError(password, '密碼長度至少需要8個字元');
        return false;
    }
    
    // 驗證信箱格式
    const email = document.querySelector('[name="email"]');
    if (email && !isValidEmail(email.value)) {
        showFieldError(email, '請輸入有效的電子郵件地址');
        return false;
    }
    
    // 驗證電話格式
    const phone = document.querySelector('[name="phone_number"]');
    if (phone && phone.value && !isValidPhone(phone.value)) {
        showFieldError(phone, '請輸入有效的台灣手機號碼');
        return false;
    }
    
    return true;
}

function validateStep4() {
    // 驗證確認勾選
    const confirmInfo = document.getElementById('confirmInfo');
    const confirmEmail = document.getElementById('confirmEmail');
    
    if (!confirmInfo || !confirmInfo.checked) {
        showMessage('請確認醫師資訊正確無誤', 'error');
        return false;
    }
    
    if (!confirmEmail || !confirmEmail.checked) {
        showMessage('請確認將發送歡迎信件', 'error');
        return false;
    }
    
    return true;
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
    
    if (field.name === 'username' && value && !isValidUsername(value)) {
        showFieldError(field, '使用者名稱只能包含英文、數字和底線');
        return false;
    }
    
    // 通過驗證
    clearFieldError(field);
    return true;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    const feedback = field.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.textContent = message;
        feedback.style.display = 'block';
    }
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    
    const feedback = field.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.style.display = 'none';
    }
}

function showStepValidationErrors() {
    showMessage('請檢查並修正表單中的錯誤', 'error');
    
    // 滾動到第一個錯誤欄位
    const firstError = document.querySelector('.is-invalid');
    if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstError.focus();
    }
}

// ========== 密碼強度檢測 ==========
function initializePasswordStrength() {
    const passwordInput = document.querySelector('[name="password"]');
    const toggleBtn = document.getElementById('togglePassword1');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', updatePasswordStrength);
    }
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', togglePasswordVisibility);
    }
}

function updatePasswordStrength() {
    const password = document.querySelector('[name="password"]').value;
    const strengthFill = document.querySelector('.strength-fill');
    const strengthText = document.querySelector('.strength-text span');
    
    if (!strengthFill || !strengthText) return;
    
    const strength = calculatePasswordStrength(password);
    
    // 更新強度條
    strengthFill.className = 'strength-fill';
    strengthFill.classList.add(strength.level);
    
    // 更新文字
    strengthText.textContent = strength.text;
    strengthText.style.color = strength.color;
}

function calculatePasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    
    if (score < 2) {
        return { level: 'weak', text: '弱', color: 'var(--danger-color)' };
    } else if (score < 4) {
        return { level: 'fair', text: '普通', color: 'var(--warning-color)' };
    } else if (score < 6) {
        return { level: 'good', text: '良好', color: 'var(--info-color)' };
    } else {
        return { level: 'strong', text: '強', color: 'var(--success-color)' };
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.querySelector('[name="password"]');
    const toggleBtn = document.getElementById('togglePassword1');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleBtn.innerHTML = '<i class="bi bi-eye-slash"></i>';
    } else {
        passwordInput.type = 'password';
        toggleBtn.innerHTML = '<i class="bi bi-eye"></i>';
    }
}

// ========== 字元計數器 ==========
function initializeCharacterCounter() {
    const bioTextarea = document.querySelector('[name="bio"]');
    
    if (bioTextarea) {
        bioTextarea.addEventListener('input', updateCharacterCounter);
    }
}

function updateCharacterCounter() {
    const textarea = document.querySelector('[name="bio"]');
    const counter = document.querySelector('.character-counter .current');
    
    if (textarea && counter) {
        counter.textContent = textarea.value.length;
        
        // 接近上限時改變顏色
        const maxLength = 500;
        const currentLength = textarea.value.length;
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

// ========== 權限處理 ==========
function initializePermissionHandlers() {
    const adminCheckbox = document.getElementById('isClinicAdmin');
    const adminWarning = document.getElementById('adminWarning');
    
    if (adminCheckbox && adminWarning) {
        adminCheckbox.addEventListener('change', function() {
            adminWarning.style.display = this.checked ? 'block' : 'none';
            
            if (this.checked) {
                showMessage('注意：管理員權限將允許此醫師管理診所設定', 'warning');
            }
        });
    }
}

// ========== 預覽更新 ==========
function initializePreviewUpdates() {
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', updatePreviewData);
    });
}

function updatePreviewData() {
    // 更新預覽名稱
    const nameInput = document.querySelector('[name="first_name"]');
    const previewName = document.getElementById('previewName');
    if (nameInput && previewName) {
        previewName.textContent = nameInput.value ? `Dr. ${nameInput.value}` : 'Dr. --';
    }
    
    // 更新預覽信箱
    const emailInput = document.querySelector('[name="email"]');
    const previewEmail = document.getElementById('previewEmail');
    if (emailInput && previewEmail) {
        previewEmail.textContent = emailInput.value || '--';
    }
    
    // 更新預覽專科
    const specializationInput = document.querySelector('[name="specialization"]');
    const previewSpecialization = document.getElementById('previewSpecialization');
    if (specializationInput && previewSpecialization) {
        previewSpecialization.textContent = specializationInput.value || '--';
    }
    
    // 更新其他預覽欄位
    updateDetailPreview('username', 'previewUsername');
    updateDetailPreview('phone_number', 'previewPhone');
    updateDetailPreview('vet_license_number', 'previewLicense');
    updateDetailPreview('years_of_experience', 'previewExperience', ' 年');
    
    // 更新權限預覽
    updatePermissionsPreview();
}

function updateDetailPreview(inputName, previewId, suffix = '') {
    const input = document.querySelector(`[name="${inputName}"]`);
    const preview = document.getElementById(previewId);
    
    if (input && preview) {
        preview.textContent = input.value ? `${input.value}${suffix}` : '--';
    }
}

function updatePermissionsPreview() {
    const preview = document.getElementById('previewPermissions');
    if (!preview) return;
    
    const permissions = [];
    
    const appointmentPerm = document.querySelector('[name="can_manage_appointments"]');
    if (appointmentPerm && appointmentPerm.checked) {
        permissions.push('預約管理');
    }
    
    const adminPerm = document.getElementById('isClinicAdmin');
    if (adminPerm && adminPerm.checked) {
        permissions.push('診所管理員');
    }
    
    preview.textContent = permissions.length > 0 ? permissions.join('、') : '一般醫師';
}

// ========== 表單提交 ==========
function initializeFormSubmission() {
    const form = document.getElementById('addDoctorForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (form && submitBtn) {
        submitBtn.addEventListener('click', handleFormSubmission);
    }
}

function handleFormSubmission(e) {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    if (!validateCurrentStep()) {
        showStepValidationErrors();
        return;
    }
    
    isSubmitting = true;
    
    // 顯示載入狀態
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;
    
    // 收集表單資料
    const formData = new FormData(document.getElementById('addDoctorForm'));
    
    // 添加管理員權限到表單資料
    const adminCheckbox = document.getElementById('isClinicAdmin');
    if (adminCheckbox && adminCheckbox.checked) {
        formData.append('is_clinic_admin', 'on');
    }
    
    // 發送 AJAX 請求
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
            showSuccessMessage('醫師建立成功！正在跳轉...');
            
            // 延遲跳轉以顯示成功訊息
            setTimeout(() => {
                window.location.href = data.redirect || '/clinic/doctors/';
            }, 1500);
        } else {
            handleFormErrors(data.errors);
            showErrorMessage(data.message || '建立失敗，請檢查輸入資料');
        }
    })
    .catch(error => {
        console.error('提交錯誤:', error);
        showErrorMessage('網路錯誤，請稍後再試');
    })
    .finally(() => {
        isSubmitting = false;
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    });
}

function handleFormErrors(errors) {
    if (!errors) return;
    
    // 回到有錯誤的步驟
    let errorStep = 1;
    
    for (const [fieldName, fieldErrors] of Object.entries(errors)) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            showFieldError(field, fieldErrors[0]);
            
            // 判斷錯誤所在步驟
            const section = field.closest('.form-section');
            if (section) {
                const sectionNumber = parseInt(section.dataset.section);
                if (sectionNumber < errorStep || errorStep === 1) {
                    errorStep = sectionNumber;
                }
            }
        }
    }
    
    // 跳轉到錯誤步驟
    if (errorStep !== currentStep) {
        currentStep = errorStep;
        updateStepDisplay();
        updateProgressBar();
        updateNavigationButtons();
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

function isValidUsername(username) {
    const usernameRegex = /^[a-zA-Z0-9_]+$/;
    return usernameRegex.test(username);
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showMessage(message, type) {
    // 重用之前的訊息顯示函數
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
    // Enter 鍵 - 下一步
    if (e.key === 'Enter' && !e.shiftKey && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        if (currentStep < totalSteps) {
            handleNextStep();
        } else {
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn && submitBtn.style.display !== 'none') {
                submitBtn.click();
            }
        }
    }
    
    // Ctrl/Cmd + Enter - 直接提交
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (currentStep === totalSteps) {
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.click();
            }
        }
    }
});

console.log('✅ 新增醫師 JavaScript 載入完成');