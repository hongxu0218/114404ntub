/* static/js/utils.js - 毛日好工具函數 */

/**
 * 工具函數集合
 */
window.PawDayUtils = {
  
  /**
   * API 請求工具
   */
  api: {
    /**
     * 發送 GET 請求
     * @param {string} url - 請求 URL
     * @param {Object} options - 可選參數
     * @returns {Promise}
     */
    get: async function(url, options = {}) {
      try {
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
          },
          ...options
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
      } catch (error) {
        console.error('API GET 請求失敗:', error);
        throw error;
      }
    },

    /**
     * 發送 POST 請求
     * @param {string} url - 請求 URL
     * @param {Object} data - 發送的資料
     * @param {Object} options - 可選參數
     * @returns {Promise}
     */
    post: async function(url, data = {}, options = {}) {
      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
            ...options.headers
          },
          body: JSON.stringify(data),
          ...options
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
      } catch (error) {
        console.error('API POST 請求失敗:', error);
        throw error;
      }
    }
  },

  /**
   * 本地儲存工具
   */
  storage: {
    /**
     * 設定本地儲存
     * @param {string} key - 鍵名
     * @param {any} value - 值
     */
    set: function(key, value) {
      try {
        localStorage.setItem(`pawday_${key}`, JSON.stringify(value));
      } catch (error) {
        console.warn('無法寫入本地儲存:', error);
      }
    },

    /**
     * 取得本地儲存
     * @param {string} key - 鍵名
     * @param {any} defaultValue - 預設值
     * @returns {any}
     */
    get: function(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(`pawday_${key}`);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.warn('無法讀取本地儲存:', error);
        return defaultValue;
      }
    },

    /**
     * 移除本地儲存
     * @param {string} key - 鍵名
     */
    remove: function(key) {
      try {
        localStorage.removeItem(`pawday_${key}`);
      } catch (error) {
        console.warn('無法移除本地儲存:', error);
      }
    }
  },

  /**
   * DOM 操作工具
   */
  dom: {
    /**
     * 等待元素出現
     * @param {string} selector - CSS 選擇器
     * @param {number} timeout - 超時時間（毫秒）
     * @returns {Promise<Element>}
     */
    waitForElement: function(selector, timeout = 10000) {
      return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
          resolve(element);
          return;
        }

        const observer = new MutationObserver((mutations, obs) => {
          const element = document.querySelector(selector);
          if (element) {
            obs.disconnect();
            resolve(element);
          }
        });

        observer.observe(document.body, {
          childList: true,
          subtree: true
        });

        setTimeout(() => {
          observer.disconnect();
          reject(new Error(`元素 ${selector} 在 ${timeout}ms 內未找到`));
        }, timeout);
      });
    },

    /**
     * 平滑滾動到元素
     * @param {string|Element} target - 目標元素或選擇器
     * @param {Object} options - 滾動選項
     */
    scrollTo: function(target, options = {}) {
      const element = typeof target === 'string' ? 
                     document.querySelector(target) : target;
      
      if (element) {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
          inline: 'nearest',
          ...options
        });
      }
    },

    /**
     * 切換元素的顯示/隱藏
     * @param {string|Element} target - 目標元素或選擇器
     * @param {boolean} show - 是否顯示（可選）
     */
    toggle: function(target, show = null) {
      const element = typeof target === 'string' ? 
                     document.querySelector(target) : target;
      
      if (element) {
        if (show === null) {
          element.classList.toggle('d-none');
        } else {
          element.classList.toggle('d-none', !show);
        }
      }
    }
  },

  /**
   * 表單工具
   */
  form: {
    /**
     * 序列化表單資料
     * @param {HTMLFormElement} form - 表單元素
     * @returns {Object}
     */
    serialize: function(form) {
      const formData = new FormData(form);
      const data = {};
      
      for (let [key, value] of formData.entries()) {
        if (data[key]) {
          if (Array.isArray(data[key])) {
            data[key].push(value);
          } else {
            data[key] = [data[key], value];
          }
        } else {
          data[key] = value;
        }
      }
      
      return data;
    },

    /**
     * 重置表單並移除驗證樣式
     * @param {HTMLFormElement} form - 表單元素
     */
    reset: function(form) {
      form.reset();
      
      // 移除 Bootstrap 驗證樣式
      form.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
        el.classList.remove('is-valid', 'is-invalid');
      });
      
      form.querySelectorAll('.valid-feedback, .invalid-feedback').forEach(el => {
        el.style.display = 'none';
      });
    },

    /**
     * 設定欄位驗證狀態
     * @param {HTMLElement} field - 欄位元素
     * @param {boolean} isValid - 是否有效
     * @param {string} message - 驗證訊息
     */
    setValidation: function(field, isValid, message = '') {
      field.classList.remove('is-valid', 'is-invalid');
      field.classList.add(isValid ? 'is-valid' : 'is-invalid');
      
      // 找到或創建回饋元素
      let feedback = field.parentNode.querySelector(
        isValid ? '.valid-feedback' : '.invalid-feedback'
      );
      
      if (!feedback && message) {
        feedback = document.createElement('div');
        feedback.className = isValid ? 'valid-feedback' : 'invalid-feedback';
        field.parentNode.appendChild(feedback);
      }
      
      if (feedback) {
        feedback.textContent = message;
        feedback.style.display = message ? 'block' : 'none';
      }
    }
  },

  /**
   * 日期時間工具
   */
  datetime: {
    /**
     * 格式化日期
     * @param {Date|string} date - 日期
     * @param {string} format - 格式（YYYY-MM-DD, MM/DD, etc.）
     * @returns {string}
     */
    format: function(date, format = 'YYYY-MM-DD') {
      const d = new Date(date);
      if (isNaN(d.getTime())) return '';
      
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hour = String(d.getHours()).padStart(2, '0');
      const minute = String(d.getMinutes()).padStart(2, '0');
      
      return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hour)
        .replace('mm', minute);
    },

    /**
     * 取得相對時間（如：2小時前）
     * @param {Date|string} date - 日期
     * @returns {string}
     */
    relative: function(date) {
      const now = new Date();
      const target = new Date(date);
      const diff = now - target;
      
      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);
      const days = Math.floor(hours / 24);
      
      if (days > 0) return `${days}天前`;
      if (hours > 0) return `${hours}小時前`;
      if (minutes > 0) return `${minutes}分鐘前`;
      return '剛剛';
    }
  },

  /**
   * 載入狀態管理
   */
  loading: {
    /**
     * 顯示載入動畫
     * @param {string} target - 目標元素選擇器（可選）
     */
    show: function(target = '#loadingSpinner') {
      const spinner = document.querySelector(target);
      if (spinner) {
        spinner.style.display = 'block';
      }
    },

    /**
     * 隱藏載入動畫
     * @param {string} target - 目標元素選擇器（可選）
     */
    hide: function(target = '#loadingSpinner') {
      const spinner = document.querySelector(target);
      if (spinner) {
        spinner.style.display = 'none';
      }
    }
  },

  /**
   * 訊息提示工具
   */
  message: {
    /**
     * 顯示 Toast 訊息
     * @param {string} message - 訊息內容
     * @param {string} type - 訊息類型（success, error, warning, info）
     * @param {number} duration - 顯示時間（毫秒）
     */
    show: function(message, type = 'info', duration = 5000) {
      const container = document.querySelector('.messages-container');
      if (!container) return;
      
      const alertDiv = document.createElement('div');
      alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
      alertDiv.setAttribute('role', 'alert');
      
      const iconMap = {
        success: 'bi-check-circle-fill',
        error: 'bi-exclamation-triangle-fill',
        warning: 'bi-exclamation-circle-fill',
        info: 'bi-info-circle-fill'
      };
      
      alertDiv.innerHTML = `
        <i class="bi ${iconMap[type]} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="關閉"></button>
      `;
      
      container.appendChild(alertDiv);
      
      // 自動移除
      setTimeout(() => {
        if (alertDiv.parentNode) {
          const bsAlert = new bootstrap.Alert(alertDiv);
          bsAlert.close();
        }
      }, duration);
    }
  },

  /**
   * 調試工具
   */
  debug: {
    /**
     * 記錄訊息（只在開發模式下）
     * @param {...any} args - 參數
     */
    log: function(...args) {
      if (window.DEBUG || localStorage.getItem('pawday_debug')) {
        console.log('[PawDay Debug]', ...args);
      }
    },

    /**
     * 記錄錯誤
     * @param {...any} args - 參數
     */
    error: function(...args) {
      console.error('[PawDay Error]', ...args);
    },

    /**
     * 記錄警告
     * @param {...any} args - 參數
     */
    warn: function(...args) {
      console.warn('[PawDay Warning]', ...args);
    }
  }
};

// 全局別名
window.PD = window.PawDayUtils;