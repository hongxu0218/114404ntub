/* static/js/clinic-registration.js - 診所註冊功能（修正版） */

/**
 * 診所註冊模組
 */
window.ClinicRegistration = {
  
  // 配置選項
  config: {
    verificationTimeout: 120000,     // 120秒驗證超時
    progressUpdateInterval: 200,     // 進度條更新間隔
    passwordStrengthCheck: true,     // 是否檢查密碼強度
    realTimeValidation: true,        // 是否啟用即時驗證
    saveFormProgress: false          // 是否保存表單進度
  },

  // 內部狀態
  state: {
    isSubmitting: false,
    currentStep: 1,
    verificationTimer: null,
    progressTimer: null,
    modal: null,
    formData: {},
    validationRules: {},
    preventUnload: false  // 新增：控制頁面離開警告
  },

  // 表單欄位驗證規則
  validationRules: {
    clinic_name: {
      required: true,
      minLength: 2,
      maxLength: 100,
      pattern: /^[\u4e00-\u9fa5a-zA-Z0-9\s]+$/
    },
    license_number: {
      required: true,
      minLength: 8,
      maxLength: 50,
      pattern: /^[\u4e00-\u9fa5a-zA-Z0-9]+$/
    },
  clinic_phone: {
      required: true,
      pattern: /^(\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}$/
      // 支援格式：02-1234-5678, (02)1234-5678, 02 1234 5678, 0212345678 等
    },
    clinic_email: {
      required: true,
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    },
    admin_username: {
      required: true,
      minLength: 3,
      maxLength: 30,
      pattern: /^[a-zA-Z0-9_]+$/
    },
    admin_email: {
      required: true,
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    },
    admin_password: {
      required: true,
      minLength: 8,
      strength: true
    },
    admin_real_name: {
      required: true,
      minLength: 2,
      maxLength: 20,
      pattern: /^[\u4e00-\u9fa5a-zA-Z\s]+$/
    },
    admin_phone: {
      required: true,
      pattern: /^09[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{3}$|^09\d{8}$/
      // 支援格式：0912-345-678, 0912 345 678, 0912345678 等
    },
    clinic_mode: {
    required: true
    }
  },

  /**
   * 初始化模組
   */
  init: function() {
//     console.log('🏥 診所註冊模組啟動');
    
    if (!this.setupDOM()) {
      return;
    }
    
    this.setupEventListeners();
    this.setupFormValidation();
    this.setupPasswordToggle();
    this.setupModal();
    this.loadSavedProgress();
    
//     console.log('診所註冊模組初始化完成');
  },

  /**
   * 設定 DOM 元素
   */
  setupDOM: function() {
    this.elements = {
      form: document.getElementById('clinicRegistrationForm'),
      submitBtn: document.getElementById('submitBtn'),
      modal: document.getElementById('verificationModal'),
      progressBar: document.getElementById('verificationProgress'),
      togglePasswordBtn: document.getElementById('togglePassword'),
      passwordIcon: document.getElementById('passwordIcon'),
      confirmationCheck: document.querySelector('input[name="verification_confirmed"]'),
      
      // 表單欄位
      clinicName: document.querySelector('input[name="clinic_name"]'),
      licenseNumber: document.querySelector('input[name="license_number"]'),
      clinicPhone: document.querySelector('input[name="clinic_phone"]'),
      clinicEmail: document.querySelector('input[name="clinic_email"]'),
      clinicAddress: document.querySelector('input[name="clinic_address"]'),
      adminUsername: document.querySelector('input[name="admin_username"]'),
      adminEmail: document.querySelector('input[name="admin_email"]'),
      adminPassword: document.querySelector('input[name="admin_password"]'),
      adminPasswordConfirm: document.querySelector('input[name="admin_password_confirm"]'),
      adminRealName: document.querySelector('input[name="admin_real_name"]'),
      adminPhone: document.querySelector('input[name="admin_phone"]'),
      
      // Modal 元素
      verificationTitle: document.getElementById('verificationTitle'),
      verificationDescription: document.getElementById('verificationDescription'),
      verificationSteps: {
        step1: document.getElementById('step1'),
        step2: document.getElementById('step2'),
        step3: document.getElementById('step3')
      }
    };

    if (!this.elements.form) {
      console.warn('診所註冊表單未找到');
      return false;
    }

    return true;
  },

  /**
   * 設定事件監聽器
   */
  setupEventListeners: function() {
    // 表單提交事件
    this.elements.form.addEventListener('submit', (e) => {
      this.handleFormSubmit(e);
    });

    // 即時驗證事件
    if (this.config.realTimeValidation) {
      Object.keys(this.validationRules).forEach(fieldName => {
        const field = this.elements.form.querySelector(`[name="${fieldName}"]`);
        if (field) {
          field.addEventListener('blur', () => this.validateField(field));
          field.addEventListener('input', () => this.handleFieldInput(field));
        }
      });
    }

    // 密碼確認驗證
    if (this.elements.adminPasswordConfirm) {
      this.elements.adminPasswordConfirm.addEventListener('input', () => {
        this.validatePasswordConfirmation();
      });
    }

    // 確認checkbox事件
    if (this.elements.confirmationCheck) {
      this.elements.confirmationCheck.addEventListener('change', () => {
        this.updateSubmitButtonState();
      });
    }

    // 🔧 修正：頁面離開警告事件
    window.addEventListener('beforeunload', (e) => {
      if (this.state.isSubmitting && this.state.preventUnload) {
        e.preventDefault();
        e.returnValue = '註冊正在進行中，確定要離開嗎？';
        return '註冊正在進行中，確定要離開嗎？';
      }
    });
  },

  /**
   * 設定表單驗證
   */
  setupFormValidation: function() {
    // 設定HTML5驗證屬性
    Object.keys(this.validationRules).forEach(fieldName => {
      const field = this.elements.form.querySelector(`[name="${fieldName}"]`);
      const rules = this.validationRules[fieldName];
      
      if (field && rules) {
        if (rules.required) {
          field.setAttribute('required', '');
        }
        if (rules.minLength) {
          field.setAttribute('minlength', rules.minLength);
        }
        if (rules.maxLength) {
          field.setAttribute('maxlength', rules.maxLength);
        }
      }
    });

    // 自訂驗證訊息
    this.setupCustomValidationMessages();
  },

  /**
   * 設定密碼顯示切換
   */
  setupPasswordToggle: function() {
    if (!this.elements.togglePasswordBtn || !this.elements.adminPassword) {
      return;
    }

    this.elements.togglePasswordBtn.addEventListener('click', () => {
      const passwordField = this.elements.adminPassword;
      const icon = this.elements.passwordIcon;
      
      if (passwordField.type === 'password') {
        passwordField.type = 'text';
        icon.className = 'bi bi-eye-slash';
        this.elements.togglePasswordBtn.setAttribute('title', '隱藏密碼');
      } else {
        passwordField.type = 'password';
        icon.className = 'bi bi-eye';
        this.elements.togglePasswordBtn.setAttribute('title', '顯示密碼');
      }
    });
  },

  /**
   * 設定 Modal
   */
  setupModal: function() {
    if (!this.elements.modal) return;

    // 檢查 Bootstrap 是否可用
    if (typeof bootstrap !== 'undefined') {
      this.state.modal = new bootstrap.Modal(this.elements.modal, {
        backdrop: 'static',
        keyboard: false
      });
    } else {
      console.warn('Bootstrap 未載入，使用備用 Modal 顯示方式');
    }

    // Modal 關閉事件
    this.elements.modal.addEventListener('hidden.bs.modal', () => {
      if (this.state.isSubmitting) {
        this.cancelVerification();
      }
    });
  },

  /**
   * 處理表單提交
   */
  handleFormSubmit: async function(event) {
    event.preventDefault();

    if (this.state.isSubmitting) {
      console.warn('表單提交中，忽略重複請求');
      return;
    }

    // 全面驗證表單
    if (!this.validateForm()) {
      this.showFirstError();
      return;
    }

//     console.log('🚀 開始提交註冊表單');
    
    // 開始提交流程
    this.state.isSubmitting = true;
    this.state.preventUnload = true;  // 啟用頁面離開警告
    this.updateSubmitButtonState();
    
    // 顯示驗證 Modal
    this.showVerificationModal();
    
    // 🔧 修正：完整的進度動畫流程
    await this.runVerificationAnimation();
  },

  /**
   * 🆕 運行驗證動畫流程
   */
  runVerificationAnimation: async function() {
    try {
      // 步驟1：連接農委會API（2秒）
      this.updateVerificationStep(1, 'active');
      this.updateProgressBar(0);
      
      await this.animateProgressTo(30, 2000);
      this.updateVerificationStep(1, 'completed');
      
      // 步驟2：查詢診所資料（3秒）
      this.updateVerificationStep(2, 'active');
      await this.animateProgressTo(70, 3000);
      this.updateVerificationStep(2, 'completed');
      
      // 步驟3：驗證完成（2秒）
      this.updateVerificationStep(3, 'active');
      await this.animateProgressTo(100, 2000);
      this.updateVerificationStep(3, 'completed');
      
      // 🔧 顯示成功訊息
      this.updateModalContent(
        'success',
        '🎉 註冊成功！',
        '恭喜您！診所資料已通過農委會驗證，管理員帳號已建立完成。即將跳轉到成功頁面...'
      );
      
      // 等待2秒後提交表單
      await this.sleep(2000);
      
      // 🔧 關閉頁面離開警告
      this.state.preventUnload = false;
      
      // 🔧 直接提交表單到後端
//       console.log('🏁 動畫完成，提交表單到後端');
      this.elements.form.submit();
      
    } catch (error) {
      console.error('驗證動畫過程發生錯誤:', error);
      this.handleSubmissionError(error);
    }
  },

  /**
   * 🆕 動畫進度條到指定百分比
   */
  animateProgressTo: function(targetPercent, duration) {
    return new Promise((resolve) => {
      const startPercent = this.getCurrentProgress();
      const diff = targetPercent - startPercent;
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 使用緩動函數
        const easeProgress = this.easeInOutQuad(progress);
        const currentPercent = startPercent + (diff * easeProgress);
        
        this.updateProgressBar(currentPercent);
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          resolve();
        }
      };
      
      requestAnimationFrame(animate);
    });
  },

  /**
   * 🆕 緩動函數
   */
  easeInOutQuad: function(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  },

  /**
   * 🆕 取得目前進度百分比
   */
  getCurrentProgress: function() {
    if (!this.elements.progressBar) return 0;
    const currentWidth = this.elements.progressBar.style.width || '0%';
    return parseFloat(currentWidth.replace('%', ''));
  },

  /**
   * 驗證整個表單
   */
  validateForm: function() {
    let isValid = true;
    const errors = [];

    // 驗證所有欄位
    Object.keys(this.validationRules).forEach(fieldName => {
      const field = this.elements.form.querySelector(`[name="${fieldName}"]`);
      if (field && !this.validateField(field)) {
        isValid = false;
        errors.push(fieldName);
      }
    });

    // 特殊驗證：密碼確認
    if (!this.validatePasswordConfirmation()) {
      isValid = false;
      errors.push('admin_password_confirm');
    }

    // 驗證確認checkbox
    if (!this.elements.confirmationCheck?.checked) {
      isValid = false;
      this.setFieldError(this.elements.confirmationCheck, '請確認同意接受農委會驗證');
    }

//     console.log('表單驗證結果', { isValid, errors });
    return isValid;
  },

  /**
   * 驗證單個欄位
   */
  validateField: function(field) {
    if (!field) return true;

    const fieldName = field.name;
    const value = field.value.trim();
    const rules = this.validationRules[fieldName];
    
    if (!rules) return true;

    // 必填驗證
    if (rules.required && !value) {
      this.setFieldError(field, '此欄位為必填');
      return false;
    }

    if (!value) {
      this.clearFieldError(field);
      return true;
    }

    // 長度驗證
    if (rules.minLength && value.length < rules.minLength) {
      this.setFieldError(field, `至少需要 ${rules.minLength} 個字元`);
      return false;
    }

    if (rules.maxLength && value.length > rules.maxLength) {
      this.setFieldError(field, `不能超過 ${rules.maxLength} 個字元`);
      return false;
    }

    // 格式驗證
    if (rules.pattern && !rules.pattern.test(value)) {
      const errorMessage = this.getPatternErrorMessage(fieldName);
      this.setFieldError(field, errorMessage);
      return false;
    }

    // 密碼強度驗證
    if (fieldName === 'admin_password' && rules.strength) {
      const strengthResult = this.checkPasswordStrength(value);
      if (!strengthResult.isStrong) {
        this.setFieldError(field, strengthResult.message);
        return false;
      }
    }

    // 驗證通過
    this.clearFieldError(field);
    this.setFieldSuccess(field);
    return true;
  },

  /**
   * 🔧 設定欄位錯誤狀態
   */
  setFieldError: function(field, message) {
    if (!field) return;
    
    // 🚀 完全清理現有的驗證狀態
    this.clearAllValidationStates(field);
    
    // 🚀 設定錯誤狀態
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    // 🚀 建立新的錯誤訊息
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${message}`;
    feedback.setAttribute('data-validation-feedback', 'true');
    
    // 🚀 正確插入錯誤訊息
    this.insertFeedbackElement(field, feedback);
  },

  /**
   * 🔧 設定欄位成功狀態
   */
  setFieldSuccess: function(field) {
    if (!field) return;
    
    // 🚀 完全清理現有的驗證狀態
    this.clearAllValidationStates(field);
    
    // 🚀 設定成功狀態
    field.classList.add('is-valid');
    field.classList.remove('is-invalid');
    
    // 可選：不顯示成功訊息，只顯示綠色邊框
    // 如果要顯示成功訊息，取消下面的註解：
    /*
    const feedback = document.createElement('div');
    feedback.className = 'valid-feedback';
    feedback.innerHTML = `<i class="bi bi-check-circle me-1"></i>格式正確`;
    feedback.setAttribute('data-validation-feedback', 'true');
    this.insertFeedbackElement(field, feedback);
    */
  },

  /**
   * 取得格式驗證錯誤訊息
   */
  getPatternErrorMessage: function(fieldName) {
    const messages = {
      clinic_name: '診所名稱只能包含中文、英文、數字和空格',
      license_number: '執照字號格式不正確',
      clinic_phone: '請輸入有效的電話號碼',
      clinic_email: '請輸入有效的電子郵件地址',
      admin_username: '帳號只能包含英文、數字和底線',
      admin_email: '請輸入有效的電子郵件地址',
      admin_real_name: '姓名只能包含中文、英文和空格',
      admin_phone: '請輸入正確的手機號碼格式（09xxxxxxxx）'
    };
    
    return messages[fieldName] || '格式不正確';
  },

  /**
   * 檢查密碼強度
   */
  checkPasswordStrength: function(password) {
    if (password.length < 8) {
      return { isStrong: false, message: '密碼長度至少需要8個字元' };
    }

    let score = 0;
    const checks = {
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      symbols: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };

    score = Object.values(checks).filter(Boolean).length;

    if (score < 3) {
      return { 
        isStrong: false, 
        message: '密碼需要包含大小寫字母、數字或特殊符號至少3種類型' 
      };
    }

    return { isStrong: true, message: '密碼強度良好' };
  },

  /**
   * 驗證密碼確認
   */
  validatePasswordConfirmation: function() {
    const password = this.elements.adminPassword?.value;
    const confirmPassword = this.elements.adminPasswordConfirm?.value;
    const confirmField = this.elements.adminPasswordConfirm;
    
    if (!confirmField) return true;
    
    this.clearFieldError(confirmField);
    
    if (!confirmPassword) {
      return true; // 空值時不驗證
    }

    if (password !== confirmPassword) {
      this.setFieldError(confirmField, '密碼確認不符');
      return false;
    }

    this.setFieldSuccess(confirmField);
    return true;
  },

  /**
   * 處理欄位輸入
   */
  handleFieldInput: function(field) {
    // 清除錯誤狀態
    this.clearFieldError(field);
    
    // 特殊處理密碼確認欄位
    if (field.name === 'admin_password_confirm' || field.name === 'admin_password') {
      this.debounce(() => {
        this.validatePasswordConfirmation();
      }, 300)();
    }
    
    // 更新提交按鈕狀態
    this.debounce(() => {
      this.updateSubmitButtonState();
    }, 300)();
  },

  /**
   * 顯示第一個錯誤
   */
  showFirstError: function() {
    const firstErrorField = this.elements.form.querySelector('.is-invalid');
    if (firstErrorField) {
      firstErrorField.focus();
      firstErrorField.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });
    }
  },

  /**
   * 清除欄位錯誤
   */
  clearFieldError: function(field) {
    if (!field) return;
    
    // 特殊處理密碼確認欄位
    if (field.name === 'admin_password_confirm') {
      this.clearAllValidationStates(field);
      return;
    }
    
    // 一般欄位處理
    this.clearAllValidationStates(field);
  },


  /**
   * 更新提交按鈕狀態
   */
  updateSubmitButtonState: function() {
    if (!this.elements.submitBtn) return;

    const isFormValid = this.isFormBasicallyValid();
    const isConfirmed = this.elements.confirmationCheck?.checked;
    
    this.elements.submitBtn.disabled = this.state.isSubmitting || !isFormValid || !isConfirmed;
    
    if (this.state.isSubmitting) {
      this.elements.submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2"></span>
        驗證中...
      `;
    } else {
      this.elements.submitBtn.innerHTML = `
        <i class="bi bi-hospital-fill me-2"></i>
        開始註冊驗證
      `;
    }
  },

  /**
   * 檢查表單基本有效性
   */
  isFormBasicallyValid: function() {
    const requiredFields = [
      'clinic_name', 'license_number', 'clinic_phone', 'clinic_email', 'clinic_address',
      'admin_username', 'admin_email', 'admin_password', 'admin_password_confirm',
      'admin_real_name', 'admin_phone'
    ];
    
    return requiredFields.every(fieldName => {
      const field = this.elements.form.querySelector(`[name="${fieldName}"]`);
      return field && field.value.trim().length > 0;
    });
  },

  /**
   * 顯示驗證Modal
   */
  showVerificationModal: function() {
    if (this.state.modal) {
      this.resetModalContent();
      this.state.modal.show();
    } else {
      // 備用方案：直接顯示 Modal
      this.elements.modal.style.display = 'block';
      this.elements.modal.classList.add('show');
      document.body.classList.add('modal-open');
    }
  },

  /**
   * 隱藏驗證Modal
   */
  hideVerificationModal: function() {
    if (this.state.modal) {
      this.state.modal.hide();
    } else {
      // 備用方案：直接隱藏 Modal
      this.elements.modal.style.display = 'none';
      this.elements.modal.classList.remove('show');
      document.body.classList.remove('modal-open');
    }
  },

  /**
   * 重置Modal內容
   */
  resetModalContent: function() {
    if (this.elements.verificationTitle) {
      this.elements.verificationTitle.textContent = '正在進行農委會驗證...';
      this.elements.verificationTitle.className = 'mb-3';
    }
    
    if (this.elements.verificationDescription) {
      this.elements.verificationDescription.textContent = '系統正在向農委會資料庫查詢您的診所資訊，請稍候片刻';
    }
    
    // 重置步驟狀態
    Object.values(this.elements.verificationSteps).forEach(step => {
      if (step) {
        step.classList.remove('active', 'completed');
      }
    });
    
    // 重置進度條
    this.updateProgressBar(0);
  },

  /**
   * 更新Modal內容
   */
  updateModalContent: function(type, title, description) {
    if (this.elements.verificationTitle) {
      this.elements.verificationTitle.textContent = title;
      
      if (type === 'success') {
        this.elements.verificationTitle.className = 'mb-3 text-success';
      } else if (type === 'error') {
        this.elements.verificationTitle.className = 'mb-3 text-danger';
      }
    }
    
    if (this.elements.verificationDescription) {
      this.elements.verificationDescription.textContent = description;
    }
  },

  /**
   * 更新驗證步驟
   */
  updateVerificationStep: function(stepNumber, status) {
    const step = this.elements.verificationSteps[`step${stepNumber}`];
    if (step) {
      step.classList.remove('active', 'completed');
      if (status) {
        step.classList.add(status);
      }
    }
  },

  /**
   * 更新進度條
   */
  updateProgressBar: function(percentage) {
    if (this.elements.progressBar) {
      this.elements.progressBar.style.width = `${percentage}%`;
      this.elements.progressBar.setAttribute('aria-valuenow', percentage);
      
      if (percentage >= 100) {
        this.elements.progressBar.style.background = 
          'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
      }
    }
  },

  /**
   * 取消驗證
   */
  cancelVerification: function() {
//     console.log('取消診所註冊驗證');
    
    this.state.isSubmitting = false;
    this.state.preventUnload = false;  // 關閉頁面離開警告
    
    // 清理計時器
    if (this.state.verificationTimer) {
      clearTimeout(this.state.verificationTimer);
      this.state.verificationTimer = null;
    }
    
    this.hideVerificationModal();
    this.updateSubmitButtonState();
  },

  /**
   * 處理提交錯誤
   */
  handleSubmissionError: function(error) {
    console.error('註冊請求發生錯誤', error);
    
    this.state.isSubmitting = false;
    this.state.preventUnload = false;
    this.hideVerificationModal();
    
    let errorMessage = '註冊過程發生錯誤，請稍後重試';
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      errorMessage = '網路連線錯誤，請檢查網路設定後重試';
    } else if (error.message.includes('timeout')) {
      errorMessage = '請求超時，請稍後重試';
    }
    
    alert(errorMessage);  // 簡單的錯誤提示
    this.updateSubmitButtonState();
  },

  /**
   * 保存表單進度
   */
  saveFormProgress: function() {
    // 簡化版本，暫時不實作
  },

  /**
   * 載入保存的進度
   */
  loadSavedProgress: function() {
    // 簡化版本，暫時不實作
  },

  /**
   * 防抖函數
   */
  debounce: function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * 睡眠函數
   */
  sleep: function(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  /**
   * 設定自訂驗證訊息
   */
  setupCustomValidationMessages: function() {
    this.elements.form.querySelectorAll('input').forEach(input => {
      input.addEventListener('invalid', (e) => {
        e.preventDefault();
        const fieldName = input.name;
        const errorMessage = this.getPatternErrorMessage(fieldName);
        this.setFieldError(input, errorMessage);
      });
    });
  },

  /**
   * 清理資源
   */
  cleanup: function() {
    this.cancelVerification();
//     console.log('診所註冊模組資源已清理');
  },


  
  clearAllValidationStates: function(field) {
    if (!field) return;
    
    // 移除所有驗證 class
    field.classList.remove('is-valid', 'is-invalid');
    
    // 找到所有相關的 feedback 元素並移除
    const container = this.getFieldContainer(field);
    const existingFeedbacks = container.querySelectorAll('[data-validation-feedback="true"]');
    existingFeedbacks.forEach(feedback => feedback.remove());
    
    // 也移除沒有標記的舊 feedback（向後兼容）
    const oldFeedbacks = container.querySelectorAll('.valid-feedback, .invalid-feedback');
    oldFeedbacks.forEach(feedback => feedback.remove());
  },

 
  getFieldContainer: function(field) {
    // 如果是在 input-group 中，返回 input-group 的父容器
    const inputGroup = field.closest('.input-group');
    if (inputGroup) {
      return inputGroup.parentNode;
    }
    
    // 否則返回欄位的直接父容器
    return field.parentNode;
  },

 
  insertFeedbackElement: function(field, feedback) {
    const container = this.getFieldContainer(field);
    container.appendChild(feedback);
  },


};



// 頁面載入完成後自動初始化
document.addEventListener('DOMContentLoaded', function() {
  window.ClinicRegistration.init();
});

// 頁面卸載時清理資源
window.addEventListener('beforeunload', function() {
  window.ClinicRegistration.cleanup();
});

// 全局別名
window.ClinicReg = window.ClinicRegistration;