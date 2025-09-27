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
    this.enhanceKeyboardNavigation();
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
        link.setAttribute('aria-current', 'page');
        // 添加視覺化說明給螢幕閱讀器
        const srText = document.createElement('span');
        srText.className = 'sr-only';
        srText.textContent = ' (目前頁面)';
        link.appendChild(srText);
      }
    });
  },

  /**
   * 增強鍵盤導航
   */
  enhanceKeyboardNavigation: function() {
    const navItems = document.querySelectorAll('.navbar-nav .nav-item');

    navItems.forEach((item, index) => {
      const link = item.querySelector('.nav-link');
      if (!link) return;

      // 添加鍵盤事件
      link.addEventListener('keydown', (e) => {
        switch(e.key) {
          case 'ArrowRight':
          case 'ArrowDown':
            e.preventDefault();
            const nextItem = navItems[index + 1];
            if (nextItem) {
              const nextLink = nextItem.querySelector('.nav-link');
              if (nextLink) nextLink.focus();
            }
            break;

          case 'ArrowLeft':
          case 'ArrowUp':
            e.preventDefault();
            const prevItem = navItems[index - 1];
            if (prevItem) {
              const prevLink = prevItem.querySelector('.nav-link');
              if (prevLink) prevLink.focus();
            }
            break;

          case 'Home':
            e.preventDefault();
            const firstLink = navItems[0]?.querySelector('.nav-link');
            if (firstLink) firstLink.focus();
            break;

          case 'End':
            e.preventDefault();
            const lastLink = navItems[navItems.length - 1]?.querySelector('.nav-link');
            if (lastLink) lastLink.focus();
            break;
        }
      });

      // 增強下拉選單鍵盤導航
      if (link.classList.contains('dropdown-toggle')) {
        link.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            link.click();
            // 焦點移到第一個選項
            setTimeout(() => {
              const firstDropdownItem = item.querySelector('.dropdown-item');
              if (firstDropdownItem) firstDropdownItem.focus();
            }, 100);
          }
        });
      }
    });

    // 下拉選單項目鍵盤導航
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
      const items = menu.querySelectorAll('.dropdown-item');
      items.forEach((item, index) => {
        item.addEventListener('keydown', (e) => {
          switch(e.key) {
            case 'ArrowDown':
              e.preventDefault();
              const nextItem = items[index + 1];
              if (nextItem) nextItem.focus();
              break;

            case 'ArrowUp':
              e.preventDefault();
              const prevItem = items[index - 1];
              if (prevItem) prevItem.focus();
              break;

            case 'Escape':
              e.preventDefault();
              const toggle = menu.previousElementSibling;
              if (toggle) {
                toggle.click();
                toggle.focus();
              }
              break;

            case 'Home':
              e.preventDefault();
              if (items[0]) items[0].focus();
              break;

            case 'End':
              e.preventDefault();
              if (items[items.length - 1]) items[items.length - 1].focus();
              break;
          }
        });
      });
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

    // 設定通知下拉選單
    this.setupNotificationDropdown();

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
   * 設定通知下拉選單功能
   */
  setupNotificationDropdown: function() {
    const dropdown = document.getElementById('notificationDropdown');
    const markAllReadBtn = document.getElementById('mark-all-read');

    if (!dropdown) return;

    // 當下拉選單打開時載入通知
    dropdown.addEventListener('show.bs.dropdown', () => {
      this.loadNotifications();
    });

    // 標記全部已讀按鈕
    if (markAllReadBtn) {
      markAllReadBtn.addEventListener('click', () => {
        this.markAllNotificationsRead();
      });
    }
  },

  /**
   * 載入通知列表
   */
  loadNotifications: async function() {
    const notificationList = document.getElementById('notification-list');
    const loadingElement = document.getElementById('loading-notifications');

    if (!notificationList) return;

    try {
      // 顯示載入動畫
      if (loadingElement) {
        loadingElement.style.display = 'block';
      }

      const response = await fetch('/api/notifications/', {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // 包含 cookies
      });

      // 處理重定向（未登入）
      if (response.status === 302 || response.redirected) {
        this.renderAuthenticationError();
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // 確保 data 是有效的 JSON 並包含 notifications
      if (data && data.notifications) {
        this.renderNotifications(data.notifications);
      } else {
        this.renderNotifications([]);
      }

    } catch (error) {
      PD.debug.error('載入通知失敗:', error);
      this.renderNotificationError();
    } finally {
      // 隱藏載入動畫
      if (loadingElement) {
        loadingElement.style.display = 'none';
      }
    }
  },

  /**
   * 渲染通知列表
   */
  renderNotifications: function(notifications) {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;

    // 清空載入中的內容
    notificationList.innerHTML = '';

    if (notifications.length === 0) {
      notificationList.innerHTML = `
        <div class="notification-empty">
          <i class="bi bi-bell-slash"></i>
          <div>目前沒有通知</div>
        </div>
      `;
      return;
    }

    // 渲染每個通知
    notifications.forEach(notification => {
      const notificationElement = this.createNotificationElement(notification);
      notificationList.appendChild(notificationElement);
    });
  },

  /**
   * 創建通知元素
   */
  createNotificationElement: function(notification) {
    const element = document.createElement('div');
    element.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
    element.setAttribute('data-notification-id', notification.id);

    // 通知圖標類型
    let iconClass = 'system';
    if (notification.type === 'appointment') iconClass = 'appointment';
    else if (notification.type === 'reminder') iconClass = 'reminder';

    // 通知圖標
    let icon = 'bi-info-circle';
    if (notification.type === 'appointment') icon = 'bi-calendar-check';
    else if (notification.type === 'reminder') icon = 'bi-clock';

    // 格式化時間
    const timeAgo = this.formatTimeAgo(notification.created_at);

    element.innerHTML = `
      <div class="notification-content">
        <div class="notification-icon ${iconClass}">
          <i class="bi ${icon}"></i>
        </div>
        <div class="notification-text">
          <div class="notification-title">${this.escapeHtml(notification.title)}</div>
          <div class="notification-message">${this.escapeHtml(notification.message)}</div>
          <div class="notification-time">${timeAgo}</div>
        </div>
      </div>
    `;

    // 點擊事件
    element.addEventListener('click', () => {
      this.handleNotificationClick(notification);
    });

    return element;
  },

  /**
   * 處理通知點擊
   */
  handleNotificationClick: async function(notification) {
    try {
      // 調用新的通知點擊API，會自動標記為已讀並返回目標URL
      const response = await fetch(`/api/notifications/${notification.id}/click/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        // 標記UI為已讀
        const notificationElement = document.querySelector(`[data-notification-id="${notification.id}"]`);
        if (notificationElement) {
          notificationElement.classList.remove('unread');
        }

        // 更新通知計數
        this.updateNotificationCount();

        // 關閉通知下拉菜單
        const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('notificationDropdown'));
        if (dropdown) {
          dropdown.hide();
        }

        // 跳轉到目標頁面
        if (data.target_url && data.target_url !== window.location.pathname) {
          window.location.href = data.target_url;
        }
      } else {
        console.error('通知點擊處理失敗:', data.error);
      }

      // 如果有舊的URL邏輯，保留作為備用
      if (notification.url) {
        window.location.href = notification.url;
      }
    } catch (error) {
      PD.debug.error('處理通知點擊失敗:', error);
    }
  },

  /**
   * 標記單個通知為已讀
   */
  markNotificationRead: async function(notificationId) {
    try {
      const response = await fetch(`/api/notifications/${notificationId}/mark-read/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        }
      });

      if (response.ok) {
        // 更新UI
        const element = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (element) {
          element.classList.remove('unread');
        }
        // 更新通知數量
        this.updateNotificationCount();
      }
    } catch (error) {
      PD.debug.error('標記通知已讀失敗:', error);
    }
  },

  /**
   * 標記所有通知為已讀
   */
  markAllNotificationsRead: async function() {
    try {
      const response = await fetch('/api/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        }
      });

      if (response.ok) {
        // 更新UI - 移除所有未讀樣式
        document.querySelectorAll('.notification-item.unread').forEach(item => {
          item.classList.remove('unread');
        });

        // 更新通知數量
        this.updateNotificationCount();

        PD.message.show('已標記所有通知為已讀', 'success');
      }
    } catch (error) {
      PD.debug.error('標記所有通知已讀失敗:', error);
      PD.message.show('操作失敗，請稍後再試', 'error');
    }
  },

  /**
   * 渲染通知載入錯誤
   */
  renderNotificationError: function() {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;

    notificationList.innerHTML = `
      <div class="notification-empty">
        <i class="bi bi-exclamation-triangle"></i>
        <div>載入通知失敗</div>
        <small class="text-muted">請重新整理頁面</small>
      </div>
    `;
  },

  /**
   * 渲染認證錯誤（用戶未登入）
   */
  renderAuthenticationError: function() {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;

    notificationList.innerHTML = `
      <div class="notification-empty">
        <i class="bi bi-person-x"></i>
        <div>請先登入</div>
        <small class="text-muted">登入後即可查看通知</small>
      </div>
    `;
  },

  /**
   * 格式化時間差
   */
  formatTimeAgo: function(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) {
      return '剛剛';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} 分鐘前`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} 小時前`;
    } else if (diffInSeconds < 604800) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} 天前`;
    } else {
      return date.toLocaleDateString('zh-TW');
    }
  },

  /**
   * 取得CSRF Token
   */
  getCSRFToken: function() {
    // 優先從表單元素獲取
    const formToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (formToken) {
      return formToken.value;
    }

    // 從 cookie 獲取
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') {
        return decodeURIComponent(value);
      }
    }

    // 從 meta 標籤獲取
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
      return metaToken.getAttribute('content');
    }

    return '';
  },

  /**
   * HTML轉義
   */
  escapeHtml: function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  /**
   * 獲取 CSRF Token
   */
  getCsrfToken: function() {
    // 從 cookie 獲取
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') {
        return decodeURIComponent(value);
      }
    }

    // 從 meta 標籤獲取
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
      return metaToken.getAttribute('content');
    }

    // 從隱藏的輸入欄位獲取
    const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (inputToken) {
      return inputToken.value;
    }

    return '';
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