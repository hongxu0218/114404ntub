/* static/js/homepage.js - 首頁專用功能 */

// 安全保護：若 PD 未載入，提供最小的 debug 介面避免報錯
(function ensurePD() {
  if (!window.PD) {
    window.PD = {
      debug: {
        log:   function(){},
        warn:  function(){},
        error: function(){}
      }
    };
  } else if (!window.PD.debug) {
    window.PD.debug = { log(){}, warn(){}, error(){} };
  }
})();

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
 * 設定聊天機器人功能（/api/chat 串流 + 轉人工 handoff + 去重）
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

  // ---- 清理舊事件監聽：clone 節點再綁定，確保覆蓋舊功能 ----
  function replaceNode(el){
    if(!el) return el;
    const clone = el.cloneNode(true);
    if (el.parentNode) el.parentNode.replaceChild(clone, el);
    return clone;
  }
  closeBtn    = replaceNode(closeBtn);
  sendBtn     = replaceNode(sendBtn);
  input       = replaceNode(input);
  messagesDiv = replaceNode(messagesDiv);

  // ---- UI 調整：避免與回到頂部重疊 ----
  try {
    if (!btn.style.bottom) btn.style.bottom = '88px';
    if (!box.style.bottom) box.style.bottom = '160px';
  } catch(_) {}

  // ---- 常數與狀態 ----
  const STREAM_URL   = '/api/chat/stream/';      // 串流端點（Django）
  const HANDOFF_URL  = '/api/handoff/request/';  // 轉人工：建立/沿用工單
  const MESSAGE_URL  = '/api/handoff/message/';  // 轉人工後，使用者發訊息給座席
  const POLL_URL     = '/api/handoff/poll/';     // 輪詢座席/系統訊息

  const history = []; // 只在前端保存，後端僅取最近 6 則
  let busy = false;
  let lastUserText = ''; // 記錄最後一次提問，提交轉人工用
  let inHandoff = false; // 是否已轉人工
  let lastMsgId = 0;     // 追蹤最後一則訊息 ID（避免重覆）
  let pollTimer = null;
  let ticketId = null;   // 保存工單 id

  // === 去重與暫存 ===
  const displayedIds = new Set();        // 已顯示過的伺服器訊息 id
  const pendingBySig = new Map();        // 暫存中的本地 user 泡泡：key=指紋, val=DOM
  const makeSig = (sender, text) => sender + '|' + (text || '').trim();

  // ---- 泡泡小工具 ----
  // （保留原本 addBubble：給串流時逐段推文字用）
  const addBubble = (sender, textOrHtml, asHTML = false) => {
    const msgDiv = document.createElement("div");
    msgDiv.className = 'cb-bubble ' + (sender === 'user' ? 'cb-user' : 'cb-bot');
    if (asHTML) msgDiv.innerHTML = textOrHtml;
    else msgDiv.textContent = textOrHtml;
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return msgDiv;
  };

  // 新版通用輸出（支援 id / 暫存 / 升級）
  function appendMsg(sender, text, { id=null, ts=null, temp=false, asHTML=false, upgradeTarget=null } = {}) {
    // 升級暫存：補上 id/time，不再新增第二顆
    if (upgradeTarget) {
      upgradeTarget.removeAttribute('data-temp');
      if (id != null) {
        upgradeTarget.dataset.id = String(id);
        displayedIds.add(id);
      }
      if (ts) {
        const timeEl = upgradeTarget.querySelector('.cb-time');
        if (timeEl) timeEl.textContent = new Date(ts).toLocaleString();
        else upgradeTarget.insertAdjacentHTML('beforeend', `<div class="cb-time">${new Date(ts).toLocaleString()}</div>`);
      }
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      return upgradeTarget;
    }

    // 正式 id 已出現過 → 直接略過
    if (id != null && displayedIds.has(id)) return null;

    const div = document.createElement('div');
    div.className = 'cb-bubble ' + (sender === 'user' ? 'cb-user' : 'cb-bot');
    if (id != null) {
      div.dataset.id = String(id);
      displayedIds.add(id);
    }
    if (temp) div.dataset.temp = '1';

    if (asHTML) div.innerHTML = text || '';
    else div.textContent = text || '';

    if (ts) {
      div.insertAdjacentHTML('beforeend', `<div class="cb-time">${new Date(ts).toLocaleString()}</div>`);
    }
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return div;
  }

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

  // ✅ 將回覆中的「【轉人工客服】/轉人工客服」替換成可點擊的內嵌按鈕
  function injectHandoffButton(botDiv){
    if (!botDiv) return;
    if (botDiv.querySelector('[data-action="handoff"]')) return; // 已替換過就不重複
    const textNow = (botDiv.innerText || '').trim();
    if (!textNow.includes('轉人工客服')) return;

    let html = botDiv.innerHTML;
    // 1) 【轉人工客服】 → button
    html = html.replace(
      /【\s*轉人工客服\s*】/g,
      '<button class="cb-inline-btn" data-action="handoff" type="button">轉人工客服</button>'
    );
    // 2) 若沒有全形括號版本，退而求其次替換單獨文字（僅第一個）
    if (!/data-action="handoff"/.test(html)) {
      html = html.replace(
        /轉人工客服(?![^<]*>)/,
        '<button class="cb-inline-btn" data-action="handoff" type="button">轉人工客服</button>'
      );
    }
    botDiv.innerHTML = html;
  }

  // ---- 狀態碼對應的明確提示 ----
  const STATUS_HINT = {
    400: "欄位有誤，請確認必填內容（例如：訊息不可為空）。",
    401: "需要登入才能提交，請先登入後再試。",
    403: "沒有操作權限（僅限客服/管理員）。",
    404: "找不到資源，服務暫時不可用。",
    409: "目前無法建立新工單，請稍後再試。",
    413: "內容過大，請精簡後再送出。",
    429: "操作過於頻繁，請稍後再試。",
    500: "系統暫時異常，請稍後再試或改用其他聯絡方式。"
  };

  // ---- 通用 JSON POST（含 CSRF、非 JSON/被轉導偵測）----
  async function apiPost(endpoint, payload) {
    const headers = { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" };
    const csrftoken = getCSRFToken();
    if (csrftoken) headers["X-CSRFToken"] = csrftoken;

    const res = await fetch(endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(payload || {}),
      credentials: "same-origin"
    });

    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      throw { status: res.status || 500, message: null };
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw { status: res.status || 500, message: data.error || null };
    }
    return data; // 正常回傳 JSON
  }

  // ---- 統一顯示錯誤 ----
  function showSubmitError(status, fallbackMsg) {
    addBubble('bot', `❌ ${STATUS_HINT[status] || fallbackMsg || STATUS_HINT[500]}`);
  }

  // ---- 顯示「轉人工客服」CTA（按鈕沿用委派事件）----
  function showHandoffCTA(lastQuestion) {
    const html = `
      <div>
        目前找不到合適的答案。要不要改由<strong>人工客服</strong>協助？
        <div class="mt-2" style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="cb-inline-btn" data-action="handoff" type="button">轉人工客服</button>
          <button class="cb-inline-btn" data-action="ask-again" type="button">我再問一次</button>
        </div>
      </div>`;
    const div = addBubble('bot', html, true);
    messagesDiv.addEventListener('click', (e) => {
      if (e.target && e.target.matches('[data-action="ask-again"]')) {
        input.focus();
      }
    }, { once: true });
    return div;
  }

