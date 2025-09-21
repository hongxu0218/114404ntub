/* static/js/base.js - 毛日好主要功能 */

/**
 * 毛日好主應用程式
 */
window.PawDayApp = {
  
  // 配置選項
  config: {
    notificationUpdateInterval: 30000, // 30秒更新一次通知
    messageAutoHideDelay: 5000,        // 5秒後自動隱藏訊息
    loadingTimeout: 30000,             // 30秒載入超時
    apiTimeout: 15000                  // 15秒API請求超時
  },

  // 內部狀態
  state: {
    isLoggedIn: false,
    userType: null,
    userProfile: null,
    currentTheme: null,
    notificationTimer: null,
    isLoading: false
  },

  /**
   * 初始化應用程式
   */
  init: function() {
    // console.log('🐾 毛日好系統啟動中...');
    
    // 檢查是否已準備好
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.onReady());
    } else {
      this.onReady();
    }
  },

  /**
   * DOM 準備就緒後執行
   */
  onReady: function() {
    this.setupUser();
    // this.setupTheme(); // 暫時停用自動主題切換
    this.setupNavigation();
    this.setupMessages();
    this.setupForms();
    this.setupNotifications();
    this.setupScrollEffects();
    this.setupLoadingIndicators();
    this.setupErrorHandling();
    
//     console.log('✅ 毛日好系統初始化完成');
  },

  /**
   * 設定使用者資訊
   */
  setupUser: function() {
    // 從 DOM 或全局變數取得使用者資訊
    const userElement = document.querySelector('[data-user-authenticated]');
    if (userElement) {
      this.state.isLoggedIn = userElement.dataset.userAuthenticated === 'true';
      this.state.userType = userElement.dataset.userType || null;
      this.state.userProfile = userElement.dataset.userProfile || null;
    }
    
    PD.debug.log('使用者狀態:', {
      isLoggedIn: this.state.isLoggedIn,
      userType: this.state.userType,
      userProfile: this.state.userProfile
    });
  },

  /**
   * 設定主題風格
   */
  setupTheme: function() {
    if (!this.state.isLoggedIn) {
      PD.debug.log('未登入用戶，使用預設主題');
      return;
    }

    // 移除所有現有主題類別
    document.body.classList.remove('vet-theme', 'admin-theme', 'owner-theme');
    
    // 根據用戶角色決定主題
    let themeClass = '';
    const userType = this.state.userType;
    const userProfile = this.state.userProfile;
    
    // 獸醫師主題 - 專業醫療藍色
    if (userProfile === 'veterinarian' || userType === 'vet') {
      themeClass = 'vet-theme';
      PD.debug.log('應用獸醫師主題');
    }
    // 診所管理員主題 - 管理紫色
    else if (userProfile === 'clinic_admin' || userType === 'clinic_admin') {
      themeClass = 'admin-theme';
      PD.debug.log('應用診所管理員主題');
    }
    // 飼主主題 - 溫暖橙色（預設）
    else if (userProfile === 'pet_owner' || userType === 'owner') {
      themeClass = 'owner-theme';
      PD.debug.log('應用飼主主題');
    }
    
    // 應用主題類別
    if (themeClass) {
      document.body.classList.add(themeClass);
      this.state.currentTheme = themeClass;
      
      // 同時應用到導航欄
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        navbar.classList.add('medical-navbar');
      }
      
      // 觸發主題變更事件
      const themeEvent = new CustomEvent('themeChanged', {
        detail: { theme: themeClass, userType: userType, userProfile: userProfile }
      });
      document.dispatchEvent(themeEvent);
      
      PD.debug.log(`✅ 已應用 ${themeClass} 主題`);
    } else {
      PD.debug.log('⚠️ 無法識別用戶角色，使用預設主題');
    }
  },

  /**
   * 設定導航功能
   */
  setupNavigation: function() {
    // 平滑滾動
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          const href = anchor.getAttribute('href');
          
          // 檢查 href 是否只是 "#" 或空值
          if (!href || href === '#' || href.length <= 1) {
            e.preventDefault();
            return; // 直接返回，不執行滾動
          }
          
          e.preventDefault();
          const target = document.querySelector(href);
          if (target) {
            PD.dom.scrollTo(target);
          }
        });
      });

    // 導航欄收合（手機版）
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
      // 點擊連結後自動收合導航欄
      navbarCollapse.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
          if (window.innerWidth < 992) { // Bootstrap lg breakpoint
            const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
              toggle: false
            });
            bsCollapse.hide();
          }
        });
      });
    }

    // 添加當前頁面的導航高亮
    this.highlightCurrentNav();
  },

  /**
   * 高亮當前頁面的導航項目
   */
  highlightCurrentNav: function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
        link.classList.add('active');
        link.style.backgroundColor = 'var(--primary-orange-light)';
      }
    });
  },

  /**
   * 設定訊息系統
   */
  setupMessages: function() {
    // 自動隱藏訊息提示
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
      setTimeout(() => {
        if (alert.parentNode && alert.classList.contains('show')) {
          const bsAlert = new bootstrap.Alert(alert);
          bsAlert.close();
        }
      }, this.config.messageAutoHideDelay);
    });

    // 監聽關閉事件
    document.addEventListener('closed.bs.alert', (event) => {
      PD.debug.log('訊息已關閉:', event.target);
    });
  },

  /**
   * 設定表單功能
   */
  setupForms: function() {
    // 表單提交時顯示載入動畫
    document.querySelectorAll('form:not(.no-loading)').forEach(form => {
      form.addEventListener('submit', (e) => {
        // 檢查表單是否有效
        if (form.checkValidity()) {
          this.showLoading();
          
          // 設定超時保護
          setTimeout(() => {
            this.hideLoading();
          }, this.config.loadingTimeout);
        }
      });
    });

    // AJAX 表單處理
    document.querySelectorAll('form[data-ajax="true"]').forEach(form => {
      form.addEventListener('submit', (e) => this.handleAjaxForm(e));
    });

    // 即時表單驗證
    document.querySelectorAll('input[data-validate], textarea[data-validate]').forEach(field => {
      field.addEventListener('blur', () => this.validateField(field));
      field.addEventListener('input', () => this.clearFieldError(field));
    });
  },

  /**
   * 處理 AJAX 表單提交
   */
  handleAjaxForm: async function(event) {
    event.preventDefault();
    const form = event.target;
    const url = form.action || window.location.href;
    
    try {
      this.showLoading();
      
      const formData = new FormData(form);
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      
      const result = await response.json();
      
      if (result.success) {
        PD.message.show(result.message || '操作成功', 'success');
        
        // 重置表單
        if (result.reset_form !== false) {
          PD.form.reset(form);
        }
        
        // 重定向
        if (result.redirect) {
          setTimeout(() => {
            window.location.href = result.redirect;
          }, 1000);
        }
      } else {
        PD.message.show(result.message || '操作失敗', 'error');
        
        // 顯示欄位錯誤
        if (result.errors) {
          this.showFormErrors(form, result.errors);
        }
      }
    } catch (error) {
      PD.debug.error('AJAX 表單提交失敗:', error);
      PD.message.show('網路錯誤，請稍後再試', 'error');
    } finally {
      this.hideLoading();
    }
  },

  /**
   * 顯示表單錯誤
   */
  showFormErrors: function(form, errors) {
    // 清除現有錯誤
    form.querySelectorAll('.is-invalid').forEach(field => {
      field.classList.remove('is-invalid');
    });
    
    // 顯示新錯誤
    Object.keys(errors).forEach(fieldName => {
      const field = form.querySelector(`[name="${fieldName}"]`);
      if (field) {
        PD.form.setValidation(field, false, errors[fieldName].join(', '));
      }
    });
  },

  /**
   * 驗證欄位
   */
  validateField: function(field) {
    const value = field.value.trim();
    const type = field.dataset.validate;
    let isValid = true;
    let message = '';

    switch (type) {
      case 'required':
        isValid = value.length > 0;
        message = isValid ? '' : '此欄位為必填';
        break;
      
      case 'email':
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        isValid = value === '' || emailRegex.test(value);
        message = isValid ? '' : '請輸入有效的電子郵件地址';
        break;
      
      case 'phone':
        const phoneRegex = /^09\d{8}$/;
        isValid = value === '' || phoneRegex.test(value);
        message = isValid ? '' : '請輸入有效的手機號碼（格式：09xxxxxxxx）';
        break;
      
      case 'password':
        isValid = value.length === 0 || value.length >= 8;
        message = isValid ? '' : '密碼長度至少需要8個字元';
        break;
    }

    PD.form.setValidation(field, isValid, message);
    return isValid;
  },

  /**
   * 清除欄位錯誤
   */
  clearFieldError: function(field) {
    if (field.classList.contains('is-invalid')) {
      field.classList.remove('is-invalid');
      const feedback = field.parentNode.querySelector('.invalid-feedback');
      if (feedback) {
        feedback.style.display = 'none';
      }
    }
  },

  /**
   * 設定通知系統
   */
  setupNotifications: function() {
    if (!this.state.isLoggedIn) return;

    // 初始載入通知數量
    this.updateNotificationCount();

    // 定期更新通知數量
    this.state.notificationTimer = setInterval(() => {
      this.updateNotificationCount();
    }, this.config.notificationUpdateInterval);

    // 頁面隱藏時停止更新，顯示時恢復
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.stopNotificationUpdates();
      } else {
        this.startNotificationUpdates();
      }
    });
  },

  /**
   * 更新通知數量
   */
  updateNotificationCount: async function() {
    try {
      const data = await PD.api.get('/api/notifications/count/');
      const countElement = document.getElementById('notification-count');
      
      if (countElement) {
        if (data.count > 0) {
          countElement.textContent = data.count > 99 ? '99+' : data.count;
          countElement.classList.remove('d-none');
          
          // 更新頁面標題
          document.title = `(${data.count}) 毛日好 Paw&Day`;
        } else {
          countElement.classList.add('d-none');
          
          // 恢復原始標題
          const originalTitle = document.title.replace(/^\(\d+\)\s/, '');
          document.title = originalTitle;
        }
      }
    } catch (error) {
      PD.debug.error('無法取得通知數量:', error);
    }
  },

  /**
   * 停止通知更新
   */
  stopNotificationUpdates: function() {
    if (this.state.notificationTimer) {
      clearInterval(this.state.notificationTimer);
      this.state.notificationTimer = null;
    }
  },

  /**
   * 開始通知更新
   */
  startNotificationUpdates: function() {
    if (!this.state.notificationTimer && this.state.isLoggedIn) {
      this.state.notificationTimer = setInterval(() => {
        this.updateNotificationCount();
      }, this.config.notificationUpdateInterval);
    }
  },

  /**
   * 設定滾動效果
   */
  setupScrollEffects: function() {
    // 回到頂部按鈕
    const backToTopBtn = document.createElement('button');
    backToTopBtn.className = 'btn btn-primary-custom back-to-top';
    backToTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    backToTopBtn.style.cssText = `
      position: fixed;
      bottom: 30px;
      right: 30px;
      z-index: 1000;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      display: none;
      box-shadow: 0 4px 12px var(--shadow-light);
    `;
    
    document.body.appendChild(backToTopBtn);

    // 監聽滾動事件
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          this.handleScroll(backToTopBtn);
          ticking = false;
        });
        ticking = true;
      }
    });

    // 點擊回到頂部
    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  },

  /**
   * 處理滾動事件
   */
  handleScroll: function(backToTopBtn) {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    // 顯示/隱藏回到頂部按鈕
    if (scrollTop > 300) {
      backToTopBtn.style.display = 'block';
    } else {
      backToTopBtn.style.display = 'none';
    }

    // 導航欄背景透明度調整
    const header = document.querySelector('.custom-header');
    if (header) {
      if (scrollTop > 10) {
        header.style.backgroundColor = 'rgba(255, 248, 240, 0.95)';
        header.style.backdropFilter = 'blur(10px)';
      } else {
        header.style.backgroundColor = 'var(--warm-bg)';
        header.style.backdropFilter = 'none';
      }
    }
  },

  /**
   * 設定載入指示器
   */
  setupLoadingIndicators: function() {
    // 全局載入控制
    window.showLoading = () => this.showLoading();
    window.hideLoading = () => this.hideLoading();
  },

  /**
   * 顯示載入動畫
   */
  showLoading: function() {
    if (this.state.isLoading) return;
    
    this.state.isLoading = true;
    PD.loading.show();
    
    // 禁用所有表單提交按鈕
    document.querySelectorAll('button[type="submit"]').forEach(btn => {
      btn.disabled = true;
      btn.dataset.originalText = btn.textContent;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>處理中...';
    });
  },

  /**
   * 隱藏載入動畫
   */
  hideLoading: function() {
    if (!this.state.isLoading) return;
    
    this.state.isLoading = false;
    PD.loading.hide();
    
    // 恢復所有表單提交按鈕
    document.querySelectorAll('button[type="submit"]').forEach(btn => {
      btn.disabled = false;
      if (btn.dataset.originalText) {
        btn.textContent = btn.dataset.originalText;
        delete btn.dataset.originalText;
      }
    });
  },

  /**
   * 設定錯誤處理
   */
  setupErrorHandling: function() {
    // 全局錯誤處理
    window.addEventListener('error', (event) => {
      PD.debug.error('全局錯誤:', event.error);
      
      // 隱藏載入動畫
      this.hideLoading();
      
      // 顯示錯誤訊息（開發模式）
      if (window.DEBUG) {
        PD.message.show('發生錯誤：' + event.error.message, 'error');
      }
    });

    // Promise 錯誤處理
    window.addEventListener('unhandledrejection', (event) => {
      PD.debug.error('未處理的 Promise 錯誤:', event.reason);
      
      // 隱藏載入動畫
      this.hideLoading();
      
      // 防止錯誤在控制台顯示
      event.preventDefault();
    });
  },

  /**
   * 清理資源
   */
  cleanup: function() {
    this.stopNotificationUpdates();
    PD.debug.log('應用程式資源已清理');
  },

  /**
   * 取得當前主題資訊
   */
  getThemeInfo: function() {
    return {
      theme: this.state.currentTheme,
      userType: this.state.userType,
      userProfile: this.state.userProfile,
      isLoggedIn: this.state.isLoggedIn
    };
  },

  /**
   * 手動切換主題（用於測試）
   */
  switchTheme: function(themeClass) {
    if (!themeClass) return;
    
    // 移除所有現有主題
    document.body.classList.remove('vet-theme', 'admin-theme', 'owner-theme');
    
    // 應用新主題
    document.body.classList.add(themeClass);
    this.state.currentTheme = themeClass;
    
    // 觸發事件
    const themeEvent = new CustomEvent('themeChanged', {
      detail: { theme: themeClass, manual: true }
    });
    document.dispatchEvent(themeEvent);
    
    PD.debug.log(`手動切換到 ${themeClass} 主題`);
  }
};

// 頁面卸載時清理資源
window.addEventListener('beforeunload', () => {
  window.PawDayApp.cleanup();
});

// 自動初始化
window.PawDayApp.init();

// 全局別名
window.App = window.PawDayApp;