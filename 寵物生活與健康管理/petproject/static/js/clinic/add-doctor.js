// static/js/clinic/add-doctor.js - 完整版本

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
//     console.log('🚀 初始化新增醫師表單...');
    
    // 初始化各種功能
    initializeStepNavigation();
    initializeFormValidation();
    initializePasswordStrength();
    initializeCharacterCounter();
    initializePermissionHandlers();
    initializePreviewUpdates();
    initializeFormSubmission();
    initializeProfessionalInfoStatus();
    initializeHelpSystem();
    initializeEnhancedProgress();
    initializeSpecializationMultiSelect();
    
    // 設定初始狀態
    updateStepDisplay();
    updateProgressBar();
    updateNavigationButtons();
    updatePreviewData();
    
//     console.log('✅ 新增醫師表單初始化完成');
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
//     console.log(`🔄 嘗試從步驟 ${currentStep} 前進到下一步`);
    
    if (!validateCurrentStep()) {
//         console.log(`❌ 步驟 ${currentStep} 驗證失敗`);
        showStepValidationErrors();
        return;
    }
    
    if (currentStep < totalSteps) {
//         console.log(`✅ 步驟 ${currentStep} 驗證通過，前進到步驟 ${currentStep + 1}`);
        currentStep++;
        updateStepDisplay();
        updateProgressBar();
        updateNavigationButtons();
        updatePreviewData();
        animateStepTransition();
        
        // 滾動到頂部
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function handlePrevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepDisplay();
        updateProgressBar();
        updateNavigationButtons();
        animateStepTransition();
        
        // 滾動到頂部
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
    
    // 更新進度摘要
    const currentStepText = document.querySelector('.current-step');
    if (currentStepText) {
        currentStepText.textContent = `步驟 ${currentStep}`;
    }
    
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

// ========== 改善的表單驗證功能 ==========
function initializeFormValidation() {
    const form = document.getElementById('addDoctorForm');
    if (!form) return;
    
    // 即時驗證
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('blur', () => {
            validateField(input);
            updateProfessionalInfoStatus();
        });
        input.addEventListener('input', () => {
            clearFieldError(input);
            updateProfessionalInfoStatus();
        });
    });
}

function validateCurrentStep() {
//     console.log(`🔍 驗證步驟 ${currentStep}`);
    
    const currentSection = document.querySelector(`[data-section="${currentStep}"]`);
    if (!currentSection) return true;
    
    let isValid = true;
    
    // 清除之前的錯誤狀態
    clearSectionErrors(currentSection);
    
    // 根據步驟進行專門驗證
    switch (currentStep) {
        case 1:
            isValid = validateStep1();
            break;
        case 2:
            isValid = validateStep2();
            break;
        case 3:
            isValid = validateStep3();
            break;
        case 4:
            isValid = validateStep4();
            break;
    }
    
//     console.log(`${isValid ? '✅' : '❌'} 步驟 ${currentStep} 驗證結果: ${isValid}`);
    return isValid;
}

function validateStep1() {
//     console.log('🔍 驗證步驟 1: 基本資料');
    let isValid = true;
    
    // 驗證必填欄位
    const requiredFields = [
        { name: 'first_name', label: '姓名' },
        { name: 'username', label: '使用者名稱' },
        { name: 'email', label: '電子信箱' },
        { name: 'password', label: '密碼' }
    ];
    
    requiredFields.forEach(field => {
        const input = document.querySelector(`[name="${field.name}"]`);
        if (!input || !input.value.trim()) {
            showFieldError(input, `${field.label}為必填欄位`);
            isValid = false;
        }
    });
    
    // 驗證密碼強度
    const password = document.querySelector('[name="password"]');
    if (password && password.value) {
        if (password.value.length < 8) {
            showFieldError(password, '密碼長度至少需要8個字元');
            isValid = false;
        }
    }
    
    // 驗證信箱格式
    const email = document.querySelector('[name="email"]');
    if (email && email.value && !isValidEmail(email.value)) {
        showFieldError(email, '請輸入有效的電子郵件地址');
        isValid = false;
    }
    
    // 驗證電話格式（非必填）
    const phone = document.querySelector('[name="phone_number"]');
    if (phone && phone.value && !isValidPhone(phone.value)) {
        showFieldError(phone, '請輸入有效的台灣手機號碼（09xxxxxxxx）');
        isValid = false;
    }
    
    // 驗證使用者名稱格式
    const username = document.querySelector('[name="username"]');
    if (username && username.value && !isValidUsername(username.value)) {
        showFieldError(username, '使用者名稱只能包含英文、數字和底線，長度3-30字元');
        isValid = false;
    }
    
    return isValid;
}