// ✅ 送出人工客服請求（不跳視窗）—— 直接建立/沿用工單
const submitHandoff = async () => {
  // 1) 盡量從現有資料自動帶入（依你網站情況擇一會拿到）
  const nameFromDom =
    (document.getElementById('handoff-name')?.value || '').trim() ||
    (document.querySelector('[data-handoff-name]')?.getAttribute('data-handoff-name') || '').trim();

  const contactFromDom =
    (document.getElementById('handoff-contact')?.value || '').trim() ||
    (document.querySelector('[data-handoff-contact]')?.getAttribute('data-handoff-contact') || '').trim();

  const nameFromApp =
    (window.PD?.user?.displayName || window.PD?.user?.name || '').trim();

  const contactFromApp =
    (window.PD?.user?.email || window.PD?.user?.phone || window.PD?.user?.mobile || '').trim();

  // 2) 取用「DOM > 應用狀態 > 預設值」
  const name = nameFromDom || nameFromApp || '匿名';
  const contact = contactFromDom || contactFromApp || '';

  try {
    const data = await apiPost(HANDOFF_URL, {
      name,
      contact,
      last_question: lastUserText || '',
      channel: 'web'
    });
    ticketId  = data.ticket_id;
    lastMsgId = 0;
    inHandoff = true;

    addBubble('bot', `✅ 已建立人工客服工單（#${ticketId}）。此後可直接在這裡與座席互動。`);
    shownHandoffBanner = true; // 避免之後 poll 到相同 system 訊息再顯示一次
    startPolling();
  } catch (e) {
    showSubmitError(e.status, e.message);
  }
};

  // === 轉人工後把訊息送到座席（帶 ticket_id），含暫存泡泡 ===
  const sendToAgent = async (text) => {
    if (!ticketId) {
      showHandoffCTA(lastUserText);
      return;
    }

    // 先插入暫存 user 泡泡（立即回饋）
    const signature = makeSig('user', text);
    const tempNode = appendMsg('user', text, { temp: true });
    pendingBySig.set(signature, tempNode);

    try {
      await apiPost(MESSAGE_URL, { ticket_id: ticketId, message: text });
      // 正式 id/時間等，留待下一輪 poll 升級暫存泡泡
    } catch (e) {
      // 發送失敗：移除暫存泡泡 + 顯示錯誤
      if (tempNode && tempNode.parentNode) tempNode.parentNode.removeChild(tempNode);
      pendingBySig.delete(signature);
      showSubmitError(e.status, e.message);
    }
  };

  // === 轉人工後輪詢座席/系統/使用者訊息（去重＋暫存升級） ===
  const pollOnce = async () => {
    if (!inHandoff || !ticketId) return;
    try {
      const r = await fetch(`${POLL_URL}?ticket_id=${ticketId}&since=${lastMsgId || 0}`, {
        cache: 'no-store',
        credentials: 'same-origin'
      });
      if (r.status === 401 || r.status === 403) {
        showSubmitError(r.status);
        stopPolling();
        inHandoff = false;
        return;
      }
      if (!r.ok) return;

      const data = await r.json().catch(() => ({}));
      if (!Array.isArray(data?.messages)) {
        if (typeof data?.last_id === 'number') lastMsgId = data.last_id;
        return;
      }

      for (const m of data.messages) {
        // 去重：伺服器 id
        if (m.id != null && displayedIds.has(m.id)) {
          lastMsgId = Math.max(lastMsgId, m.id);
          continue;
        }

        const isUser = (m.sender === 'user');
        const signature = makeSig(m.sender, m.text);
        const maybeTemp = pendingBySig.get(signature);

        if (isUser && maybeTemp && maybeTemp.dataset.temp === '1') {
          // 升級暫存 user 泡泡 → 補 id/time
          appendMsg('user', m.text, { id: m.id, ts: m.ts, upgradeTarget: maybeTemp });
          pendingBySig.delete(signature);
        } else {
          // 直接新增（agent/system 或是沒有對應暫存）
          appendMsg(isUser ? 'user' : 'bot', m.text, { id: m.id, ts: m.ts });
        }

        if (m.id != null) lastMsgId = Math.max(lastMsgId, m.id);

        // 工單結案 UX
        if (/工單已結案/.test(m.text)) {
          inHandoff = false;
          stopPolling();
        }
      }
    } catch (_) {}
  };
  const startPolling = () => { stopPolling(); pollOnce(); pollTimer = setInterval(pollOnce, 2000); };
  const stopPolling  = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };

  // ---- 串流呼叫：逐行解析 NDJSON（meta / delta / done / error）----
  async function askRAGStream(message, historyArr) {
    const headers = { "Content-Type": "application/json" };
    const csrftoken = getCSRFToken();
    if (csrftoken) headers["X-CSRFToken"] = csrftoken;

    const res = await fetch(STREAM_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({ message, history: historyArr }),
      credentials: 'same-origin'
    });
    if (!res.ok || !res.body) throw new Error("stream response error");

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    // 回傳 async 迭代器
    return {
      async *[Symbol.asyncIterator]() {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              yield JSON.parse(line);
            } catch {
              yield { type: "delta", text: line };
            }
          }
        }
        if (buffer.trim()) {
          try { yield JSON.parse(buffer); } catch { yield { type: "delta", text: buffer }; }
        }
      }
    };
  }

  // ---- 送出訊息（串流版；handoff 模式則改送座席）----
  const sendMessageStream = async () => {
    const text = input.value.trim();
    if (!text || busy) return;

    // 若已轉人工：改為送給座席
    if (inHandoff){
      input.value = '';
      return sendToAgent(text);
    }

    busy = true;
    input.value = '';
    sendBtn.setAttribute('disabled', 'disabled');

    // 使用者泡泡
    addBubble('user', text);
    lastUserText = text;

    // 機器人泡泡（會持續追加）
    const botDiv = addBubble('bot', '<em>輸入中…</em>', true);

    try {
      const stream = await askRAGStream(text, history.slice(-6)); // 傳最近 6 則上下文
      let started = false;
      let sourcesHTML = "";

      for await (const evt of stream) {
        if (evt.type === "meta") {
          const srcList = (evt.sources || []).map(s => `<li>${(s.source || '來源')}</li>`).join("");
          if (srcList) sourcesHTML = `<details class="cb-sources"><summary>來源</summary><ul>${srcList}</ul></details>`;
        } else if (evt.type === "delta") {
          const piece = (evt.text || "").replace(/\n/g, "<br>");
          if (!started) {
            botDiv.innerHTML = piece;
            started = true;
          } else {
            botDiv.innerHTML += piece;
          }
          messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } else if (evt.type === "error") {
          botDiv.textContent = evt.message || "發生錯誤";
        } else if (evt.type === "done") {
          if (sourcesHTML) botDiv.innerHTML += sourcesHTML;

          // 若模型回覆語句顯示「找不到」或「沒有找到」，改為給 CTA
          const contentText = botDiv.textContent || botDiv.innerText || "";
          if (/目前知識庫沒有找到相關資訊|找不到合適的答案|無法找到|沒有找到/.test(contentText)) {
            showHandoffCTA(lastUserText);
          } else {
            // 仍保留「把文字轉成可點擊的轉人工客服按鈕」
            injectHandoffButton(botDiv);
          }
        }
      }

      // 更新前端歷史（用於下次串流）
      history.push(
        { role: 'user', content: text },
        { role: 'assistant', content: (botDiv.textContent || botDiv.innerText || '') }
      );
    } catch (err) {
      botDiv.textContent = '連線失敗，請確認 /api/chat/stream 是否可用，以及本機 Ollama 是否啟動';
      (window.PD?.debug?.error || console.error)(err);
    } finally {
      busy = false;
      sendBtn.removeAttribute('disabled');
      input.focus();
    }
  };

  // ---- 事件 ----
  btn.addEventListener("click", () => {
    if (box.style.display === 'flex') closeBox(); else openBox();
  });
  closeBtn.addEventListener("click", closeBox);
  sendBtn.addEventListener("click", sendMessageStream);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessageStream(); } // Enter 送出
    if (e.key === "Escape") closeBox();
  });

  // ✅ 在訊息區委派事件 → 點擊「轉人工客服」或「我再問一次」
  messagesDiv.addEventListener('click', (e) => {
    const t = e.target;
    if (t && t.matches('[data-action="handoff"]')) {
      submitHandoff();
    }
    if (t && t.matches('[data-action="ask-again"]')) {
      input.focus();
    }
  });

  // 鍵盤快速開啟：Alt + /
  window.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === '/') {
      if (box.style.display === 'flex') closeBox(); else openBox();
    }
  });
},


  /**
   * 設定首頁「新聞水平滾動」功能
   * 需求的 DOM：
   *  - 容器：.news-scroll-container .d-flex
   *  - 左鍵：#news-left（可選）
   *  - 右鍵：#news-right（可選）
   */
  setupNewsScroll: function () {
    const container = document.querySelector('.news-scroll-container .d-flex');
    if (!container) {
      PD.debug.warn('找不到新聞容器 .news-scroll-container .d-flex，跳過 setupNewsScroll');
      return;
    }

    const leftBtn  = document.getElementById('news-left');
    const rightBtn = document.getElementById('news-right');

    PD.debug.log('📰 設定新聞水平滾動');

    if (leftBtn) {
      leftBtn.addEventListener('click', () => {
        this.scrollNews(container, 'left');
        setTimeout(() => this.updateScrollButtons(container, leftBtn, rightBtn), 300);
      });
    }
    if (rightBtn) {
      rightBtn.addEventListener('click', () => {
        this.scrollNews(container, 'right');
        setTimeout(() => this.updateScrollButtons(container, leftBtn, rightBtn), 300);
      });
    }

    // 初始化按鈕狀態
    if (leftBtn || rightBtn) {
      this.updateScrollButtons(container, leftBtn, rightBtn);
    }

    // 監聽捲動（節流更新）
    let btnTimer = null;
    container.addEventListener('scroll', () => {
      if (!leftBtn && !rightBtn) return;
      if (btnTimer) return;
      btnTimer = setTimeout(() => {
        this.updateScrollButtons(container, leftBtn, rightBtn);
        btnTimer = null;
      }, 100);
    }, { passive: true });

    // 視窗尺寸改變
    window.addEventListener('resize', () => {
      if (leftBtn || rightBtn) {
        this.updateScrollButtons(container, leftBtn, rightBtn);
      }
    });

    // 啟用自動滾動
    this.setupAutoScroll(container);

    // 鍵盤左右鍵支援（容器聚焦時）
    if (!container.hasAttribute('tabindex')) container.setAttribute('tabindex', '0');
    container.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        this.scrollNews(container, 'left');
      } else if (e.key === 'ArrowRight') {
        this.scrollNews(container, 'right');
      }
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
    if (!container) return;
    const scrollLeft = container.scrollLeft;
    const maxScroll = container.scrollWidth - container.clientWidth;

    if (leftBtn) {
      leftBtn.style.opacity = scrollLeft > 0 ? '1' : '0.5';
      leftBtn.disabled = scrollLeft <= 0;
    }
    if (rightBtn) {
      rightBtn.style.opacity = scrollLeft < maxScroll ? '1' : '0.5';
      rightBtn.disabled = scrollLeft >= maxScroll;
    }
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