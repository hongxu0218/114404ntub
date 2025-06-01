/**
 * PAW&DAY 寵物列表頁面互動功能
 * 提供優雅的用戶體驗與流暢的動畫效果
 */

// 全域變數
let currentOpenPet = null;
let animationInProgress = false;

/**
 * 頁面載入完成後初始化
 */
document.addEventListener("DOMContentLoaded", function() {
  initializePage();
  setupEventListeners();
  handleMessages();
  setupAnimations();
});

/**
 * 初始化頁面
 */
function initializePage() {
  // 檢查 URL 中是否有指定要展開的寵物
  const urlParams = new URLSearchParams(window.location.search);
  const openPetId = urlParams.get('open');
  
  if (openPetId) {
    setTimeout(() => {
      togglePetDetails(parseInt(openPetId));
      scrollToPet(openPetId);
    }, 500);
  }

  // 設置 ARIA 屬性提升無障礙性
  setupAccessibility();
}

/**
 * 設置事件監聽器
 */
function setupEventListeners() {
  // 取消預約確認
  setupCancelConfirmation();
    
  // 鍵盤導航支援
  setupKeyboardNavigation();
  
  // 圖片載入錯誤處理
  setupImageErrorHandling();
}

/**
 * 寵物詳細資訊切換（主要功能）
 */
function togglePetDetails(petId) {
  if (animationInProgress) return;
  
  animationInProgress = true;
  
  const details = document.getElementById(`details-${petId}`);
  const header = details.previousElementSibling;
  const icon = document.getElementById(`toggle-${petId}`);
  const petCard = details.closest('.pet-card');
  
  // 如果當前寵物已展開，則收合
  if (details.classList.contains('show')) {
    closePetDetails(petId, details, header, icon);
    currentOpenPet = null;
  } else {
    // 先關閉其他已展開的寵物
    if (currentOpenPet && currentOpenPet !== petId) {
      const otherDetails = document.getElementById(`details-${currentOpenPet}`);
      const otherHeader = otherDetails.previousElementSibling;
      const otherIcon = document.getElementById(`toggle-${currentOpenPet}`);
      
      closePetDetails(currentOpenPet, otherDetails, otherHeader, otherIcon);
    }
    
    // 展開當前寵物
    openPetDetails(petId, details, header, icon, petCard);
    currentOpenPet = petId;
  }
  
  // 動畫完成後重置標記
  setTimeout(() => {
    animationInProgress = false;
  }, 400);
}

/**
 * 展開寵物詳情
 */
function openPetDetails(petId, details, header, icon, petCard) {
  details.classList.add('show');
  header.classList.add('expanded');
  
  // 圖標旋轉動畫
  icon.style.transform = 'rotate(180deg)';
  
  // 卡片輕微放大效果
  petCard.style.transform = 'translateY(-12px) scale(1.02)';
  
  // 更新 ARIA 屬性
  header.setAttribute('aria-expanded', 'true');
  details.setAttribute('aria-hidden', 'false');
  
  // 滾動到視窗中央
  setTimeout(() => {
    scrollToPet(petId);
    petCard.style.transform = 'translateY(-8px) scale(1)';
  }, 200);
  
  // 觸發進入動畫
  animateDetailsContent(details);
}

/**
 * 收合寵物詳情
 */
function closePetDetails(petId, details, header, icon) {
  details.classList.remove('show');
  header.classList.remove('expanded');
  
  // 圖標復原
  icon.style.transform = 'rotate(0deg)';
  
  // 更新 ARIA 屬性
  header.setAttribute('aria-expanded', 'false');
  details.setAttribute('aria-hidden', 'true');
}

/**
 * 特徵文字展開/收合
 */
function toggleFeature(petId) {
  const feature = document.getElementById(`feature-${petId}`);
  const toggleText = document.getElementById(`toggle-text-${petId}`);
  
  if (!feature || !toggleText) return;
  
  if (feature.classList.contains('collapsed')) {
    // 展開
    feature.classList.remove('collapsed');
    toggleText.textContent = '收合';
    
    // 添加展開動畫
    feature.style.maxHeight = feature.scrollHeight + 'px';
    
    // 滾動調整
    setTimeout(() => {
      feature.style.maxHeight = 'none';
    }, 300);
    
  } else {
    // 收合
    feature.style.maxHeight = feature.scrollHeight + 'px';
    
    // 強制重繪
    feature.offsetHeight;
    
    feature.classList.add('collapsed');
    toggleText.textContent = '展開';
    feature.style.maxHeight = '';
  }
}

/**
 * 滾動到指定寵物
 */
function scrollToPet(petId) {
  const petCard = document.querySelector(`#details-${petId}`).closest('.pet-card');
  
  if (petCard) {
    petCard.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
}

/**
 * 詳情內容進入動畫
 */
function animateDetailsContent(details) {
  const sections = details.querySelectorAll('.pet-info-section, .appointment-section');
  
  sections.forEach((section, index) => {
    section.style.opacity = '0';
    section.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      section.style.transition = 'all 0.3s ease';
      section.style.opacity = '1';
      section.style.transform = 'translateY(0)';
    }, index * 50);
  });
}

/**
 * 設置無障礙功能
 */