function validateStep2() {
//     console.log('🔍 驗證步驟 2: 專業資訊');
    let isValid = true;
    
    // 執業年資驗證
    const experience = document.querySelector('[name="years_of_experience"]');
    if (experience && experience.value) {
        const years = parseInt(experience.value);
        if (isNaN(years) || years < 0 || years > 50) {
            showFieldError(experience, '執業年資應在0-50年之間');
            isValid = false;
        }
    }
    
    // 執照號碼格式驗證（如果有填寫）
    const license = document.querySelector('[name="vet_license_number"]');
    if (license && license.value.trim()) {
        if (!isValidLicenseNumber(license.value)) {
            showFieldError(license, '請輸入有效的獸醫師執照號碼格式');
            isValid = false;
        }
    }
    
    // 個人簡介長度驗證
    const bio = document.querySelector('[name="bio"]');
    if (bio && bio.value.length > 500) {
        showFieldError(bio, '個人簡介不能超過500字元');
        isValid = false;
    }
    
    // 如果沒有填寫任何專業資訊，顯示提示但不阻止進行
    const specialization = document.querySelector('[name="specialization"]');
    const hasAnyProfessionalInfo = 
        (specialization && specialization.value.trim()) ||
        (license && license.value.trim()) ||
        (bio && bio.value.trim()) ||
        (experience && experience.value && parseInt(experience.value) > 0);
    
    if (!hasAnyProfessionalInfo) {
        showMessage('建議填寫專業資訊以提升醫師檔案完整度', 'info');
    }
    
    return isValid;
}

function validateStep3() {
//     console.log('🔍 驗證步驟 3: 權限設定');
    
    // 權限設定都是可選的，但建議至少有一個身份
    const vetCheckbox = document.querySelector('[name="is_active_veterinarian"]');
    const adminCheckbox = document.querySelector('[name="is_clinic_admin"]');
    
    if ((!vetCheckbox || !vetCheckbox.checked) && (!adminCheckbox || !adminCheckbox.checked)) {
        showMessage('建議至少選擇一種身份（獸醫師或管理員）', 'info');
        // 這裡不返回 false，只是提醒
    }
    
    return true;
}

function validateStep4() {
//     console.log('🔍 驗證步驟 4: 確認建立');
    let isValid = true;
    
    // 驗證確認勾選
    const confirmInfo = document.getElementById('confirmInfo');
    const confirmEmail = document.getElementById('confirmEmail');
    
    if (!confirmInfo || !confirmInfo.checked) {
        showMessage('請確認醫師資訊正確無誤', 'error');
        isValid = false;
    }
    
    if (!confirmEmail || !confirmEmail.checked) {
        showMessage('請確認將發送歡迎信件', 'error');
        isValid = false;
    }
    
    return isValid;
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

function clearSectionErrors(section) {
    const errorFields = section.querySelectorAll('.is-invalid');
    errorFields.forEach(field => {
        clearFieldError(field);
    });
}

function showFieldError(field, message) {
    if (!field) return;
    
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = field.parentElement.querySelector('.invalid-feedback');
    }
    
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.textContent = message;
        feedback.style.display = 'block';
    } else {
        // 如果找不到 invalid-feedback，動態創建一個
        const newFeedback = document.createElement('div');
        newFeedback.className = 'invalid-feedback';
        newFeedback.textContent = message;
        newFeedback.style.display = 'block';
        field.parentElement.appendChild(newFeedback);
    }
}

