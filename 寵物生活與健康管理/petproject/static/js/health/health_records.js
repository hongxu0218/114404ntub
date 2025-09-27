/**
 * 健康紀錄管理 - 飼主專用
 * 現代化、簡潔的用戶體驗
 */

class HealthRecordsController {
    constructor() {
        this.currentTab = this.getCurrentTab();
        this.init();
    }

    init() {
        // console.log('🏥 健康紀錄系統初始化...');
        
        this.setupEventListeners();
        this.updateActiveTab();
        this.setupAnimations();
        
        // 顯示當前標籤的內容
        this.showTabContent(this.currentTab);
        
        // console.log('✅ 健康紀錄系統已就緒');
    }

    getCurrentTab() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('tab') || 'medical';
    }

    showTabContent(tabName) {
        // 隱藏所有標籤內容
        document.querySelectorAll('.health-tab-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // 顯示選定的標籤內容
        const targetContent = document.querySelector(`[data-tab="${tabName}"]`);
        if (targetContent) {
            targetContent.style.display = 'block';
        }
        
        // 更新標題
        this.updateContentTitle(tabName);
        
        // 更新活動標籤
        document.querySelectorAll('.health-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`.health-tab[href*="tab=${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
    }
    
    updateContentTitle(tabName) {
        const titleElement = document.querySelector('.health-content-title');
        if (!titleElement) return;
        
        const titles = {
            'medical': '<i class="fas fa-stethoscope"></i> 看診紀錄',
            'vaccine': '<i class="fas fa-syringe"></i> 疫苗記錄',
            'deworm': '<i class="fas fa-shield-alt"></i> 驅蟲記錄',
            'report': '<i class="fas fa-file-medical-alt"></i> 檢驗報告',
            'daily': '<i class="fas fa-calendar-day"></i> 生活記錄'
        };
        
        titleElement.innerHTML = titles[tabName] || titles['medical'];
        
        // 控制新增按鈕顯示
        const addButton = document.querySelector('.health-add-btn');
        if (addButton) {
            addButton.style.display = tabName === 'daily' ? 'flex' : 'none';
        }
    }

    setupEventListeners() {
        // 使用事件委託處理點擊
        document.addEventListener('click', (e) => {
            // 處理記錄卡片點擊
            const recordCard = e.target.closest('.health-record-card');
            if (recordCard && !e.target.closest('.health-record-actions')) {
                this.handleRecordClick(recordCard);
            }

            // 處理操作按鈕點擊
            const actionBtn = e.target.closest('.health-action-btn');
            if (actionBtn) {
                e.preventDefault();
                e.stopPropagation();
                this.handleActionClick(actionBtn);
            }

            // 處理生活記錄篩選按鈕
            const filterBtn = e.target.closest('.daily-filter-btn');
            if (filterBtn) {
                e.preventDefault();
                this.handleDailyFilter(filterBtn);
            }

            // 處理生活記錄編輯按鈕
            const editDailyBtn = e.target.closest('.edit-daily-btn');
            if (editDailyBtn) {
                e.preventDefault();
                e.stopPropagation();
                this.handleEditDaily(editDailyBtn);
            }

            // 處理生活記錄刪除按鈕
            const deleteDailyBtn = e.target.closest('.delete-daily-btn');
            if (deleteDailyBtn) {
                e.preventDefault();
                e.stopPropagation();
                this.handleDeleteDaily(deleteDailyBtn);
            }
        });

        // 處理標籤切換
        document.querySelectorAll('.health-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleTabClick(e, tab);
            });
        });
    }

    handleRecordClick(card) {
        // 添加點擊效果
        card.style.transform = 'scale(0.98)';
        setTimeout(() => {
            card.style.transform = '';
        }, 150);

        // 這裡可以添加展開詳情的邏輯
        // console.log('記錄卡片被點擊:', card);
    }

    handleActionClick(button) {
        const icon = button.querySelector('i');
        const card = button.closest('.health-record-card');
        
        if (icon) {
            if (icon.classList.contains('fa-eye')) {
                this.viewRecord(card);
            } else if (icon.classList.contains('fa-edit')) {
                this.editRecord(card);
            } else if (icon.classList.contains('fa-download')) {
                this.downloadReport(button);
            }
        }
    }

    viewRecord(card) {
        // 查看記錄詳情
        // console.log('查看記錄:', card);
        
        // 添加視覺反饋
        const button = card.querySelector('.health-action-btn');
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            // 這裡可以打開模態窗口或跳轉到詳情頁
        }, 500);
    }

    editRecord(card) {
        // 編輯記錄
        // console.log('編輯記錄:', card);
        
        // 添加編輯邏輯
        this.showNotification('編輯功能開發中...', 'info');
    }

    downloadReport(button) {
        // 下載報告
        // console.log('下載報告:', button.href);
        
        // 添加下載反饋
        this.showNotification('開始下載報告...', 'success');
    }

    handleTabClick(e, tab) {
        // 從href獲取標籤名稱
        const href = tab.getAttribute('href');
        const tabName = href ? href.split('tab=')[1] : 'medical';
        
        // 如果是當前標籤，不需要切換
        if (tab.classList.contains('active')) {
            return;
        }

        // 顯示對應的標籤內容
        this.showTabContent(tabName);
        
        // 添加切換動畫
        this.addTabSwitchAnimation(tab);
    }

    addTabSwitchAnimation(tab) {
        // 移除所有活動狀態
        document.querySelectorAll('.health-tab').forEach(t => {
            t.classList.remove('active');
        });

        // 添加活動狀態
        tab.classList.add('active');

        // 添加切換動畫
        tab.style.transform = 'scale(0.95)';
        setTimeout(() => {
            tab.style.transform = '';
        }, 200);
    }

    updateActiveTab() {
        // 確保正確的標籤處於活動狀態
        const activeTab = document.querySelector(`.health-tab[href*="tab=${this.currentTab}"]`);
        if (activeTab) {
            document.querySelectorAll('.health-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            activeTab.classList.add('active');
        }
    }

    setupAnimations() {
        // 卡片進入動畫
        this.animateCards();
        
        // 滾動動畫
        this.setupScrollAnimations();
    }

    animateCards() {
        const cards = document.querySelectorAll('.health-record-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }

    setupScrollAnimations() {
        // 滾動時的視差效果
        let ticking = false;
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    this.handleScroll();
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    handleScroll() {
        const scrollY = window.scrollY;
        const header = document.querySelector('.health-header');
        
        if (header) {
            // 添加視差效果
            const parallax = scrollY * 0.5;
            header.style.transform = `translateY(${parallax}px)`;
            
            // 添加模糊效果
            if (scrollY > 100) {
                header.style.filter = `blur(${Math.min(scrollY / 200, 2)}px)`;
                header.style.opacity = Math.max(1 - scrollY / 500, 0.3);
            } else {
                header.style.filter = 'blur(0px)';
                header.style.opacity = 1;
            }
        }
    }

    showNotification(message, type = 'info') {
        // 創建通知
        const notification = document.createElement('div');
        notification.className = `health-notification health-${type}`;
        notification.innerHTML = `
            <div class="health-notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;

        // 添加樣式
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        document.body.appendChild(notification);

        // 動畫進入
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);

        // 自動消失
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    getNotificationColor(type) {
        const colors = {
            'success': '#4caf50',
            'error': '#f44336',
            'warning': '#ff9800',
            'info': '#2196f3'
        };
        return colors[type] || '#2196f3';
    }

    // ===============================
    // 生活記錄專用方法
    // ===============================

    handleDailyFilter(button) {
        const category = button.dataset.category;
        
        // 更新按鈕狀態
        document.querySelectorAll('.daily-filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        // 篩選卡片
        this.filterDailyRecords(category);
        
        // 添加按鈕動畫
        button.style.transform = 'scale(0.95)';
        setTimeout(() => {
            button.style.transform = '';
        }, 150);
    }

    filterDailyRecords(category) {
        const cards = document.querySelectorAll('.daily-record-card');
        let visibleCount = 0;

        cards.forEach((card, index) => {
            const cardCategory = card.dataset.category;
            const shouldShow = category === 'all' || cardCategory === category;
            
            if (shouldShow) {
                card.classList.remove('hidden');
                card.classList.add('show');
                // 錯開動畫
                card.style.animationDelay = `${index * 0.1}s`;
                visibleCount++;
            } else {
                card.classList.add('hidden');
                card.classList.remove('show');
            }
        });

        // 如果沒有符合的記錄，顯示空狀態
        const container = document.querySelector('.daily-records-container');
        const emptyState = document.querySelector('.health-empty-state');
        
        if (visibleCount === 0 && container && !emptyState) {
            this.showEmptyState(container, category);
        } else if (visibleCount > 0 && emptyState) {
            emptyState.remove();
        }
    }

    showEmptyState(container, category) {
        const categoryNames = {
            'diet': '飲食記錄',
            'exercise': '運動記錄', 
            'allergen': '過敏記錄',
            'other': '其他記錄'
        };

        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'health-empty-state';
        emptyDiv.innerHTML = `
            <div class="health-empty-icon">
                <i class="fas fa-search"></i>
            </div>
            <h3 class="health-empty-title">找不到${categoryNames[category] || '記錄'}</h3>
            <p class="health-empty-description">
                目前沒有符合條件的生活記錄<br>
                試試其他分類或新增記錄
            </p>
        `;
        
        container.parentNode.appendChild(emptyDiv);
    }

    handleEditDaily(button) {
        const recordId = button.dataset.recordId;
        const card = button.closest('.daily-record-card');

        if (!card) return;

        // 獲取記錄類型
        const category = card.dataset.category;

        // 根據不同類型創建不同的編輯表單
        if (['temperature', 'weight', 'exercise'].includes(category)) {
            this.showDataEditForm(card, recordId, category);
        } else {
            // 文字內容記錄
            const contentP = card.querySelector('.daily-record-content p, .record-text');
            const currentContent = contentP ? contentP.textContent.trim() : '';
            this.showContentEditForm(card, recordId, currentContent);
        }

        this.showNotification('編輯模式已啟動', 'info');
    }

    showDataEditForm(card, recordId, category) {
        const contentDiv = card.querySelector('.daily-record-content');
        const actionsDiv = card.querySelector('.daily-record-actions');

        // 獲取當前數值
        const valueSpan = card.querySelector('.record-value .value');
        let currentValue = '';
        if (valueSpan) {
            const text = valueSpan.textContent;
            if (category === 'temperature') {
                currentValue = text.replace('°C', '').trim();
            } else if (category === 'weight') {
                currentValue = text.replace('kg', '').trim();
            } else if (category === 'exercise') {
                currentValue = text.replace('分鐘', '').trim();
            }
        }

        // 保存原始內容
        card.dataset.originalValue = currentValue;

        const config = this.getDataEditConfig(category);

        // 創建數值編輯表單
        contentDiv.innerHTML = `
            <div class="data-edit-form">
                <label class="data-edit-label">${config.label}</label>
                <div class="data-input-group">
                    <input type="number"
                           class="data-edit-input"
                           value="${currentValue}"
                           placeholder="${config.placeholder}"
                           min="${config.min}"
                           max="${config.max}"
                           step="${config.step}">
                    <span class="data-unit">${config.unit}</span>
                </div>
                <div class="data-hint">${config.hint}</div>
            </div>
        `;

        // 更新操作按鈕
        actionsDiv.innerHTML = `
            <button class="daily-action-btn save-data-btn" data-record-id="${recordId}" data-category="${category}">
                <i class="fas fa-save"></i>
                <span>保存</span>
            </button>
            <button class="daily-action-btn cancel-daily-btn">
                <i class="fas fa-times"></i>
                <span>取消</span>
            </button>
        `;

        // 添加編輯狀態樣式
        card.classList.add('editing');

        // 聚焦到輸入框
        const input = contentDiv.querySelector('.data-edit-input');
        input.focus();
        input.select();

        // 綁定保存和取消事件
        this.setupDataEditEvents(card, recordId, category);
    }

    showContentEditForm(card, recordId, currentContent) {
        const contentDiv = card.querySelector('.daily-record-content');
        const actionsDiv = card.querySelector('.daily-record-actions');
        
        // 保存原始內容
        card.dataset.originalContent = currentContent;
        
        // 創建編輯表單
        contentDiv.innerHTML = `
            <textarea class="daily-edit-textarea" rows="3" placeholder="請輸入生活記錄內容...">${currentContent}</textarea>
        `;

        // 更新操作按鈕
        actionsDiv.innerHTML = `
            <button class="daily-action-btn save-daily-btn" data-record-id="${recordId}">
                <i class="fas fa-save"></i>
                <span>保存</span>
            </button>
            <button class="daily-action-btn cancel-daily-btn">
                <i class="fas fa-times"></i>
                <span>取消</span>
            </button>
        `;

        // 添加編輯狀態樣式
        card.classList.add('editing');

        // 聚焦到文本框
        const textarea = contentDiv.querySelector('.daily-edit-textarea');
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        // 綁定保存和取消事件
        this.setupEditEvents(card, recordId);
    }

    setupEditEvents(card, recordId) {
        const saveBtn = card.querySelector('.save-daily-btn');
        const cancelBtn = card.querySelector('.cancel-daily-btn');
        const textarea = card.querySelector('.daily-edit-textarea');

        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveDailyRecord(card, recordId, textarea.value.trim());
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cancelEdit(card);
            });
        }

        // 按鍵處理：Escape 取消編輯，Enter 保存
        if (textarea) {
            textarea.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.cancelEdit(card);
                } else if (e.key === 'Enter') {
                    // Ctrl/Cmd + Enter 或單獨 Enter 都可以保存
                    if (e.ctrlKey || e.metaKey || !e.shiftKey) {
                        e.preventDefault();
                        this.saveDailyRecord(card, recordId, textarea.value.trim());
                    }
                    // Shift + Enter 允許換行
                }
            });
        }
    }

    async saveDailyRecord(card, recordId, newContent) {
        if (!newContent) {
            this.showNotification('內容不能為空', 'warning');
            return;
        }

        // 嘗試獲取CSRF token，如果失敗則使用備用方法
        let csrfToken = this.getCSRFToken();
        if (!csrfToken) {
            console.log('嘗試異步獲取CSRF token...');
            csrfToken = await this.getCSRFTokenAsync();
        }

        console.log('準備保存生活記錄:', { recordId, newContent, csrfToken: csrfToken ? '已獲取' : '未獲取' });

        if (!csrfToken) {
            this.showNotification('無法獲取安全令牌，請重新整理頁面', 'error');
            return;
        }

        try {
            const response = await fetch(`/daily_record/${recordId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ content: newContent })
            });

            console.log('伺服器回應狀態:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('伺服器回應資料:', data);

            if (data.status === 'success') {
                this.exitEditMode(card, newContent);
                this.showNotification('生活記錄已更新', 'success');
            } else {
                this.showNotification('更新失敗：' + (data.message || '未知錯誤'), 'error');
                console.error('更新失敗詳情:', data);
            }
        } catch (error) {
            console.error('更新生活記錄時出錯:', error);
            this.showNotification('更新失敗，請稍後再試', 'error');
        }
    }

    cancelEdit(card) {
        const originalContent = card.dataset.originalContent;
        this.exitEditMode(card, originalContent);
        this.showNotification('已取消編輯', 'info');
    }

    exitEditMode(card, content) {
        const contentDiv = card.querySelector('.daily-record-content');
        const actionsDiv = card.querySelector('.daily-record-actions');
        const recordId = card.querySelector('[data-record-id]').dataset.recordId;

        // 恢復內容顯示
        contentDiv.innerHTML = `<p>${content}</p>`;

        // 恢復操作按鈕
        actionsDiv.innerHTML = `
            <button class="daily-action-btn edit-daily-btn" data-record-id="${recordId}">
                <i class="fas fa-edit"></i>
                <span>編輯</span>
            </button>
            <button class="daily-action-btn delete-daily-btn" data-record-id="${recordId}">
                <i class="fas fa-trash"></i>
                <span>刪除</span>
            </button>
        `;

        // 移除編輯狀態
        card.classList.remove('editing');
        delete card.dataset.originalContent;
    }

    handleDeleteDaily(button) {
        const recordId = button.dataset.recordId;
        const card = button.closest('.daily-record-card');

        console.log('刪除記錄 - recordId:', recordId, 'button:', button);

        if (!card) {
            console.error('找不到daily-record-card');
            return;
        }

        if (!recordId) {
            console.error('找不到recordId');
            this.showNotification('找不到記錄ID，無法刪除', 'error');
            return;
        }

        // 確認刪除
        if (!confirm('確定要刪除這筆生活記錄嗎？此操作無法恢復。')) {
            return;
        }

        this.deleteDailyRecord(card, recordId);
    }

    async deleteDailyRecord(card, recordId) {
        try {
            // 獲取寵物ID（從卡片或其他地方）
            const petId = this.getPetIdFromCard(card);
            
            const formData = new FormData();
            formData.append('record_id', recordId);
            
            const response = await fetch(`/pet/${petId}/health/delete_record/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: formData
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                // 添加刪除動畫
                card.style.transform = 'scale(0.9)';
                card.style.opacity = '0';
                
                setTimeout(() => {
                    card.remove();
                    this.checkEmptyState();
                }, 300);
                
                this.showNotification('生活記錄已刪除', 'success');
            } else {
                this.showNotification('刪除失敗：' + (data.message || '未知錯誤'), 'error');
            }
        } catch (error) {
            console.error('刪除生活記錄時出錯:', error);
            this.showNotification('刪除失敗，請稍後再試', 'error');
        }
    }

    getPetIdFromCard(card) {
        // 1. 優先從卡片的 data-pet-id 屬性獲取
        const petIdFromCard = card.getAttribute('data-pet-id');
        if (petIdFromCard) {
            return petIdFromCard;
        }

        // 2. 從URL參數獲取（如果有篩選特定寵物）
        const urlParams = new URLSearchParams(window.location.search);
        const petIdFromUrl = urlParams.get('pet');
        if (petIdFromUrl) {
            return petIdFromUrl;
        }

        // 3. 從頁面上的寵物列表獲取第一個寵物ID
        const firstPetOption = document.querySelector('.pet-filter-option[onclick*="filterByPet"]');
        if (firstPetOption) {
            const onclick = firstPetOption.getAttribute('onclick');
            const matches = onclick.match(/filterByPet\('(\d+)'\)/);
            if (matches && matches[1]) {
                return matches[1];
            }
        }

        // 3. 從卡片中的隱藏數據獲取（如果有的話）
        const petId = card.dataset.petId;
        if (petId) {
            return petId;
        }

        // 4. 最後手段：使用全局變量或從其他地方獲取
        if (window.currentPetId) {
            return window.currentPetId;
        }

        console.warn('無法獲取寵物ID，使用預設值');
        return 1; // 預設值
    }

    checkEmptyState() {
        const visibleCards = document.querySelectorAll('.daily-record-card:not(.hidden)');
        const container = document.querySelector('.daily-records-container');
        
        if (visibleCards.length === 0 && container) {
            const activeFilter = document.querySelector('.daily-filter-btn.active')?.dataset.category || 'all';
            this.showEmptyState(container, activeFilter);
        }
    }

    getCSRFToken() {
        // 首先嘗試從meta標籤獲取
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            const token = metaToken.getAttribute('content');
            if (token) return token;
        }

        // 然後嘗試從cookies獲取
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                const token = decodeURIComponent(value);
                if (token) return token;
            }
        }

        // 最後嘗試從表單中的hidden input獲取
        const csrfInput = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfInput && csrfInput.value) {
            return csrfInput.value;
        }

        console.error('無法獲取CSRF Token');
        return '';
    }

    getDataEditConfig(category) {
        const configs = {
            'temperature': {
                label: '寵物體溫',
                unit: '°C',
                min: 35,
                max: 42,
                step: 0.1,
                placeholder: '請輸入體溫值',
                hint: '正常體溫範圍: 37.5°C - 39.2°C'
            },
            'weight': {
                label: '寵物體重',
                unit: 'kg',
                min: 0.1,
                max: 100,
                step: 0.1,
                placeholder: '請輸入體重值',
                hint: '請輸入準確的體重數值，用於健康追蹤'
            },
            'exercise': {
                label: '運動時長',
                unit: '分鐘',
                min: 1,
                max: 480,
                step: 1,
                placeholder: '請輸入運動時間',
                hint: '記錄寵物的運動或活動時間'
            }
        };
        return configs[category] || configs['temperature'];
    }

    setupDataEditEvents(card, recordId, category) {
        const saveBtn = card.querySelector('.save-data-btn');
        const cancelBtn = card.querySelector('.cancel-daily-btn');
        const input = card.querySelector('.data-edit-input');

        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const value = parseFloat(input.value);
                if (!isNaN(value) && value > 0) {
                    this.saveDataRecord(card, recordId, category, value);
                } else {
                    this.showNotification('請輸入有效的數值', 'warning');
                }
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cancelDataEdit(card, category);
            });
        }

        // 按鍵處理
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.cancelDataEdit(card, category);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    const value = parseFloat(input.value);
                    if (!isNaN(value) && value > 0) {
                        this.saveDataRecord(card, recordId, category, value);
                    } else {
                        this.showNotification('請輸入有效的數值', 'warning');
                    }
                }
            });
        }
    }

    async saveDataRecord(card, recordId, category, value) {
        // 嘗試獲取CSRF token
        let csrfToken = this.getCSRFToken();
        if (!csrfToken) {
            csrfToken = await this.getCSRFTokenAsync();
        }

        if (!csrfToken) {
            this.showNotification('無法獲取安全令牌，請重新整理頁面', 'error');
            return;
        }

        try {
            const dataToSend = {};
            dataToSend[category] = value;

            const response = await fetch(`/daily_record/${recordId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(dataToSend)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.status === 'success') {
                this.exitDataEditMode(card, category, value);
                this.showNotification('數據已更新', 'success');
            } else {
                this.showNotification('更新失敗：' + (data.message || '未知錯誤'), 'error');
            }
        } catch (error) {
            console.error('更新數據時出錯:', error);
            this.showNotification('更新失敗，請稍後再試', 'error');
        }
    }

    cancelDataEdit(card, category) {
        const originalValue = card.dataset.originalValue;
        this.exitDataEditMode(card, category, originalValue);
        this.showNotification('已取消編輯', 'info');
    }

    exitDataEditMode(card, category, value) {
        const contentDiv = card.querySelector('.daily-record-content');
        const actionsDiv = card.querySelector('.daily-record-actions');
        const recordId = card.querySelector('[data-record-id]').dataset.recordId;

        const config = this.getDataEditConfig(category);

        // 恢復數據顯示
        contentDiv.innerHTML = `
            <div class="record-value ${category}-value data-only">
                <i class="fas fa-${this.getCategoryIcon(category)}"></i>
                <span class="value">${value}${config.unit}</span>
                ${this.getValueStatus(category, value)}
            </div>
        `;

        // 恢復操作按鈕
        actionsDiv.innerHTML = `
            <button class="daily-action-btn edit-daily-btn" data-record-id="${recordId}">
                <i class="fas fa-edit"></i>
                <span>編輯</span>
            </button>
            <button class="daily-action-btn delete-daily-btn" data-record-id="${recordId}">
                <i class="fas fa-trash"></i>
                <span>刪除</span>
            </button>
        `;

        // 移除編輯狀態
        card.classList.remove('editing');
        delete card.dataset.originalValue;
    }

    getCategoryIcon(category) {
        const icons = {
            'temperature': 'thermometer-half',
            'weight': 'weight',
            'exercise': 'running'
        };
        return icons[category] || 'chart-bar';
    }

    getValueStatus(category, value) {
        if (category === 'temperature') {
            if (value <= 37.4) {
                return '<span class="status low">偏低</span>';
            } else if (value >= 39.3) {
                return '<span class="status high">偏高</span>';
            } else {
                return '<span class="status normal">正常</span>';
            }
        } else if (category === 'weight') {
            return '<span class="data-hint">用於成長追蹤</span>';
        } else if (category === 'exercise') {
            return '<span class="data-hint">用於習慣分析</span>';
        }
        return '';
    }

    // 備用的異步CSRF token獲取方法
    async getCSRFTokenAsync() {
        try {
            const response = await fetch('/api/csrf-token/');
            const data = await response.json();
            return data.csrfToken;
        } catch (error) {
            console.error('無法從API獲取CSRF Token:', error);
            return this.getCSRFToken(); // 降級到同步方法
        }
    }
}

// CSS樣式注入（用於編輯表單）
const dailyEditStyles = document.createElement('style');
dailyEditStyles.textContent = `
    .daily-edit-textarea {
        width: 100%;
        padding: 12px;
        border: 2px solid var(--health-primary, #4caf50);
        border-radius: 8px;
        font-family: inherit;
        font-size: 0.95rem;
        line-height: 1.6;
        resize: vertical;
        min-height: 80px;
        background: #fff;
        transition: all 0.3s ease;
    }

    .daily-edit-textarea:focus {
        outline: none;
        border-color: var(--health-secondary, #81c784);
        box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
    }

    .daily-record-card.editing {
        border-color: var(--health-primary, #4caf50);
        box-shadow: 0 8px 25px rgba(76, 175, 80, 0.15);
    }

    /* 數值編輯表單樣式 */
    .data-edit-form {
        padding: 1rem;
        background: #f8fffe;
        border-radius: 8px;
        border: 2px dashed var(--health-primary, #4caf50);
    }

    .data-edit-label {
        display: block;
        font-weight: 600;
        color: var(--health-primary, #4caf50);
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }

    .data-input-group {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .data-edit-input {
        flex: 1;
        padding: 0.75rem;
        border: 2px solid #e0e0e0;
        border-radius: 6px;
        font-size: 1rem;
        font-weight: 600;
        text-align: center;
        background: #fff;
        transition: all 0.3s ease;
    }

    .data-edit-input:focus {
        outline: none;
        border-color: var(--health-primary, #4caf50);
        box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
    }

    .data-unit {
        font-weight: 600;
        color: var(--health-primary, #4caf50);
        font-size: 1rem;
        min-width: 2rem;
    }

    .data-hint {
        font-size: 0.8rem;
        color: #666;
        font-style: italic;
        margin-top: 0.25rem;
    }

    /* 手機響應式優化 */
    @media (max-width: 768px) {
        .health-notification {
            position: fixed !important;
            top: auto !important;
            bottom: 80px !important;
            left: 50% !important;
            right: auto !important;
            transform: translateX(-50%) !important;
            width: 90% !important;
            max-width: 350px !important;
            z-index: 999999 !important;
            border-radius: 12px !important;
            font-size: 0.9rem !important;
        }

        .health-notification.health-success {
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%) !important;
        }

        .health-notification.health-error {
            background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%) !important;
        }

        .health-notification.health-warning {
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%) !important;
        }

        .health-notification.health-info {
            background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%) !important;
        }

        .daily-edit-textarea {
            font-size: 1rem;
            padding: 1rem;
            min-height: 100px;
        }

        .data-edit-form {
            padding: 1.25rem;
        }

        .data-edit-input {
            padding: 1rem;
            font-size: 1.1rem;
            min-height: 48px;
        }

        .data-edit-label {
            font-size: 1rem;
            margin-bottom: 0.75rem;
        }

        .data-unit {
            font-size: 1.1rem;
            min-width: 2.5rem;
        }

        .data-hint {
            font-size: 0.9rem;
            margin-top: 0.5rem;
            line-height: 1.4;
        }

        .daily-action-btn {
            min-height: 48px;
            font-size: 0.95rem;
            padding: 0.75rem 1.5rem;
        }
    }

    @media (max-width: 576px) {
        .data-edit-input {
            min-height: 52px;
            font-size: 1.2rem;
            padding: 1.25rem;
        }

        .daily-action-btn {
            min-height: 52px;
            font-size: 1rem;
            padding: 1rem 2rem;
        }

        .health-notification {
            bottom: 100px !important;
            font-size: 1rem !important;
            padding: 1.25rem 1.5rem !important;
        }
    }

    /* 觸控設備優化 */
    @media (hover: none) and (pointer: coarse) {
        .data-edit-input:hover {
            border-color: #e0e0e0;
        }

        .data-edit-input:focus {
            border-color: var(--health-primary, #4caf50);
            transform: scale(1.02);
        }

        .daily-action-btn:hover {
            transform: none;
        }

        .daily-action-btn:active {
            transform: scale(0.96);
            transition: transform 0.1s ease;
        }
    }
`;
document.head.appendChild(dailyEditStyles);

/**
 * 趨勢圖管理類
 */
class TrendChartController {
    constructor() {
        this.chart = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setChartFromURL();
        this.loadChart();
    }

    setChartFromURL() {
        // 從URL參數獲取圖表類型
        const urlParams = new URLSearchParams(window.location.search);
        const chartType = urlParams.get('chart');
        
        if (chartType) {
            const categorySelect = document.getElementById('chart-category');
            if (categorySelect) {
                // 設置下拉選單的值
                categorySelect.value = chartType;
                // console.log(`📊 自動設置圖表類型為: ${chartType}`);
            }
        }
    }

    setupEventListeners() {
        const categorySelect = document.getElementById('chart-category');
        const daysSelect = document.getElementById('chart-days');

        if (categorySelect) {
            categorySelect.addEventListener('change', () => this.loadChart());
        }

        if (daysSelect) {
            daysSelect.addEventListener('change', () => this.loadChart());
        }
    }

    async loadChart() {
        const category = document.getElementById('chart-category')?.value || 'temperature';
        const days = document.getElementById('chart-days')?.value || 30;

        try {
            const response = await fetch(`/api/chart-data/?category=${category}&days=${days}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.renderChart(data);
        } catch (error) {
            console.error('載入圖表數據時出錯:', error);
            this.showChartError();
        }
    }

    renderChart(data) {
        const canvas = document.getElementById('trendChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // 銷毀舊圖表
        if (this.chart) {
            this.chart.destroy();
        }

        const category = document.getElementById('chart-category')?.value || 'temperature';
        
        // 根據分類設置不同的配置
        const config = this.getChartConfig(category, data);

        this.chart = new Chart(ctx, config);
    }

    getChartConfig(category, data) {
        const baseConfig = {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: this.getChartTitle(category),
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                const unit = this.getUnit(category);
                                return `${label}: ${value}${unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '日期'
                        },
                        grid: {
                            color: '#f0f0f0'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: this.getYAxisTitle(category)
                        },
                        grid: {
                            color: '#f0f0f0'
                        }
                    }
                }
            }
        };

        // 根據分類添加特殊配置
        if (category === 'temperature') {
            // 為體溫添加正常範圍線
            baseConfig.options.plugins.annotation = {
                annotations: {
                    normalRangeLow: {
                        type: 'line',
                        yMin: 37.5,
                        yMax: 37.5,
                        borderColor: 'rgba(0, 255, 0, 0.5)',
                        borderWidth: 1,
                        label: {
                            content: '正常範圍下限',
                            enabled: true
                        }
                    },
                    normalRangeHigh: {
                        type: 'line',
                        yMin: 39.2,
                        yMax: 39.2,
                        borderColor: 'rgba(0, 255, 0, 0.5)',
                        borderWidth: 1,
                        label: {
                            content: '正常範圍上限',
                            enabled: true
                        }
                    }
                }
            };
        }

        return baseConfig;
    }

    getChartTitle(category) {
        const titles = {
            'temperature': '體溫變化趨勢',
            'weight': '體重變化趨勢',
            'exercise': '運動時長趨勢'
        };
        return titles[category] || '數據趨勢';
    }

    getYAxisTitle(category) {
        const titles = {
            'temperature': '體溫 (°C)',
            'weight': '體重 (kg)',
            'exercise': '運動時長 (分鐘)'
        };
        return titles[category] || '數值';
    }

    getUnit(category) {
        const units = {
            'temperature': '°C',
            'weight': 'kg',
            'exercise': '分鐘'
        };
        return units[category] || '';
    }

    showChartError() {
        const canvas = document.getElementById('trendChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#999';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('載入圖表數據時出錯，請稍後再試', canvas.width / 2, canvas.height / 2);
        }
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.health-records-wrapper')) {
        window.healthRecords = new HealthRecordsController();
        // console.log('🏥 健康紀錄管理系統已初始化');
        
        // 初始化圖表
        if (document.getElementById('trendChart')) {
            window.trendChart = new TrendChartController();
            // console.log('📊 趨勢圖表系統已初始化');
        }
    }
});

// 向後相容
window.HealthRecordsController = HealthRecordsController;
window.TrendChartController = TrendChartController;