function setupAccessibility() {
  const headers = document.querySelectorAll('.pet-card-header');
  
  headers.forEach(header => {
    header.setAttribute('role', 'button');
    header.setAttribute('tabindex', '0');
    header.setAttribute('aria-expanded', 'false');
    
    const details = header.nextElementSibling;
    if (details) {
      details.setAttribute('aria-hidden', 'true');
    }
  });
}

/**
 * 鍵盤導航支援
 */
function setupKeyboardNavigation() {
  const headers = document.querySelectorAll('.pet-card-header');
  
  headers.forEach(header => {
    header.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const petId = this.onclick.toString().match(/togglePetDetails\((\d+)\)/)[1];
        togglePetDetails(parseInt(petId));
      }
    });
  });
  
  // 功能按鈕鍵盤支援
  const toggleBtns = document.querySelectorAll('.toggle-feature-btn');
  toggleBtns.forEach(btn => {
    btn.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        this.click();
      }
    });
  });
}

/**
 * 取消預約確認對話框
 */
function setupCancelConfirmation() {
  const cancelBtns = document.querySelectorAll('.cancel-appointment-btn');
  
  cancelBtns.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      
      const appointmentInfo = this.closest('.appointment-item').querySelector('.appointment-datetime strong').textContent;
      
      if (showCustomConfirm(
        '取消預約確認',
        `確定要取消 ${appointmentInfo} 的預約嗎？\n獸醫將會收到取消通知。`,
        '確定取消',
        '保留預約'
      )) {
        this.closest('form').submit();
      }
    });
  });
}

/**
 * 自定義確認對話框
 */
function showCustomConfirm(title, message, confirmText, cancelText) {
  return confirm(`${title}\n\n${message}`);
  
  // 未來可以實作自定義的美觀對話框
  // 目前使用瀏覽器原生 confirm
}

/**
 * 圖片載入錯誤處理
 */
function setupImageErrorHandling() {
  const images = document.querySelectorAll('.pet-image, .add-pet-icon');
  
  images.forEach(img => {
    img.addEventListener('error', function() {
      // 如果是寵物圖片載入失敗
      if (this.classList.contains('pet-image')) {
        const container = this.parentElement;
        const placeholder = document.createElement('div');
        placeholder.className = 'no-image-placeholder';
        placeholder.innerHTML = '<i class="bi bi-image"></i>';
        
        container.replaceChild(placeholder, this);
        
        const errorText = document.createElement('p');
        errorText.className = 'text-muted mt-2';
        errorText.textContent = '圖片載入失敗';
        container.appendChild(errorText);
      }
      
      // 如果是圖標載入失敗
      if (this.classList.contains('add-pet-icon')) {
        this.style.display = 'none';
        const iconFallback = document.createElement('i');
        iconFallback.className = 'bi bi-plus-circle';
        iconFallback.style.fontSize = '4rem';
        iconFallback.style.color = 'var(--primary-orange)';
        this.parentElement.insertBefore(iconFallback, this.nextSibling);
      }
    });
  });
}

/**
 * 訊息處理
 */
function handleMessages() {
  const msgContainer = document.getElementById('message-container');
  
  if (msgContainer) {
    // 添加關閉按鈕
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '<i class="bi bi-x"></i>';
    closeBtn.className = 'btn-close-message';
    closeBtn.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255,255,255,0.2);
      border: none;
      color: inherit;
      padding: 5px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.9rem;
    `;
    
    msgContainer.style.position = 'relative';
    msgContainer.appendChild(closeBtn);
    
    // 點擊關閉
    closeBtn.addEventListener('click', () => {
      hideMessage(msgContainer);
    });
    
    // 自動消失
    setTimeout(() => {
      hideMessage(msgContainer);
    }, 5000);
  }
}

/**
 * 隱藏訊息
 */
function hideMessage(msgContainer) {
  msgContainer.style.transition = 'all 0.5s ease';
  msgContainer.style.opacity = '0';
  msgContainer.style.transform = 'translateX(100%)';
  
  setTimeout(() => {
    if (msgContainer.parentNode) {
      msgContainer.remove();
    }
  }, 500);
}

/**
 * 設置載入動畫
 */
function setupAnimations() {
  const elements = document.querySelectorAll('.fade-in-up');
  
  // 使用 Intersection Observer 來觸發動畫
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, index * 100);
        
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '50px'
  });
  
  elements.forEach(el => {
    observer.observe(el);
  });
}

/**
 * 實用工具函數
 */

// 防抖函數
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 節流函數
function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// 平滑滾動到頂部
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

// 添加到收藏夾（未來功能）
function addToFavorites(petId) {
  // 實作收藏功能
  console.log(`Adding pet ${petId} to favorites`);
}

// 分享寵物資訊（未來功能）
function sharePetInfo(petId) {
  if (navigator.share) {
    navigator.share({
      title: 'PAW&DAY - 我的毛孩',
      text: '快來看看我可愛的毛孩！',
      url: `${window.location.origin}${window.location.pathname}?open=${petId}`
    });
  } else {
    // 降級處理：複製到剪貼簿
    const url = `${window.location.origin}${window.location.pathname}?open=${petId}`;
    navigator.clipboard.writeText(url).then(() => {
      showToast('連結已複製到剪貼簿');
    });
  }
}

// 顯示提示訊息
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast-message toast-${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--text-dark);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    z-index: 10000;
    animation: slideInUp 0.3s ease;
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// 導出全域函數（供 HTML 內聯使用）
window.togglePetDetails = togglePetDetails;
window.toggleFeature = toggleFeature;