function clearFieldError(field) {
    if (!field) return;
    
    field.classList.remove('is-invalid');
    
    // 如果有值且通過基本驗證，標記為有效
    if (field.value.trim()) {
        field.classList.add('is-valid');
    } else {
        field.classList.remove('is-valid');
    }
    
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = field.parentElement.querySelector('.invalid-feedback');
    }
    
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

// ========== 驗證所有步驟 ==========
function validateAllSteps() {
//     console.log('🔍 執行最終驗證...');
    
    for (let step = 1; step <= 4; step++) {
        const originalStep = currentStep;
        currentStep = step;
        
        if (!validateCurrentStep()) {
//             console.log(`❌ 步驟 ${step} 驗證失敗`);
            updateStepDisplay();
            updateProgressBar();
            updateNavigationButtons();
            return false;
        }
        
        currentStep = originalStep;
    }
    
//     console.log('✅ 所有步驟驗證通過');
    return true;
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
        // 初始更新
        updateCharacterCounter();
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

// ========== 專業資訊完整度狀態 ==========
function initializeProfessionalInfoStatus() {
    const professionalFields = ['specialization', 'bio', 'vet_license_number'];
    
    professionalFields.forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.addEventListener('input', updateProfessionalInfoStatus);
            field.addEventListener('blur', updateProfessionalInfoStatus);
        }
    });
    
    // 初始更新
    updateProfessionalInfoStatus();
}

function updateProfessionalInfoStatus() {
    const statusItems = document.querySelectorAll('.status-item');
    
    statusItems.forEach(item => {
        const fieldName = item.dataset.field;
        const field = document.querySelector(`[name="${fieldName}"]`);
        
        if (field && field.value.trim()) {
            item.classList.add('filled');
        } else {
            item.classList.remove('filled');
        }
    });
    
    // 計算完整度百分比
    const totalItems = statusItems.length;
    const filledItems = document.querySelectorAll('.status-item.filled').length;
    const completeness = Math.round((filledItems / totalItems) * 100);
    
    // 更新完整度顯示
    const summary = document.querySelector('.status-summary small');
    if (summary) {
        summary.textContent = `專業資訊完整度：${completeness}% (${filledItems}/${totalItems})`;
    }
}

// ========== 權限處理 ==========
function initializePermissionHandlers() {
    const adminCheckbox = document.getElementById('isClinicAdmin');
    const vetCheckbox = document.getElementById('isVeterinarian');
    const adminWarning = document.getElementById('adminWarning');
    
    if (adminCheckbox && adminWarning) {
        adminCheckbox.addEventListener('change', function() {
            adminWarning.style.display = this.checked ? 'block' : 'none';
            
            if (this.checked) {
                showMessage('注意：管理員權限將允許此醫師管理診所設定', 'warning');
            }
            
            // 更新預覽
            updatePermissionsPreview();
        });
    }
    
    if (vetCheckbox) {
        vetCheckbox.addEventListener('change', function() {
            // 更新預覽
            updatePermissionsPreview();
        });
    }
}

// ========== 預覽更新 ==========
function initializePreviewUpdates() {
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', updatePreviewData);
    });
    
    // 初始更新
    updatePreviewData();
}

