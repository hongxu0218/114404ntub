/* static/js/homepage.js - 首頁專用功能 */

/**
 * 首頁功能模組
 */
window.PawDayHomepage = {
  
  // 配置選項
  config: {
    newsScrollSpeed: 220,          // 新聞滾動速度
    parallaxStrength: 0.1,         // 視差效果強度
    animationDelay: 100,           // 動畫延遲時間
    intersectionThreshold: 0.1,    // 元素進入視窗的觸發比例
    autoScrollInterval: 5000,      // 自動滾動間隔（毫秒）
    touchSensitivity: 50           // 觸控靈敏度
  },

  // 內部狀態
  state: {
    isAutoScrolling: false,
    touchStartX: 0,
    touchEndX: 0,
    currentNewsPosition: 0,
    observers: [],
    isInitialized: false
  },

  /**
   * 初始化首頁功能
   */
  init: function() {
    if (this.state.isInitialized) return;
    
    // 檢查是否為首頁
    if (!this.isHomePage()) return;
    
    PD.debug.log('🏠 首頁功能初始化中...');
    
    // 等待DOM準備完成
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.onReady());
    } else {
      this.onReady();
    }
  },

  /**
   * 檢查是否為首頁
   */
  isHomePage: function() {
    // 檢查URL路徑或特定元素來判斷是否為首頁
    const path = window.location.pathname;
    return path === '/' || path === '/home/' || 
           document.querySelector('.hero-section') !== null;
  },

  /**
   * DOM準備就緒後執行
   */
  onReady: function() {
    this.setupNewsScroll();
    this.setupCategoryCards();
    this.setupParallaxEffect();
    this.setupAnimations();
    this.setupTouchSupport();
    this.setupAccessibility();
    this.setupPerformanceOptimization();
    this.setupChatbot();  // 假設有一個聊天機器人功能需要初始化
    
    this.state.isInitialized = true;
    PD.debug.log('✅ 首頁功能初始化完成');
  },

  /**
   * 設定聊天機器人功能（覆蓋舊版：改用 /api/chat）
   */
  setupChatbot: function() {
    const $ = (id) => document.getElementById(id);
    const btn   = $('chatbot-button');
    const box   = $('chatbot-box');
    let   closeBtn = $('chatbot-close');
    let   sendBtn  = $('chatbot-send');
    let   input    = $('chatbot-text');
    let   messagesDiv = $('chatbot-messages');

    if (!btn || !box || !closeBtn || !sendBtn || !input || !messagesDiv) {
      (window.PD?.debug?.warn || console.warn)('🔎 找不到 AI 客服 DOM 節點，跳過初始化');
      return;
    }

    // ---- 清理舊事件監聽：clone 節點再綁定，確保「覆蓋舊功能」 ----
    function replaceNodeKeepId(el){
      if(!el) return el;
      const clone = el.cloneNode(true);
      if (el.parentNode) el.parentNode.replaceChild(clone, el);
      return clone;
    }
    closeBtn    = replaceNodeKeepId(closeBtn);
    sendBtn     = replaceNodeKeepId(sendBtn);
    input       = replaceNodeKeepId(input);
    messagesDiv = replaceNodeKeepId(messagesDiv);

    // ---- UI 調整：避免與回到頂部重疊 ----
    try {
      const btnStyle = btn.style;
      const boxStyle = box.style;
      if (!btnStyle.bottom) btnStyle.bottom = '88px';
      if (!boxStyle.bottom) boxStyle.bottom = '160px';
    } catch(_) {}

    // ---- 小工具 ----
    const history = []; // 只在前端保存，後端僅取最近 6 則
    let busy = false;
    const API_PATH = '/api/chat/'; // 後端請在 petapp/urls.py 加上 path("api/chat/", views.api_chat, ...)

    const addBubble = (sender, text) => {
      const msgDiv = document.createElement("div");
      msgDiv.className = 'cb-bubble ' + (sender === 'user' ? 'cb-user' : 'cb-bot');
      msgDiv.textContent = text;
      messagesDiv.appendChild(msgDiv);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    };

    const addTyping = () => {
      const div = document.createElement('div');
      div.className = 'cb-bubble cb-bot';
      div.textContent = '輸入中…';
      messagesDiv.appendChild(div);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      return div;
    };

    const getCSRFToken = () => {
      const name = 'csrftoken';
      const cookies = document.cookie ? document.cookie.split(';') : [];
      for (let c of cookies){
        c = c.trim();
        if (c.startsWith(name + '=')) return decodeURIComponent(c.substring(name.length+1));
      }
      return null;
    };

    const openBox = () => {
      box.style.display = 'flex';
      box.style.flexDirection = 'column';
      if (messagesDiv.childElementCount === 0) {
        addBubble('bot', '哈囉～我是毛日好 AI 客服，要查詢預約、健康紀錄或常見問題嗎？🙂');
      }
      input.focus();
    };
    const closeBox = () => { box.style.display = 'none'; };

    // ---- 事件 ----
    btn.addEventListener("click", () => {
      if (box.style.display === 'flex') closeBox(); else openBox();
    });
    closeBtn.addEventListener("click", closeBox);

    const sendMessage = async () => {
      const text = input.value.trim();
      if (!text || busy) return;
      busy = true;
      input.value = '';
      sendBtn.setAttribute('disabled', 'disabled');

      addBubble('user', text);
      const typing = addTyping();

      try {
        const headers = { "Content-Type": "application/json" };
        const csrftoken = getCSRFToken();
        if (csrftoken) headers["X-CSRFToken"] = csrftoken;

        const res = await fetch(API_PATH, {
          method: "POST",
          headers,
          body: JSON.stringify({ message: text, history }),
          credentials: 'same-origin'
        });

        let reply = '（後端沒有回覆）';
        if (res.ok) {
          const data = await res.json().catch(() => null);
          if (data && data.reply) reply = data.reply;
        } else {
          reply = `（伺服器錯誤 ${res.status}）`;
        }

        typing.remove();
        addBubble('bot', reply);
        history.push({role:'user', content:text}, {role:'assistant', content:reply});
      } catch (err) {
        typing.remove();
        addBubble('bot', '（連線失敗，請確認 /api/chat 是否可用，以及本機 Ollama 是否啟動）');
        (window.PD?.debug?.error || console.error)(err);
      } finally {
        busy = false;
        sendBtn.removeAttribute('disabled');
        input.focus();
      }
    };

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendMessage();
      if (e.key === "Escape") closeBox();
    });

    // 鍵盤快速開啟：Alt + /
    window.addEventListener('keydown', (e) => {
      if (e.altKey && e.key === '/') {
        if (box.style.display === 'flex') closeBox(); else openBox();
      }
    });
  },

  /**
   * 設定新聞滾動功能
   */
  setupNewsScroll: function() {
    const newsContainer = document.querySelector('.news-scroll-container .d-flex');
    if (!newsContainer) return;

    PD.debug.log('📰 設定新聞滾動功能');

    // 新聞卡片點擊效果
    const newsCards = document.querySelectorAll('.news-card:not(.more)');
    newsCards.forEach((card, index) => {
      // 滑鼠事件
      card.addEventListener('mouseenter', () => this.animateNewsCard(card, 'enter'));
      card.addEventListener('mouseleave', () => this.animateNewsCard(card, 'leave'));
      
      // 點擊事件
      card.addEventListener('click', (e) => {
        this.handleNewsCardClick(e, card, index);
      });
    });

    // "更多消息" 卡片
    const moreCard = document.querySelector('.news-card.more');
    if (moreCard) {
      moreCard.addEventListener('click', (e) => {
        e.preventDefault();
        this.showMoreNews();
      });
    }

    // 滾動控制按鈕（如果需要）
    this.createScrollButtons(newsContainer);
    
    // 自動滾動（可選）
    this.setupAutoScroll(newsContainer);
  },

  /**
   * 新聞卡片動畫
   */
  animateNewsCard: function(card, action) {
    if (action === 'enter') {
      card.style.transform = 'translateY(-8px) scale(1.02)';
      card.style.zIndex = '10';
      
      // 添加光澤效果
      const gloss = card.querySelector('::before');
      if (gloss) {
        gloss.style.transform = 'translateX(100%)';
      }
    } else {
      card.style.transform = 'translateY(-5px) scale(1)';
      card.style.zIndex = '1';
    }
  },

  /**
   * 處理新聞卡片點擊
   */
  handleNewsCardClick: function(event, card, index) {
    // 添加點擊動畫
    card.style.transform = 'scale(0.95)';
    
    setTimeout(() => {
      card.style.transform = 'translateY(-8px) scale(1.02)';
    }, 150);

    // 記錄點擊事件（如果需要分析）
    PD.debug.log(`新聞卡片點擊: ${index}`);
    
    // 可以在這裡添加GA追蹤
    if (window.gtag) {
      gtag('event', 'news_card_click', {
        'news_index': index,
        'news_url': card.href
      });
    }
  },

  /**
   * 顯示更多新聞
   */
  showMoreNews: function() {
    // 這裡可以實作載入更多新聞的邏輯
    PD.message.show('更多新聞功能開發中...', 'info');
    
    // 模擬載入效果
    const moreCard = document.querySelector('.news-card.more');
    if (moreCard) {
      moreCard.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';
      
      setTimeout(() => {
        moreCard.innerHTML = '<span><i class="bi bi-arrow-right-circle me-2"></i>更多消息</span>';
      }, 2000);
    }
  },

  /**
   * 創建滾動控制按鈕
   */
  createScrollButtons: function(container) {
    const scrollContainer = container.parentElement;
    if (!scrollContainer) return;

    // 左滾動按鈕
    const leftBtn = document.createElement('button');
    leftBtn.className = 'btn btn-outline-secondary news-scroll-btn news-scroll-left';
    leftBtn.innerHTML = '<i class="bi bi-chevron-left"></i>';
    leftBtn.setAttribute('aria-label', '向左滾動新聞');
    
    // 右滾動按鈕
    const rightBtn = document.createElement('button');
    rightBtn.className = 'btn btn-outline-secondary news-scroll-btn news-scroll-right';
    rightBtn.innerHTML = '<i class="bi bi-chevron-right"></i>';
    rightBtn.setAttribute('aria-label', '向右滾動新聞');

    // 按鈕樣式
    const btnStyle = `
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      z-index: 10;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255,255,255,0.9);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border-light);
      transition: all var(--transition-normal) ease;
    `;
    
    leftBtn.style.cssText = btnStyle + 'left: 10px;';
    rightBtn.style.cssText = btnStyle + 'right: 10px;';

    // 事件監聽
    leftBtn.addEventListener('click', () => this.scrollNews(container, 'left'));
    rightBtn.addEventListener('click', () => this.scrollNews(container, 'right'));

    // 添加到DOM
    scrollContainer.style.position = 'relative';
    scrollContainer.appendChild(leftBtn);
    scrollContainer.appendChild(rightBtn);

    // 根據滾動位置顯示/隱藏按鈕
    this.updateScrollButtons(container, leftBtn, rightBtn);
    container.addEventListener('scroll', () => {
      this.updateScrollButtons(container, leftBtn, rightBtn);
    });
  },

  /**
   * 滾動新聞
   */
  scrollNews: function(container, direction) {
    const scrollAmount = this.config.newsScrollSpeed;
    const currentScroll = container.scrollLeft;
    const targetScroll = direction === 'left' 
      ? currentScroll - scrollAmount 
      : currentScroll + scrollAmount;

    container.scrollTo({
      left: targetScroll,
      behavior: 'smooth'
    });

    // 記錄滾動事件
    PD.debug.log(`新聞滾動: ${direction}`);
  },

  /**
   * 更新滾動按鈕狀態
   */
  updateScrollButtons: function(container, leftBtn, rightBtn) {
    const scrollLeft = container.scrollLeft;
    const maxScroll = container.scrollWidth - container.clientWidth;

    leftBtn.style.opacity = scrollLeft > 0 ? '1' : '0.5';
    leftBtn.disabled = scrollLeft <= 0;
    
    rightBtn.style.opacity = scrollLeft < maxScroll ? '1' : '0.5';
    rightBtn.disabled = scrollLeft >= maxScroll;
  },

  /**
   * 設定自動滾動
   */
  setupAutoScroll: function(container) {
    let autoScrollTimer;

    const startAutoScroll = () => {
      if (this.state.isAutoScrolling) return;
      
      this.state.isAutoScrolling = true;
      autoScrollTimer = setInterval(() => {
        const maxScroll = container.scrollWidth - container.clientWidth;
        const currentScroll = container.scrollLeft;
        
        if (currentScroll >= maxScroll) {
          // 滾動到開頭
          container.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
          // 繼續向右滾動
          this.scrollNews(container, 'right');
        }
      }, this.config.autoScrollInterval);
    };

    const stopAutoScroll = () => {
      this.state.isAutoScrolling = false;
      if (autoScrollTimer) {
        clearInterval(autoScrollTimer);
        autoScrollTimer = null;
      }
    };

    // 滑鼠懸停時停止自動滾動
    container.addEventListener('mouseenter', stopAutoScroll);
    container.addEventListener('mouseleave', startAutoScroll);

    // 用戶滾動時停止自動滾動
    container.addEventListener('scroll', stopAutoScroll);

    // 開始自動滾動
    setTimeout(startAutoScroll, 3000);
  },

  /**
   * 設定分類卡片效果
   */
  setupCategoryCards: function() {
    const categoryCards = document.querySelectorAll('.category-card');
    if (categoryCards.length === 0) return;

    PD.debug.log('🎴 設定分類卡片效果');

    categoryCards.forEach((card, index) => {
      // 滑鼠事件
      card.addEventListener('mouseenter', () => this.animateCategoryCard(card, 'enter'));
      card.addEventListener('mouseleave', () => this.animateCategoryCard(card, 'leave'));
      
      // 點擊事件
      card.addEventListener('click', (e) => {
        this.handleCategoryCardClick(e, card, index);
      });

      // 鍵盤支援
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });

      // 確保卡片可以獲得焦點
      if (!card.hasAttribute('tabindex')) {
        card.setAttribute('tabindex', '0');
      }
    });
  },

  /**
   * 分類卡片動畫
   */
  animateCategoryCard: function(card, action) {
    const icon = card.querySelector('.category-icon');
    const text = card.querySelector('.category-text');

    if (action === 'enter') {
      card.style.transform = 'translateY(-12px)';
      card.style.boxShadow = '0 15px 45px rgba(0,0,0,0.2)';
      
      if (icon) {
        icon.style.transform = 'scale(1.2) rotate(5deg)';
      }
      
      if (text) {
        text.style.color = 'var(--primary-orange)';
      }
    } else {
      card.style.transform = 'translateY(-8px)';
      card.style.boxShadow = '0 12px 40px rgba(0,0,0,0.15)';
      
      if (icon) {
        icon.style.transform = 'scale(1.1)';
      }
      
      if (text) {
        text.style.color = '';
      }
    }
  },

  /**
   * 處理分類卡片點擊
   */
  handleCategoryCardClick: function(event, card, index) {
    // 點擊動畫
    card.style.transform = 'translateY(-8px) scale(0.95)';
    
    setTimeout(() => {
      card.style.transform = 'translateY(-12px) scale(1)';
    }, 150);

    // 記錄點擊事件
    const cardText = card.querySelector('.category-text')?.textContent || `卡片${index}`;
    PD.debug.log(`分類卡片點擊: ${cardText}`);

    // GA追蹤
    if (window.gtag) {
      gtag('event', 'category_card_click', {
        'category_name': cardText,
        'category_index': index
      });
    }
  },

  /**
   * 設定視差效果
   */
  setupParallaxEffect: function() {
    const heroImg = document.querySelector('.hero-img');
    if (!heroImg) return;

    PD.debug.log('🌟 設定視差效果');

    let ticking = false;

    const updateParallax = () => {
      const scrolled = window.pageYOffset;
      const rate = scrolled * this.config.parallaxStrength;
      
      if (heroImg) {
        heroImg.style.transform = `translateY(${rate}px)`;
      }
      
      ticking = false;
    };

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(updateParallax);
        ticking = true;
      }
    };

    // 只在不偏好減少動態效果的情況下啟用
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.addEventListener('scroll', handleScroll);
    }
  },

  /**
   * 設定動畫效果
   */
  setupAnimations: function() {
    // 檢查是否支援 Intersection Observer
    if (!('IntersectionObserver' in window)) {
      PD.debug.warn('瀏覽器不支援 Intersection Observer，跳過動畫設定');
      return;
    }

    PD.debug.log('✨ 設定滾動動畫');

    const animationElements = [
      { selector: '.hero-text', animation: 'slide-in-left' },
      { selector: '.hero-img', animation: 'slide-in-right' },
      { selector: '.news-title', animation: 'fade-in-up' },
      { selector: '.category-card', animation: 'bounce-in' },
      { selector: '.features-highlight .col-lg-4', animation: 'fade-in-up' }
    ];

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const element = entry.target;
          const animation = element.dataset.animation;
          
          setTimeout(() => {
            element.classList.add(animation);
          }, element.dataset.delay || 0);
          
          observer.unobserve(element);
        }
      });
    }, {
      threshold: this.config.intersectionThreshold,
      rootMargin: '0px 0px -50px 0px'
    });

    animationElements.forEach((item, index) => {
      const elements = document.querySelectorAll(item.selector);
      elements.forEach((element, elementIndex) => {
        element.dataset.animation = item.animation;
        element.dataset.delay = (index * this.config.animationDelay) + (elementIndex * 50);
        observer.observe(element);
      });
    });

    this.state.observers.push(observer);
  },

  /**
   * 設定觸控支援
   */
  setupTouchSupport: function() {
    const newsContainer = document.querySelector('.news-scroll-container .d-flex');
    if (!newsContainer) return;

    PD.debug.log('👆 設定觸控支援');

    newsContainer.addEventListener('touchstart', (e) => {
      this.state.touchStartX = e.touches[0].clientX;
    }, { passive: true });

    newsContainer.addEventListener('touchend', (e) => {
      this.state.touchEndX = e.changedTouches[0].clientX;
      this.handleTouchSwipe(newsContainer);
    }, { passive: true });
  },

  /**
   * 處理觸控滑動
   */
  handleTouchSwipe: function(container) {
    const deltaX = this.state.touchStartX - this.state.touchEndX;
    
    if (Math.abs(deltaX) > this.config.touchSensitivity) {
      if (deltaX > 0) {
        // 向左滑動，滾動到右邊
        this.scrollNews(container, 'right');
      } else {
        // 向右滑動，滾動到左邊
        this.scrollNews(container, 'left');
      }
    }
  },

  /**
   * 設定無障礙功能
   */
  setupAccessibility: function() {
    PD.debug.log('♿ 設定無障礙功能');

    // 為分類卡片添加適當的ARIA標籤
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach((card, index) => {
      const text = card.querySelector('.category-text')?.textContent;
      if (text) {
        card.setAttribute('aria-label', `前往${text}功能`);
        card.setAttribute('role', 'button');
      }
    });

    // 為新聞卡片添加適當的ARIA標籤
    const newsCards = document.querySelectorAll('.news-card:not(.more)');
    newsCards.forEach((card, index) => {
      card.setAttribute('aria-label', `閱讀第${index + 1}則新聞`);
    });

    // 為更多新聞按鈕添加標籤
    const moreCard = document.querySelector('.news-card.more');
    if (moreCard) {
      moreCard.setAttribute('aria-label', '查看更多新聞');
      moreCard.setAttribute('role', 'button');
    }
  },

  /**
   * 設定效能優化
   */
  setupPerformanceOptimization: function() {
    PD.debug.log('⚡ 設定效能優化');

    // 圖片懶加載
    const images = document.querySelectorAll('img[data-src]');
    if (images.length > 0 && 'IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
          }
        });
      });

      images.forEach(img => imageObserver.observe(img));
      this.state.observers.push(imageObserver);
    }

    // 節流滾動事件
    let scrollTimer;
    const throttledScroll = () => {
      if (scrollTimer) return;
      
      scrollTimer = setTimeout(() => {
        // 執行滾動相關邏輯
        this.updateScrollElements();
        scrollTimer = null;
      }, 16); // 約60fps
    };

    window.addEventListener('scroll', throttledScroll, { passive: true });
  },

  /**
   * 更新滾動相關元素
   */
  updateScrollElements: function() {
    // 可以在這裡添加其他需要隨滾動更新的邏輯
    // 例如：進度條、滾動指示器等
  },

  /**
   * 清理資源
   */
  cleanup: function() {
    PD.debug.log('🧹 清理首頁資源');

    // 清理觀察器
    this.state.observers.forEach(observer => {
      if (observer && observer.disconnect) {
        observer.disconnect();
      }
    });
    this.state.observers = [];

    // 停止自動滾動
    this.state.isAutoScrolling = false;

    // 重置狀態
    this.state.isInitialized = false;
  },

  /**
   * 調試用：顯示統計資訊
   */
  getStats: function() {
    return {
      initialized: this.state.isInitialized,
      observers: this.state.observers.length,
      autoScrolling: this.state.isAutoScrolling,
      newsCards: document.querySelectorAll('.news-card').length,
      categoryCards: document.querySelectorAll('.category-card').length
    };
  }
};

// 頁面卸載時清理資源
window.addEventListener('beforeunload', () => {
  window.PawDayHomepage.cleanup();
});

// 自動初始化
window.PawDayHomepage.init();

// 全局別名
window.Homepage = window.PawDayHomepage;