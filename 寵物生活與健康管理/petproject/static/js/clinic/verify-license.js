
/**
 * 獸醫師執照驗證模組
 */
window.VetLicenseVerification = {
  
  // 配置選項
  config: {
    verificationTimeout: 60000,    // 60秒驗證超時
    progressUpdateInterval: 100,   // 進度條更新間隔
    licenseNumberMaxLength: 50,    // 執照號碼最大長度
    retryAttempts: 3              // 重試次數
  },

  // 內部狀態
  state: {
    isVerifying: false,
    currentAttempt: 0,
    verificationTimer: null,
    progressTimer: null,
    modal: null
  },

  // 執照號碼格式模式
  licensePatterns: [
    /^\d{2,3}府農畜字第\d+號$/,                    // 94府農畜字第13273號
    /^\d{3}農牧字第\d+號$/,                        // 103農牧字第1031473829號
    /^\d{2,3}[縣市]府農畜字第\d+號$/,              // 含縣市的格式
    /^[A-Z]{2,4}\d{8,12}$/,                        // 英文字母+數字格式
    /^\d{8,15}$/                                   // 純數字格式
  ],

  /**
   * 初始化模組
   */
  init: function() {
//     console.log('🏥 獸醫師執照驗證模組啟動');
    
    this.setupDOM();
    this.setupEventListeners();
    this.setupValidation();
    this.setupModal();
    
    PD.debug.log('執照驗證模組初始化完成');
  },

  /**
   * 設定 DOM 元素
   */
  setupDOM: function() {
    this.elements = {
      form: document.getElementById('licenseVerificationForm'),
      licenseInput: document.querySelector('input[name="vet_license_number"]'),
      submitBtn: document.getElementById('submitBtn'),
      modal: document.getElementById('verificationModal'),
      progressBar: document.querySelector('.progress-bar')
    };

    // 檢查必要元素
    if (!this.elements.form || !this.elements.licenseInput) {
      PD.debug.warn('執照驗證表單元素未找到');
      return false;
    }

    return true;
  },

  /**
   * 設定事件監聽器
   */
  setupEventListeners: function() {
    if (!this.elements.form) return;

    // 表單提交事件
    this.elements.form.addEventListener('submit', (e) => {
      this.handleFormSubmit(e);
    });

    // 執照號碼輸入事件
    if (this.elements.licenseInput) {
      this.elements.licenseInput.addEventListener('input', (e) => {
        this.handleLicenseInput(e);
      });

      this.elements.licenseInput.addEventListener('blur', (e) => {
        this.validateLicenseNumber(e.target.value);
      });

      this.elements.licenseInput.addEventListener('paste', (e) => {
        setTimeout(() => {
          this.formatLicenseNumber(e.target);
        }, 10);
      });
    }

    // 提交按鈕點擊事件
    if (this.elements.submitBtn) {
      this.elements.submitBtn.addEventListener('click', (e) => {
        if (this.state.isVerifying) {
          e.preventDefault();
          this.showMessage('驗證進行中，請稍候...', 'warning');
        }
      });
    }

    // 鍵盤快捷鍵
    document.addEventListener('keydown', (e) => {
      // Ctrl+Enter 快速提交
      if (e.ctrlKey && e.key === 'Enter' && !this.state.isVerifying) {
        this.elements.form?.requestSubmit();
      }
      
      // Escape 關閉 Modal
      if (e.key === 'Escape' && this.state.isVerifying) {
        this.cancelVerification();
      }
    });
  },

  /**
   * 設定表單驗證
   */
  setupValidation: function() {
    if (!this.elements.licenseInput) return;

    // 設定表單屬性
    this.elements.licenseInput.setAttribute('maxlength', this.config.licenseNumberMaxLength);
    this.elements.licenseInput.setAttribute('autocomplete', 'off');
    this.elements.licenseInput.setAttribute('spellcheck', 'false');
  },

  /**
   * 設定 Modal
   */
  setupModal: function() {
    if (!this.elements.modal) return;

    this.state.modal = new bootstrap.Modal(this.elements.modal, {
      backdrop: 'static',
      keyboard: false
    });

    // Modal 事件監聽
    this.elements.modal.addEventListener('hidden.bs.modal', () => {
      if (this.state.isVerifying) {
        this.cancelVerification();
      }
    });
  },

  /**
   * 處理表單提交
   */
  handleFormSubmit: async function(event) {
    event.preventDefault();

    if (this.state.isVerifying) {
      PD.debug.warn('驗證進行中，忽略重複提交');
      return;
    }

    const formData = new FormData(this.elements.form);
    const licenseNumber = formData.get('vet_license_number')?.trim();

    // 前端驗證
    if (!this.validateLicenseNumber(licenseNumber)) {
      return;
    }

    // 開始驗證流程
    await this.startVerification(formData);
  },

  /**
   * 處理執照號碼輸入
   */
  handleLicenseInput: function(event) {
    const input = event.target;
    let value = input.value;

    // 移除不必要的字符
    value = value.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
    
    // 格式化輸入
    this.formatLicenseNumber(input);
    
    // 即時驗證
    this.clearFieldErrors(input);
    
    // 更新提交按鈕狀態
    this.updateSubmitButtonState();
  },

  /**
   * 格式化執照號碼
   */
  formatLicenseNumber: function(input) {
    let value = input.value.trim();
    
    // 基本清理
    value = value.replace(/\s+/g, '');
    
    // 自動大寫英文字母
    value = value.replace(/[a-z]/g, (match) => match.toUpperCase());
    
    input.value = value;
  },

  /**
   * 驗證執照號碼格式
   */
  validateLicenseNumber: function(licenseNumber) {
    if (!licenseNumber) {
      this.showFieldError(this.elements.licenseInput, '請輸入執照號碼');
      return false;
    }

    if (licenseNumber.length < 8) {
      this.showFieldError(this.elements.licenseInput, '執照號碼長度不足');
      return false;
    }

    // 檢查格式
    const isValidFormat = this.licensePatterns.some(pattern => 
      pattern.test(licenseNumber)
    );

    if (!isValidFormat) {
      this.showFieldError(this.elements.licenseInput, '執照號碼格式不正確，請參考範例格式');
      return false;
    }

    this.clearFieldErrors(this.elements.licenseInput);
    return true;
  },

  /**
   * 開始執照驗證
   */
  startVerification: async function(formData) {
    try {
      this.state.isVerifying = true;
      this.state.currentAttempt++;
      
      // 顯示驗證 Modal
      this.showVerificationModal();
      
      // 開始進度條動畫
      this.startProgressAnimation();
      
      // 設定超時保護
      this.setVerificationTimeout();
      
      // 發送驗證請求
      const result = await this.submitVerificationRequest(formData);
      
      // 處理驗證結果
      await this.handleVerificationResult(result);
      
    } catch (error) {
      await this.handleVerificationError(error);
    }
  },

  /**
   * 提交驗證請求
   */
  submitVerificationRequest: async function(formData) {
    const url = this.elements.form.action || window.location.href;
    
    PD.debug.log('發送執照驗證請求', { url, attempt: this.state.currentAttempt });
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type');
    
    // 檢查是否為 JSON 回應
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    } 
    
    // 檢查是否為重定向（成功情況）
    if (response.redirected || response.status === 302) {
      return {
        success: true,
        redirect: response.url || '/clinic/dashboard/'
      };
    }
    
    // 其他情況視為 HTML 回應（包含表單錯誤）
    const html = await response.text();
    return this.parseHtmlResponse(html);
  },

  /**
   * 解析 HTML 回應
   */
  parseHtmlResponse: function(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // 檢查是否有錯誤訊息
    const errorElements = doc.querySelectorAll('.invalid-feedback, .errorlist');
    const errors = {};
    
    errorElements.forEach(element => {
      const fieldName = this.findFieldNameFromError(element);
      if (fieldName) {
        errors[fieldName] = [element.textContent.trim()];
      }
    });
    
    // 檢查是否有成功訊息
    const successElements = doc.querySelectorAll('.alert-success');
    const hasSuccess = successElements.length > 0;
    
    return {
      success: hasSuccess,
      errors: Object.keys(errors).length > 0 ? errors : null,
      message: hasSuccess ? '驗證成功！' : '驗證失敗，請檢查輸入資料'
    };
  },

  /**
   * 從錯誤元素找到對應的欄位名稱
   */
  findFieldNameFromError: function(errorElement) {
    // 向上查找包含欄位的容器
    let container = errorElement.closest('.form-group, .mb-4, .field');
    if (container) {
      const input = container.querySelector('input, select, textarea');
      return input ? input.name : null;
    }
    return 'vet_license_number'; // 預設為執照號碼欄位
  },

  /**
   * 處理驗證結果
   */
  handleVerificationResult: async function(result) {
    // 完成進度條動畫
    await this.completeProgressAnimation();
    
    if (result.success) {
      await this.handleVerificationSuccess(result);
    } else {
      await this.handleVerificationFailure(result);
    }
  },

  /**
   * 處理驗證成功
   */
  handleVerificationSuccess: async function(result) {
    PD.debug.log('執照驗證成功', result);
    
    // 更新進度條為成功狀態
    this.updateProgressBar(100, 'success');
    
    // 顯示成功訊息
    this.updateModalContent('success', '驗證成功！', '您的執照已通過農委會驗證，即將跳轉到診所管理頁面...');
    
    // 短暫延遲後跳轉
    setTimeout(() => {
      const redirectUrl = result.redirect || '/clinic/dashboard/';
      window.location.href = redirectUrl;
    }, 2000);
  },

  /**
   * 處理驗證失敗
   */
  handleVerificationFailure: async function(result) {
    PD.debug.warn('執照驗證失敗', result);
    
    this.state.isVerifying = false;
    this.hideVerificationModal();
    
    // 顯示錯誤訊息
    if (result.errors) {
      this.showFormErrors(result.errors);
    } else {
      this.showMessage(result.message || '驗證失敗，請檢查執照號碼是否正確', 'error');
    }
    
    // 重置提交按鈕
    this.resetSubmitButton();
    
    // 提供重試選項
    if (this.state.currentAttempt < this.config.retryAttempts) {
      setTimeout(() => {
        this.showRetryOption();
      }, 1000);
    }
  },

  /**
   * 處理驗證錯誤
   */
  handleVerificationError: async function(error) {
    PD.debug.error('驗證請求發生錯誤', error);
    
    this.state.isVerifying = false;
    this.hideVerificationModal();
    
    let errorMessage = '驗證過程發生錯誤';
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      errorMessage = '網路連線錯誤，請檢查網路設定後重試';
    } else if (error.message.includes('timeout')) {
      errorMessage = '驗證請求超時，請稍後重試';
    } else if (error.message.includes('HTTP')) {
      errorMessage = '伺服器回應錯誤，請聯絡客服協助';
    }
    
    this.showMessage(errorMessage, 'error');
    this.resetSubmitButton();
    
    // 提供重試選項
    if (this.state.currentAttempt < this.config.retryAttempts) {
      setTimeout(() => {
        this.showRetryOption();
      }, 1000);
    }
  },

  /**
   * 顯示驗證 Modal
   */
  showVerificationModal: function() {
    if (this.state.modal) {
      this.updateModalContent('loading', '正在驗證執照...', '請稍候，系統正在向農委會查詢您的執照資訊');
      this.state.modal.show();
    }
  },

  /**
   * 隱藏驗證 Modal
   */
  hideVerificationModal: function() {
    if (this.state.modal) {
      this.state.modal.hide();
    }
  },

  /**
   * 更新 Modal 內容
   */
  updateModalContent: function(type, title, description) {
    const modal = this.elements.modal;
    if (!modal) return;

    const iconElement = modal.querySelector('.verification-spinner');
    const titleElement = modal.querySelector('h5');
    const descElement = modal.querySelector('p');

    if (type === 'success') {
      iconElement.innerHTML = '<i class="bi bi-check-circle-fill text-success" style="font-size: 3rem;"></i>';
      titleElement.className = 'mb-2 text-success';
    } else if (type === 'error') {
      iconElement.innerHTML = '<i class="bi bi-x-circle-fill text-danger" style="font-size: 3rem;"></i>';
      titleElement.className = 'mb-2 text-danger';
    }

    titleElement.textContent = title;
    descElement.textContent = description;
  },

  /**
   * 開始進度條動畫
   */
  startProgressAnimation: function() {
    if (!this.elements.progressBar) return;

    let progress = 0;
    this.state.progressTimer = setInterval(() => {
      if (progress < 90) {
        progress += Math.random() * 15;
        progress = Math.min(progress, 90);
        this.updateProgressBar(progress);
      }
    }, this.config.progressUpdateInterval);
  },

  /**
   * 完成進度條動畫
   */
  completeProgressAnimation: function() {
    return new Promise((resolve) => {
      if (this.state.progressTimer) {
        clearInterval(this.state.progressTimer);
        this.state.progressTimer = null;
      }

      if (this.elements.progressBar) {
        this.updateProgressBar(100);
        setTimeout(resolve, 500);
      } else {
        resolve();
      }
    });
  },

  /**
   * 更新進度條
   */
  updateProgressBar: function(percentage, type = 'primary') {
    if (!this.elements.progressBar) return;

    this.elements.progressBar.style.width = `${percentage}%`;
    this.elements.progressBar.setAttribute('aria-valuenow', percentage);

    // 更新樣式
    this.elements.progressBar.className = `progress-bar progress-bar-striped progress-bar-animated`;
    
    if (type === 'success') {
      this.elements.progressBar.style.background = 'linear-gradient(135deg, var(--success-color) 0%, #20c997 100%)';
    } else if (type === 'error') {
      this.elements.progressBar.style.background = 'linear-gradient(135deg, var(--error-color) 0%, #dc3545 100%)';
    }
  },

  /**
   * 設定驗證超時
   */
  setVerificationTimeout: function() {
    this.state.verificationTimer = setTimeout(() => {
      if (this.state.isVerifying) {
        this.cancelVerification();
        this.showMessage('驗證請求超時，請重試', 'warning');
      }
    }, this.config.verificationTimeout);
  },

  /**
   * 取消驗證
   */
  cancelVerification: function() {
    PD.debug.log('取消執照驗證');
    
    this.state.isVerifying = false;
    
    // 清理計時器
    if (this.state.verificationTimer) {
      clearTimeout(this.state.verificationTimer);
      this.state.verificationTimer = null;
    }
    
    if (this.state.progressTimer) {
      clearInterval(this.state.progressTimer);
      this.state.progressTimer = null;
    }
    
    // 隱藏 Modal
    this.hideVerificationModal();
    
    // 重置按鈕
    this.resetSubmitButton();
  },

  /**
   * 顯示表單錯誤
   */
  showFormErrors: function(errors) {
    Object.keys(errors).forEach(fieldName => {
      const field = this.elements.form.querySelector(`[name="${fieldName}"]`);
      if (field) {
        this.showFieldError(field, errors[fieldName].join(', '));
      }
    });
  },

  /**
   * 顯示欄位錯誤
   */
  showFieldError: function(field, message) {
    PD.form.setValidation(field, false, message);
    
    // 聚焦到錯誤欄位
    field.focus();
  },

  /**
   * 清除欄位錯誤
   */
  clearFieldErrors: function(field) {
    field.classList.remove('is-invalid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
      feedback.style.display = 'none';
    }
  },

  /**
   * 更新提交按鈕狀態
   */
  updateSubmitButtonState: function() {
    if (!this.elements.submitBtn) return;

    const licenseNumber = this.elements.licenseInput?.value?.trim();
    const isValid = this.validateLicenseNumber(licenseNumber);
    
    this.elements.submitBtn.disabled = !isValid || this.state.isVerifying;
    
    if (isValid && !this.state.isVerifying) {
      this.elements.submitBtn.classList.remove('btn-secondary');
      this.elements.submitBtn.classList.add('btn-primary-custom');
    } else {
      this.elements.submitBtn.classList.remove('btn-primary-custom');
      this.elements.submitBtn.classList.add('btn-secondary');
    }
  },

  /**
   * 重置提交按鈕
   */
  resetSubmitButton: function() {
    if (!this.elements.submitBtn) return;

    this.elements.submitBtn.disabled = false;
    this.elements.submitBtn.innerHTML = '<i class="bi bi-shield-check me-2"></i>開始驗證';
    this.updateSubmitButtonState();
  },

  /**
   * 顯示重試選項
   */
  showRetryOption: function() {
    const retryMessage = `驗證失敗，您還可以重試 ${this.config.retryAttempts - this.state.currentAttempt} 次`;
    this.showMessage(retryMessage, 'warning');
  },

  /**
   * 顯示訊息
   */
  showMessage: function(message, type) {
    PD.message.show(message, type);
  },

  /**
   * 清理資源
   */
  cleanup: function() {
    this.cancelVerification();
    PD.debug.log('執照驗證模組資源已清理');
  }
};

// 頁面載入完成後自動初始化
document.addEventListener('DOMContentLoaded', function() {
  window.VetLicenseVerification.init();
});

// 頁面卸載時清理資源
window.addEventListener('beforeunload', function() {
  window.VetLicenseVerification.cleanup();
});

// 全局別名
window.LicenseVerify = window.VetLicenseVerification;