function updatePreviewData() {
    // 更新預覽姓名
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
    updatePreviewSpecialization();
    
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
    
    // 檢查獸醫師身份
    const vetCheckbox = document.querySelector('[name="is_active_veterinarian"]');
    if (vetCheckbox && vetCheckbox.checked) {
        permissions.push('獸醫師');
    }
    
    // 檢查管理員權限
    const adminCheckbox = document.getElementById('isClinicAdmin');
    if (adminCheckbox && adminCheckbox.checked) {
        permissions.push('診所管理員');
    }
    
    // 顯示結果
    if (permissions.length > 0) {
        preview.textContent = permissions.join('、');
    } else {
        preview.textContent = '無特殊權限';
    }
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
    
    if (isSubmitting) {
//         console.log('⏳ 表單正在提交中，忽略重複提交');
        return;
    }
    
    // 最終驗證所有步驟
    if (!validateAllSteps()) {
//         console.log('❌ 表單驗證失敗');
        return;
    }
    
    isSubmitting = true;
    
    // 顯示載入狀態
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
        <i class="bi bi-hourglass-split"></i>
        <span>建立中...</span>
        <div class="loading-spinner-modern"></div>
    `;
    
    // 收集表單資料
    const formData = new FormData(document.getElementById('addDoctorForm'));
    
    // 確保正確的欄位名稱被包含
    const vetCheckbox = document.querySelector('[name="is_active_veterinarian"]');
    const adminCheckbox = document.querySelector('[name="is_clinic_admin"]');
    
    // 確保勾選框狀態正確傳送
    if (vetCheckbox && vetCheckbox.checked) {
        if (!formData.has('is_veterinarian')) {
            formData.append('is_veterinarian', 'on');
        }
    }
    
    if (adminCheckbox && adminCheckbox.checked) {
        if (!formData.has('is_clinic_admin')) {
            formData.append('is_clinic_admin', 'on');
        }
    }
    
//     console.log('📤 提交表單資料...');
    
    // 發送 AJAX 請求
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => {
//         console.log('📥 收到伺服器回應:', response.status);
        
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // HTML 回應處理
            return response.text().then(htmlText => {
                if (response.ok) {
                    return {
                        success: true,
                        message: '醫師建立成功！正在跳轉...',
                        redirect: response.url || '/clinic/doctors/'
                    };
                } else {
                    throw new Error(`伺服器回應錯誤 ${response.status}: ${response.statusText}`);
                }
            });
        }
    })
    .then(data => {
//         console.log('✅ 處理回應資料:', data);
        
        if (data.success) {
            showSuccessMessage(data.message || '醫師建立成功！');
            
            // 成功動畫效果
            submitBtn.innerHTML = `
                <i class="bi bi-check-circle-fill"></i>
                <span>建立成功</span>
            `;
            
            // 延遲跳轉
            setTimeout(() => {
                window.location.href = data.redirect || '/clinic/doctors/';
            }, 2000);
        } else {
//             console.log('❌ 表單驗證失敗:', data.errors);
            handleFormErrors(data.errors);
            showErrorMessage(data.message || '建立失敗，請檢查輸入資料');
        }
    })
    .catch(error => {
        console.error('💥 提交錯誤:', error);
        
        // 更詳細的錯誤處理
        let errorMessage = '系統錯誤，請稍後再試';
        
        if (error.message.includes('property') && error.message.includes('no setter')) {
            errorMessage = '表單欄位設定錯誤，請聯繫系統管理員';
        } else if (error.name === 'SyntaxError' && error.message.includes('JSON')) {
            errorMessage = '伺服器回應格式錯誤，請聯繫管理員';
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage = '網路連接失敗，請檢查網路連接';
        } else if (error.message.includes('timeout')) {
            errorMessage = '請求超時，請重試';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showErrorMessage(errorMessage);
    })
    .finally(() => {
        // 恢復按鈕狀態
        setTimeout(() => {
            isSubmitting = false;
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }, 1000);
    });
}

function handleFormErrors(errors) {
    if (!errors) return;
    
//     console.log('🚨 處理表單錯誤:', errors);
    
    // 找到有錯誤的最早步驟
    let errorStep = currentStep;
    const stepFieldMapping = {
        1: ['first_name', 'username', 'email', 'password', 'phone_number'],
        2: ['vet_license_number', 'specialization', 'years_of_experience', 'bio'],
        3: ['is_active_veterinarian', 'is_clinic_admin'], // 修正後的欄位名稱
        4: []
    };
    
    // 檢查每個步驟是否有錯誤
    for (let step = 1; step <= 4; step++) {
        const stepFields = stepFieldMapping[step];
        const hasErrorInStep = stepFields.some(fieldName => 
            errors.hasOwnProperty(fieldName)
        );
        
        if (hasErrorInStep) {
            errorStep = step;
            break;
        }
    }
    
    // 顯示所有欄位錯誤
    for (const [fieldName, fieldErrors] of Object.entries(errors)) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            const errorMessage = Array.isArray(fieldErrors) ? fieldErrors[0] : fieldErrors;
            showFieldError(field, errorMessage);
        } else {
            console.warn('找不到欄位:', fieldName);
        }
    }
    
    // 跳轉到錯誤步驟
    if (errorStep !== currentStep) {
//         console.log(`🔄 跳轉到步驟 ${errorStep} 處理錯誤`);
        currentStep = errorStep;
        updateStepDisplay();
        updateProgressBar();
        updateNavigationButtons();
        
        showMessage(`步驟 ${errorStep} 中有需要修正的欄位`, 'error');
    }
    
    // 滾動到第一個錯誤欄位
    setTimeout(() => {
        const firstError = document.querySelector('.is-invalid');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.focus();
        }
    }, 300);
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
    const usernameRegex = /^[a-zA-Z0-9_]{3,30}$/;
    return usernameRegex.test(username);
}

function isValidLicenseNumber(license) {
    // 基本的獸醫師執照號碼格式驗證
    return license.length >= 8 && /[\u4e00-\u9fff]/.test(license);
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showMessage(message, type) {
    // 移除現有的訊息
    const existingMessages = document.querySelectorAll('.message-toast');
    existingMessages.forEach(msg => msg.remove());
    
    const messageEl = document.createElement('div');
    messageEl.className = `message-toast message-${type}`;
    messageEl.innerHTML = `
        <div class="message-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 
                              type === 'warning' ? 'exclamation-triangle' : 
                              type === 'info' ? 'info-circle' :
                              'x-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="message-close">&times;</button>
    `;
    
    document.body.appendChild(messageEl);
    
    // 自動移除
    const autoRemoveTimeout = setTimeout(() => {
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
        clearTimeout(autoRemoveTimeout);
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

// ========== 幫助系統 ==========
function initializeHelpSystem() {
    const helpButton = document.getElementById('helpButton');
    const helpPanel = document.getElementById('helpPanel');
    const helpClose = document.getElementById('helpClose');
    const helpOverlay = document.querySelector('.help-overlay');
    const helpTabs = document.querySelectorAll('.help-tab');
    const helpTabContents = document.querySelectorAll('.help-tab-content');
    
    if (!helpButton || !helpPanel) return;
    
    // 開啟幫助面板
    helpButton.addEventListener('click', () => {
        helpPanel.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        // 動畫效果
        setTimeout(() => {
            helpPanel.classList.add('active');
        }, 10);
    });
    
    // 關閉幫助面板
    function closeHelpPanel() {
        helpPanel.classList.remove('active');
        document.body.style.overflow = '';
        
        setTimeout(() => {
            helpPanel.style.display = 'none';
        }, 300);
    }
    
    if (helpClose) {
        helpClose.addEventListener('click', closeHelpPanel);
    }
    
    if (helpOverlay) {
        helpOverlay.addEventListener('click', closeHelpPanel);
    }
    
    // ESC鍵關閉
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && helpPanel.style.display === 'block') {
            closeHelpPanel();
        }
    });
    
    // 標籤頁切換
    helpTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;
            
            // 更新標籤狀態
            helpTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 更新內容顯示
            helpTabContents.forEach(content => {
                content.classList.remove('active');
                if (content.dataset.content === targetTab) {
                    content.classList.add('active');
                }
            });
        });
    });
    
//     console.log('🔧 幫助系統初始化完成');
}

// ========== 增強進度指示器 ==========
function initializeEnhancedProgress() {
    // 為進度條添加動態效果
    updateProgressBar();
    
    // 添加步驟點擊跳轉功能（僅限已完成的步驟）
    const progressSteps = document.querySelectorAll('.progress-step');
    progressSteps.forEach((step, index) => {
        const stepNumber = index + 1;
        
        step.addEventListener('click', () => {
            if (stepNumber < currentStep) {
                // 允許返回已完成的步驟
                currentStep = stepNumber;
                updateStepDisplay();
                updateProgressBar();
                updateNavigationButtons();
                animateStepTransition();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
        
        // 添加hover效果
        step.addEventListener('mouseenter', () => {
            if (stepNumber < currentStep) {
                step.style.cursor = 'pointer';
                step.style.opacity = '0.8';
            }
        });
        
        step.addEventListener('mouseleave', () => {
            step.style.cursor = 'default';
            step.style.opacity = '1';
        });
    });
    
//     console.log('🔧 增強進度指示器初始化完成');
}

// ========== 步驟轉換動畫 ==========
function animateStepTransition() {
    const currentSection = document.querySelector('.form-section.active');
    
    if (currentSection) {
        // 淡出效果
        currentSection.style.opacity = '0';
        currentSection.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            // 顯示目標步驟
            const formSections = document.querySelectorAll('.form-section');
            formSections.forEach((section, index) => {
                section.classList.remove('active');
                if (index + 1 === currentStep) {
                    section.classList.add('active');
                    
                    // 淡入效果
                    section.style.opacity = '0';
                    section.style.transform = 'translateX(20px)';
                    
                    setTimeout(() => {
                        section.style.opacity = '1';
                        section.style.transform = 'translateX(0)';
                    }, 50);
                }
            });
        }, 150);
    }
}

// ========== 進度條更新增強 ==========
function updateProgressBar() {
    const progressFill = document.querySelector('.progress-fill');
    const progressPercentage = document.querySelector('.progress-percentage');
    
    if (progressFill && progressPercentage) {
        const percentage = Math.round((currentStep / totalSteps) * 100);
        
        // 動畫更新進度條
        progressFill.style.width = `${percentage}%`;
        progressPercentage.textContent = `${percentage}%`;
        
        // 添加顏色變化
        if (percentage === 100) {
            progressFill.style.background = 'linear-gradient(90deg, var(--success-color), var(--success-light))';
        } else {
            progressFill.style.background = 'linear-gradient(90deg, var(--primary-color), var(--primary-light))';
        }
    }
}

// ========== 多選專科領域功能 ==========
function initializeSpecializationMultiSelect() {
    const dropdown = document.getElementById('multi_select_dropdown');
    const display = document.getElementById('multi_select_display');
    
    if (!dropdown || !display) return;
    
    // 點擊外部關閉下拉選單
    document.addEventListener('click', function(e) {
        if (!display.contains(e.target) && !dropdown.contains(e.target)) {
            closeMultiSelectDropdown();
        }
    });
    
    // 初始化搜索功能
    const searchInput = document.getElementById('spec_search');
    if (searchInput) {
        searchInput.addEventListener('input', filterSpecializationOptions);
    }
    
    // 初始化其他專科輸入框
    const otherCheckbox = document.getElementById('other_checkbox');
    const otherInput = document.getElementById('specialization_other');
    
    if (otherCheckbox) {
        otherCheckbox.addEventListener('change', toggleOtherInput);
    }
    
    if (otherInput) {
        otherInput.addEventListener('input', updateSelectedSpecs);
        otherInput.addEventListener('click', (e) => e.stopPropagation());
    }
    
    // 初始化所有複選框
    const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedSpecs);
    });
    
//     console.log('🔧 多選專科領域初始化完成');
}

function toggleMultiSelectDropdown() {
    const dropdown = document.getElementById('multi_select_dropdown');
    const display = document.getElementById('multi_select_display');
    
    if (!dropdown || !display) return;
    
    const isOpen = dropdown.classList.contains('show');
    
    if (isOpen) {
        closeMultiSelectDropdown();
    } else {
        openMultiSelectDropdown();
    }
}

function openMultiSelectDropdown() {
    const dropdown = document.getElementById('multi_select_dropdown');
    const display = document.getElementById('multi_select_display');
    const searchInput = document.getElementById('spec_search');
    
    if (!dropdown || !display) return;
    
    dropdown.classList.add('show');
    display.classList.add('active');
    
    // 清空搜索並focus
    if (searchInput) {
        searchInput.value = '';
        setTimeout(() => searchInput.focus(), 100);
    }
    
    // 顯示所有選項
    filterSpecializationOptions();
}

function closeMultiSelectDropdown() {
    const dropdown = document.getElementById('multi_select_dropdown');
    const display = document.getElementById('multi_select_display');
    
    if (!dropdown || !display) return;
    
    dropdown.classList.remove('show');
    display.classList.remove('active');
}

function filterSpecializationOptions() {
    const searchInput = document.getElementById('spec_search');
    const options = document.querySelectorAll('#dropdown_options .option-item');
    
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    options.forEach(option => {
        const label = option.querySelector('span:last-child');
        const text = label ? label.textContent.toLowerCase() : '';
        
        if (text.includes(searchTerm) || searchTerm === '') {
            option.style.display = 'block';
        } else {
            option.style.display = 'none';
        }
    });
}

function updateSelectedSpecs() {
    const checkboxes = document.querySelectorAll('#dropdown_options input[type="checkbox"]:checked');
    const otherInput = document.getElementById('specialization_other');
    const selectedText = document.querySelector('.selected-text');
    const selectedTags = document.getElementById('selected_tags');
    const hiddenField = document.getElementById('specialization');
    
    if (!selectedText || !hiddenField) return;
    
    // 收集選中的專科
    const selectedSpecs = Array.from(checkboxes)
        .filter(cb => cb.id !== 'other_checkbox')
        .map(cb => cb.value);
    
    // 加入其他專科（如果有填寫）
    const otherSpec = otherInput ? otherInput.value.trim() : '';
    if (otherSpec) {
        selectedSpecs.push(otherSpec);
    }
    
    // 更新顯示文字
    if (selectedSpecs.length === 0) {
        selectedText.textContent = '請選擇專科領域';
        selectedText.classList.remove('has-selection');
        if (selectedTags) {
            selectedTags.style.display = 'none';
        }
    } else {
        const displayText = selectedSpecs.length === 1 
            ? selectedSpecs[0]
            : `已選擇 ${selectedSpecs.length} 個專科`;
        selectedText.textContent = displayText;
        selectedText.classList.add('has-selection');
        
        // 顯示標籤
        displaySelectedTags(selectedSpecs);
    }
    
    // 更新隱藏欄位
    hiddenField.value = selectedSpecs.join('、');
    
    // 更新專業資訊完整度
    updateProfessionalInfoStatus();
    
    // 更新預覽數據
    updatePreviewData();
}

function displaySelectedTags(selectedSpecs) {
    const selectedTags = document.getElementById('selected_tags');
    if (!selectedTags) return;
    
    if (selectedSpecs.length === 0) {
        selectedTags.style.display = 'none';
        return;
    }
    
    selectedTags.style.display = 'block';
    selectedTags.innerHTML = '';
    
    selectedSpecs.forEach((spec, index) => {
        const tag = document.createElement('div');
        tag.className = 'tag-item';
        tag.innerHTML = `
            <span>${spec}</span>
            <button type="button" class="tag-remove" onclick="removeSpecTag('${spec}', ${index >= selectedSpecs.length - 1 && document.getElementById('specialization_other')?.value.trim() === spec})">
                <i class="bi bi-x"></i>
            </button>
        `;
        selectedTags.appendChild(tag);
    });
}

function removeSpecTag(specName, isOther = false) {
    if (isOther) {
        // 清空其他專科輸入框並取消勾選其他checkbox
        const otherInput = document.getElementById('specialization_other');
        const otherInputSection = document.getElementById('other_input_section');
        const otherCheckbox = document.getElementById('other_checkbox');
        
        if (otherInput) otherInput.value = '';
        if (otherInputSection) otherInputSection.style.display = 'none';
        if (otherCheckbox) otherCheckbox.checked = false;
    } else {
        // 取消勾選對應的checkbox
        const checkboxes = document.querySelectorAll('#dropdown_options input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (checkbox.value === specName && checkbox.id !== 'other_checkbox') {
                checkbox.checked = false;
            }
        });
    }
    
    // 更新顯示
    updateSelectedSpecs();
}

function toggleOtherInput() {
    const otherCheckbox = document.getElementById('other_checkbox');
    const otherInputSection = document.getElementById('other_input_section');
    const otherInput = document.getElementById('specialization_other');
    
    if (!otherCheckbox || !otherInputSection || !otherInput) return;
    
    if (otherCheckbox.checked) {
        // 顯示輸入區域
        otherInputSection.style.display = 'block';
        setTimeout(() => otherInput.focus(), 100);
    } else {
        // 隱藏輸入區域並清空內容
        otherInputSection.style.display = 'none';
        otherInput.value = '';
    }
    
    // 更新選擇狀態
    updateSelectedSpecs();
}

// 更新專業資訊完整度狀態
function updateProfessionalInfoStatus() {
    const specializationField = document.getElementById('specialization');
    const statusItem = document.querySelector('.professional-info-status .status-item[data-field="specialization"]');
    const statusSummary = document.querySelector('.professional-info-status .status-summary');
    
    if (!specializationField || !statusItem) return;
    
    const hasSpecialization = specializationField.value.trim() !== '';
    
    if (hasSpecialization) {
        statusItem.classList.add('filled');
        statusItem.querySelector('.status-icon').classList.remove('bi-circle');
        statusItem.querySelector('.status-icon').classList.add('bi-check-circle-fill');
    } else {
        statusItem.classList.remove('filled');
        statusItem.querySelector('.status-icon').classList.remove('bi-check-circle-fill');
        statusItem.querySelector('.status-icon').classList.add('bi-circle');
    }
    
    // 更新完整度摘要
    if (statusSummary) {
        const filledItems = document.querySelectorAll('.professional-info-status .status-item.filled');
        const totalItems = document.querySelectorAll('.professional-info-status .status-item');
        const percentage = Math.round((filledItems.length / totalItems.length) * 100);
        
        statusSummary.innerHTML = `<small class="text-muted">專業資訊完整度：${percentage}% (${filledItems.length}/${totalItems.length})</small>`;
    }
}

// 在預覽數據更新函數中添加專科領域
function updatePreviewSpecialization() {
    const specializationField = document.getElementById('specialization');
    const previewSpecialization = document.getElementById('previewSpecialization');
    
    if (specializationField && previewSpecialization) {
        const value = specializationField.value.trim();
        previewSpecialization.textContent = value || '未填寫';
    }
}

// 全域函數導出
window.toggleMultiSelectDropdown = toggleMultiSelectDropdown;
window.filterSpecializationOptions = filterSpecializationOptions;
window.updateSelectedSpecs = updateSelectedSpecs;
window.removeSpecTag = removeSpecTag;
window.toggleOtherInput = toggleOtherInput;

// console.log('✅ 新增醫師 JavaScript 載入完成（包含多選專科領域）');