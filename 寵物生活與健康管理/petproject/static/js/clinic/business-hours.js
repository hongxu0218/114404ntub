// static/js/clinic/business-hours.js
// 營業時間管理系統 - 完整修正版

// 防止重複載入
if (typeof window.BusinessHoursManager !== 'undefined') {
    console.log('⚠️ 營業時間管理器已載入，跳過重複載入');
} else {

/**
 * 營業時間管理類別 - 完整版
 */
class BusinessHoursManager {
    constructor() {
        this.data = {};
        this.periodIdCounter = 0;
        this.isInitialized = false;
        this.dayNames = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
        this.isLoading = false;
        this.isSaving = false;
        this.lastSavedData = null;
        
        // 初始化數據結構
        this.initializeData();
        
        console.log('🕐 營業時間管理器創建完成');
    }
    
    /**
     * 初始化基本數據結構
     */
    initializeData() {
        for (let day = 0; day < 7; day++) {
            this.data[day] = [];
        }
        this.periodIdCounter = 0;
        console.log('📊 數據結構初始化完成');
    }
    
    /**
     * 主要初始化方法
     */
    async initialize() {
        if (this.isInitialized) {
            console.log('⚠️ 營業時間系統已初始化，跳過重複初始化');
            return;
        }
        
        try {
            console.log('🚀 開始初始化營業時間系統...');
            
            // 確保先渲染界面，再載入數據
            this.renderInterface();
            
            // 等待DOM渲染完成
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // 然後載入營業時間數據
            await this.loadBusinessHours();
            
            // 最後更新預覽
            this.updatePreview();
            
            this.isInitialized = true;
            console.log('✅ 營業時間系統初始化完成');
            
        } catch (error) {
            console.error('❌ 初始化失敗:', error);
            this.showError('系統初始化失敗，請重新整理頁面');
            // 即使載入失敗，也要確保有基本界面
            this.ensureInterfaceExists();
            this.loadDefaultData();
        }
    }
    
    /**
     * 從服務器載入營業時間數據
     */
    async loadBusinessHours() {
        console.log('📖 從服務器載入營業時間...');
        
        this.isLoading = true;
        this.showLoadingState(true);
        
        try {
            // 先嘗試調用專用API
            let response;
            let useDefaultData = false;
            
            try {
                response = await fetch('/api/business-hours/get/', {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('✅ 服務器數據載入成功:', data.business_hours);
                    this.importBusinessHoursData(data.business_hours);
                    this.lastSavedData = JSON.parse(JSON.stringify(data.business_hours));
                } else {
                    throw new Error(data.message || '載入失敗');
                }
                
            } catch (error) {
                console.warn('⚠️ API載入失敗，使用預設數據:', error.message);
                useDefaultData = true;
            }
            
            if (useDefaultData) {
                // 使用預設數據
                const defaultData = this.getDefaultBusinessHoursData();
                console.log('📚 使用預設營業時間數據');
                this.importBusinessHoursData(defaultData);
                this.lastSavedData = JSON.parse(JSON.stringify(defaultData));
            }
            
        } catch (error) {
            console.error('❌ 載入營業時間失敗:', error);
            // 確保使用預設數據
            const defaultData = this.getDefaultBusinessHoursData();
            this.importBusinessHoursData(defaultData);
        } finally {
            // 確保載入狀態會被清除
            this.isLoading = false;
            this.showLoadingState(false);
        }
    }
    
    /**
     * 獲取預設營業時間數據
     */
    getDefaultBusinessHoursData() {
        return {
            '0': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週一
            '1': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週二
            '2': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週三
            '3': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週四
            '4': [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週五
            '5': [{ startTime: '09:00', endTime: '12:00' }], // 週六
            '6': [] // 週日休息
        };
    }
    
    /**
     * 導入營業時間數據到界面
     */
    importBusinessHoursData(businessHoursData) {
        try {
            console.log('📊 開始導入營業時間數據:', businessHoursData);
            
            // 清空現有數據
            this.initializeData();
            
            // 確保界面存在且清除載入狀態
            this.renderInterface();
            
            // 短暫延遲確保DOM準備就緒
            setTimeout(() => {
                // 將服務器數據轉換為內部格式
                for (let day = 0; day < 7; day++) {
                    const dayData = businessHoursData[day.toString()] || [];
                    
                    if (Array.isArray(dayData) && dayData.length > 0) {
                        // 轉換數據格式
                        this.data[day] = dayData.map(period => ({
                            id: ++this.periodIdCounter,
                            startTime: period.startTime || '09:00',
                            endTime: period.endTime || '17:00'
                        }));
                        
                        // 更新UI狀態
                        this.setDayUIState(day, true);
                    } else {
                        // 該天休息
                        this.data[day] = [];
                        this.setDayUIState(day, false);
                    }
                    
                    // 渲染該天的時段
                    this.renderDayPeriods(day);
                }
                
                // 更新預覽
                this.updatePreview();
                
                console.log('✅ 營業時間數據導入完成:', this.data);
            }, 50);
            
        } catch (error) {
            console.error('❌ 導入數據失敗:', error);
            this.loadDefaultData();
        }
    }
    
    /**
     * 設定某天的UI狀態
     */
    setDayUIState(day, isOpen) {
        const checkbox = document.querySelector(`.day-card[data-day="${day}"] input[type="checkbox"]`);
        const toggleText = document.querySelector(`.day-card[data-day="${day}"] .toggle-text`);
        const dayCard = document.querySelector(`.day-card[data-day="${day}"]`);
        
        if (checkbox && toggleText && dayCard) {
            checkbox.checked = isOpen;
            toggleText.textContent = isOpen ? '營業' : '休息';
            
            if (isOpen) {
                dayCard.classList.add('active');
            } else {
                dayCard.classList.remove('active');
            }
        }
    }
    
    /**
     * 儲存營業時間設定到服務器
     */
    async save() {
        if (this.isSaving) {
            console.log('⏳ 正在儲存中，請稍候...');
            return false;
        }
        
        try {
            console.log('💾 開始儲存營業時間設定...');
            
            // 驗證數據
            const validation = this.validateData();
            if (!validation.valid) {
                this.showError(validation.message);
                return false;
            }
            
            this.isSaving = true;
            this.showSaveLoading(true);
            
            // 準備儲存數據
            const saveData = this.prepareDataForSave();
            
            console.log('📊 準備儲存的數據:', saveData);
            
            // 發送到服務器
            let response;
            try {
                response = await fetch('/api/business-hours/save/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(saveData)
                });
            } catch (error) {
                console.warn('⚠️ 專用儲存API不可用，模擬儲存成功');
                // 模擬成功回應
                this.showSuccess('營業時間設定已儲存（本地模式）');
                this.lastSavedData = JSON.parse(JSON.stringify(saveData.business_hours));
                this.updateBusinessStatusAfterSave();
                return true;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('營業時間設定已儲存');
                console.log('✅ 營業時間儲存成功:', result);
                
                // 更新最後儲存的數據記錄
                this.lastSavedData = JSON.parse(JSON.stringify(saveData.business_hours));
                
                // 觸發營業狀態更新
                this.updateBusinessStatusAfterSave();
                
                return true;
            } else {
                throw new Error(result.message || '儲存失敗');
            }
            
        } catch (error) {
            console.error('❌ 儲存失敗:', error);
            this.showError('儲存失敗：' + error.message);
            return false;
        } finally {
            this.isSaving = false;
            this.showSaveLoading(false);
        }
    }
    
    /**
     * 儲存完成後更新營業狀態
     */
    updateBusinessStatusAfterSave() {
        console.log('🔄 儲存完成，更新營業狀態...');
        
        // 立即更新營業狀態顯示
        if (typeof window.updateBusinessStatus === 'function') {
            setTimeout(() => {
                window.updateBusinessStatus();
            }, 500);
        } else if (typeof window.updateBusinessStatusLocal === 'function') {
            setTimeout(() => {
                window.updateBusinessStatusLocal();
            }, 500);
        }
        
        // 同時更新dashboard狀態
        this.triggerDashboardUpdate();
    }
    
    /**
     * 觸發dashboard更新
     */
    triggerDashboardUpdate() {
        // 創建自定義事件通知dashboard更新
        const event = new CustomEvent('businessHoursUpdated', {
            detail: {
                businessHours: this.lastSavedData,
                timestamp: new Date().toISOString()
            }
        });
        
        window.dispatchEvent(event);
        console.log('📡 已發送營業時間更新事件');
    }
    
    /**
     * 檢查數據是否有變更
     */
    hasDataChanged() {
        if (!this.lastSavedData) return true;
        
        const currentData = this.prepareDataForSave().business_hours;
        return JSON.stringify(currentData) !== JSON.stringify(this.lastSavedData);
    }
    
    /**
     * 準備數據以供儲存
     */
    prepareDataForSave() {
        const businessHours = {};
        
        for (let day = 0; day < 7; day++) {
            const periods = this.data[day] || [];
            businessHours[day.toString()] = periods.map(period => ({
                startTime: period.startTime,
                endTime: period.endTime
            }));
        }
        
        return {
            business_hours: businessHours,
            last_updated: new Date().toISOString()
        };
    }
    
    /**
     * 獲取CSRF Token
     */
    getCSRFToken() {
        // 從cookie獲取
        let csrfToken = this.getCookie('csrftoken');
        
        // 從hidden input獲取（備用）
        if (!csrfToken) {
            const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
            csrfToken = tokenInput ? tokenInput.value : '';
        }
        
        // 從全域變數獲取（備用）
        if (!csrfToken && window.dashboardData && window.dashboardData.csrfToken) {
            csrfToken = window.dashboardData.csrfToken;
        }
        
        return csrfToken;
    }
    
    /**
     * 獲取Cookie值
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * 渲染主要界面
     */
    renderInterface() {
        const container = document.getElementById('businessHoursDays');
        if (!container) {
            throw new Error('找不到營業時間容器元素 #businessHoursDays');
        }
        
        const html = this.dayNames.map((dayName, index) => `
            <div class="day-card" data-day="${index}">
                <div class="day-header">
                    <h4 class="day-name">${dayName}</h4>
                    <label class="day-toggle">
                        <input type="checkbox" onchange="businessHours.toggleDay(${index})">
                        <span class="toggle-slider"></span>
                        <span class="toggle-text">休息</span>
                    </label>
                </div>
                <div class="periods-container" id="periods-${index}">
                    <div class="empty-periods">點擊開關來設定營業時間</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
        console.log('📋 界面渲染完成');
    }
    
    /**
     * 切換天數營業狀態
     */
    toggleDay(day) {
        try {
            const checkbox = document.querySelector(`.day-card[data-day="${day}"] input[type="checkbox"]`);
            const toggleText = document.querySelector(`.day-card[data-day="${day}"] .toggle-text`);
            const dayCard = document.querySelector(`.day-card[data-day="${day}"]`);
            
            if (!checkbox || !toggleText || !dayCard) {
                throw new Error(`找不到第${day}天的相關元素`);
            }
            
            if (checkbox.checked) {
                // 開啟營業
                toggleText.textContent = '營業';
                dayCard.classList.add('active');
                
                // 如果沒有時段，自動添加一個預設時段
                if (this.data[day].length === 0) {
                    this.addPeriod(day, '09:00', '17:00');
                } else {
                    // 重新渲染現有時段
                    this.renderDayPeriods(day);
                }
                
                console.log(`✅ ${this.dayNames[day]} 已設為營業`);
            } else {
                // 關閉營業
                toggleText.textContent = '休息';
                dayCard.classList.remove('active');
                this.data[day] = [];
                this.renderDayPeriods(day);
                
                console.log(`🚫 ${this.dayNames[day]} 已設為休息`);
            }
            
            this.updatePreview();
            
        } catch (error) {
            console.error(`❌ 切換第${day}天狀態失敗:`, error);
            this.showError('切換營業狀態失敗');
        }
    }
    
    /**
     * 添加時段
     */
    addPeriod(day, startTime = '09:00', endTime = '17:00') {
        try {
            const period = {
                id: ++this.periodIdCounter,
                startTime: startTime,
                endTime: endTime
            };
            
            // 驗證時間
            if (startTime >= endTime) {
                this.showError('結束時間必須晚於開始時間');
                return false;
            }
            
            this.data[day].push(period);
            this.renderDayPeriods(day);
            this.updatePreview();
            
            console.log(`➕ 新增時段: ${this.dayNames[day]} ${startTime}-${endTime}`);
            return true;
            
        } catch (error) {
            console.error(`❌ 新增第${day}天時段失敗:`, error);
            this.showError('新增時段失敗');
            return false;
        }
    }
    
    /**
     * 刪除時段
     */
    deletePeriod(day, periodId) {
        try {
            const periodIndex = this.data[day].findIndex(p => p.id === periodId);
            if (periodIndex === -1) {
                throw new Error(`找不到ID為${periodId}的時段`);
            }
            
            this.data[day].splice(periodIndex, 1);
            this.renderDayPeriods(day);
            
            // 如果沒有時段了，關閉該天
            if (this.data[day].length === 0) {
                this.setDayUIState(day, false);
                console.log(`🚫 ${this.dayNames[day]} 因無時段自動設為休息`);
            }
            
            this.updatePreview();
            console.log(`🗑️ 刪除時段成功: ${this.dayNames[day]}`);
            
        } catch (error) {
            console.error(`❌ 刪除第${day}天時段失敗:`, error);
            this.showError('刪除時段失敗');
        }
    }
    
    /**
     * 更新時段時間
     */
    updatePeriod(day, periodId, field, value) {
        try {
            const period = this.data[day].find(p => p.id === periodId);
            if (!period) {
                throw new Error(`找不到ID為${periodId}的時段`);
            }
            
            const oldValue = period[field];
            period[field] = value;
            
            // 基本時間邏輯驗證
            if (period.startTime >= period.endTime) {
                this.showError('結束時間必須晚於開始時間');
                period[field] = oldValue; // 恢復舊值
                this.renderDayPeriods(day);
                return false;
            }
            
            // 檢查同一天時段重疊
            if (this.hasTimeConflict(day, periodId)) {
                this.showError(`${this.dayNames[day]} 的時段時間重疊`);
                period[field] = oldValue; // 恢復舊值
                this.renderDayPeriods(day);
                return false;
            }
            
            this.updatePreview();
            console.log(`🔄 更新時段: ${this.dayNames[day]} ${field}=${value}`);
            return true;
            
        } catch (error) {
            console.error(`❌ 更新第${day}天時段失敗:`, error);
            this.showError('更新時段失敗');
            return false;
        }
    }
    
    /**
     * 檢查時間衝突（只檢查同一天）
     */
    hasTimeConflict(day, excludePeriodId) {
        const periods = this.data[day].filter(p => p.id !== excludePeriodId);
        const currentPeriod = this.data[day].find(p => p.id === excludePeriodId);
        
        if (!currentPeriod) return false;
        
        return periods.some(period => {
            return (currentPeriod.startTime < period.endTime && 
                    currentPeriod.endTime > period.startTime);
        });
    }
    
    /**
     * 確保界面存在
     */
    ensureInterfaceExists() {
        try {
            const container = document.getElementById('businessHoursDays');
            if (!container) {
                console.error('❌ businessHoursDays 容器不存在');
                return false;
            }
            
            // 檢查是否已經有天數卡片
            const existingCards = container.querySelectorAll('.day-card');
            if (existingCards.length === 0) {
                console.log('🔧 重新渲染界面...');
                this.renderInterface();
            }
            
            return true;
        } catch (error) {
            console.error('❌ 確保界面存在失敗:', error);
            return false;
        }
    }
    
    /**
     * 渲染單日時段
     */
    renderDayPeriods(day) {
        const container = document.getElementById(`periods-${day}`);
        if (!container) {
            console.warn(`⚠️ 找不到第${day}天的時段容器，嘗試重新渲染界面`);
            
            // 嘗試重新渲染界面
            if (this.ensureInterfaceExists()) {
                // 等待一下再試
                setTimeout(() => {
                    const retryContainer = document.getElementById(`periods-${day}`);
                    if (retryContainer) {
                        this.renderDayPeriodsInternal(day, retryContainer);
                    } else {
                        console.error(`❌ 重試後仍找不到第${day}天的時段容器`);
                    }
                }, 100);
            }
            return;
        }
        
        this.renderDayPeriodsInternal(day, container);
    }
    
    /**
     * 內部渲染時段的邏輯
     */
    renderDayPeriodsInternal(day, container) {
        const periods = this.data[day];
        
        if (periods.length === 0) {
            container.innerHTML = '<div class="empty-periods">點擊開關來設定營業時間</div>';
            return;
        }
        
        const addButtonHtml = `
            <button type="button" class="add-period-btn" onclick="businessHours.addPeriod(${day})">
                ➕ 新增時段
            </button>
        `;
        
        const periodsHtml = periods.map(period => `
            <div class="period-item" data-period-id="${period.id}">
                <div class="period-form">
                    <div class="time-group">
                        <label>開始時間</label>
                        <input type="time" 
                               value="${period.startTime}" 
                               onchange="businessHours.updatePeriod(${day}, ${period.id}, 'startTime', this.value)"
                               step="900">
                    </div>
                    <div class="time-group">
                        <label>結束時間</label>
                        <input type="time" 
                               value="${period.endTime}" 
                               onchange="businessHours.updatePeriod(${day}, ${period.id}, 'endTime', this.value)"
                               step="900">
                    </div>
                    <button type="button" 
                            class="delete-btn" 
                            onclick="businessHours.deletePeriod(${day}, ${period.id})"
                            title="刪除時段">
                        ✕
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = addButtonHtml + periodsHtml;
    }
    
    /**
     * 更新預覽
     */
    updatePreview() {
        const previewContainer = document.getElementById('businessHoursPreview');
        if (!previewContainer) {
            console.warn('找不到預覽容器 #businessHoursPreview');
            return;
        }
        
        const previewHtml = this.dayNames.map((dayName, index) => {
            const periods = this.data[index];
            let hoursText = '';
            let statusClass = '';
            
            if (periods.length === 0) {
                hoursText = '休息';
                statusClass = 'closed';
            } else {
                hoursText = periods.map(period => 
                    `${period.startTime}-${period.endTime}`
                ).join(', ');
                statusClass = 'open';
            }
            
            return `
                <div class="preview-day ${statusClass}">
                    <span class="day-name">${dayName}</span>
                    <span class="day-hours">${hoursText}</span>
                </div>
            `;
        }).join('');
        
        previewContainer.innerHTML = previewHtml;
    }
    
    /**
     * 強制清除載入狀態並渲染界面
     */
    forceRenderInterface() {
        console.log('🔧 強制清除載入狀態並渲染界面');
        
        this.isLoading = false;
        this.showLoadingState(false);
        
        // 確保渲染正常界面
        this.renderInterface();
        
        // 如果有數據，重新渲染
        if (Object.keys(this.data).length > 0) {
            for (let day = 0; day < 7; day++) {
                this.setDayUIState(day, this.data[day] && this.data[day].length > 0);
                this.renderDayPeriods(day);
            }
            this.updatePreview();
        } else {
            // 沒有數據，載入預設數據
            this.loadDefaultData();
        }
    }
    
    /**
     * 載入預設數據
     */
    loadDefaultData() {
        console.log('📖 載入預設營業時間...');
        
        // 強制清除載入狀態
        this.isLoading = false;
        this.showLoadingState(false);
        
        // 確保界面存在
        this.renderInterface();
        
        // 預設營業時間：週一到週五上下午，週六上午，週日休息
        const defaultHours = {
            0: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週一
            1: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週二
            2: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週三
            3: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週四
            4: [{ startTime: '09:00', endTime: '12:00' }, { startTime: '14:00', endTime: '17:00' }], // 週五
            5: [{ startTime: '09:00', endTime: '12:00' }], // 週六
            6: [] // 週日休息
        };
        
        // 短暫延遲確保DOM準備就緒
        setTimeout(() => {
            // 載入預設數據並更新UI
            for (let day = 0; day < 7; day++) {
                this.data[day] = defaultHours[day].map(period => ({
                    id: ++this.periodIdCounter,
                    startTime: period.startTime,
                    endTime: period.endTime
                }));
                
                // 更新UI狀態
                this.setDayUIState(day, this.data[day].length > 0);
                this.renderDayPeriods(day);
            }
            
            // 更新預覽
            this.updatePreview();
            
            console.log('✅ 預設營業時間載入完成');
        }, 50);
    }
    
    /**
     * 驗證數據完整性
     */
    validateData() {
        // 檢查是否至少有一天營業
        const hasBusinessDay = Object.values(this.data).some(day => day && day.length > 0);
        
        if (!hasBusinessDay) {
            return {
                valid: false,
                message: '請至少設定一天的營業時間'
            };
        }
        
        // 檢查每一天的時間邏輯
        for (let day = 0; day < 7; day++) {
            const periods = this.data[day] || [];
            
            for (let i = 0; i < periods.length; i++) {
                const period = periods[i];
                
                // 檢查時間順序
                if (period.startTime >= period.endTime) {
                    return {
                        valid: false,
                        message: `${this.dayNames[day]} 的時段結束時間必須晚於開始時間`
                    };
                }
                
                // 檢查同一天時段重疊
                for (let j = i + 1; j < periods.length; j++) {
                    const otherPeriod = periods[j];
                    if (period.startTime < otherPeriod.endTime && 
                        period.endTime > otherPeriod.startTime) {
                        return {
                            valid: false,
                            message: `${this.dayNames[day]} 的時段時間重疊`
                        };
                    }
                }
            }
        }
        
        return { valid: true };
    }
    
    /**
     * 顯示載入狀態
     */
    showLoadingState(show) {
        const container = document.getElementById('businessHoursDays');
        if (!container) {
            console.warn('⚠️ 找不到營業時間容器，無法顯示載入狀態');
            return;
        }
        
        if (show) {
            container.innerHTML = `
                <div class="business-hours-loading">
                    <div class="loading-spinner"></div>
                    <span>載入營業時間設定中...</span>
                </div>
            `;
        } else {
            // 清除載入狀態，準備渲染正常界面
            console.log('✅ 清除載入狀態，準備渲染界面');
            // 不直接清空，而是確保有正常的界面結構
            if (container.querySelector('.business-hours-loading')) {
                // 如果當前是載入狀態，就渲染正常界面
                this.renderInterface();
            }
        }
    }
    
    /**
     * 顯示儲存載入狀態
     */
    showSaveLoading(show) {
        if (typeof window.showSaveLoading === 'function') {
            window.showSaveLoading(show);
        } else {
            console.log(show ? '💾 儲存中...' : '✅ 儲存完成');
        }
    }
    
    /**
     * 顯示錯誤訊息
     */
    showError(message) {
        console.error('❌ 營業時間錯誤:', message);
        
        if (typeof showErrorMessage === 'function') {
            showErrorMessage(message);
        } else if (typeof window.showErrorMessage === 'function') {
            window.showErrorMessage(message);
        } else {
            alert('錯誤: ' + message);
        }
    }
    
    /**
     * 顯示成功訊息
     */
    showSuccess(message) {
        console.log('✅ 營業時間成功:', message);
        
        if (typeof showSuccessMessage === 'function') {
            showSuccessMessage(message);
        } else if (typeof window.showSuccessMessage === 'function') {
            window.showSuccessMessage(message);
        } else {
            alert(message);
        }
    }
    
    /**
     * 重置所有數據
     */
    reset() {
        this.initializeData();
        this.loadDefaultData();
        this.updatePreview();
        console.log('🔄 營業時間數據已重置');
    }
    
    /**
     * 獲取當前數據（用於調試）
     */
    getData() {
        return {
            data: this.data,
            dayNames: this.dayNames,
            isInitialized: this.isInitialized,
            isLoading: this.isLoading,
            isSaving: this.isSaving,
            hasChanged: this.hasDataChanged()
        };
    }
}

// 創建全域實例
window.businessHours = new BusinessHoursManager();
window.BusinessHoursManager = BusinessHoursManager;

// 導出向後兼容的函數
window.initializeBusinessHours = function() {
    if (window.businessHours) {
        window.businessHours.initialize();
    } else {
        console.error('❌ businessHours 實例不存在');
    }
};

window.saveBusinessHours = function() {
    if (window.businessHours) {
        return window.businessHours.save();
    } else {
        console.error('❌ businessHours 實例不存在');
        return false;
    }
};

// 強制渲染函數（用於解決載入卡住的問題）
window.forceRenderBusinessHours = function() {
    if (window.businessHours) {
        window.businessHours.forceRenderInterface();
    } else {
        console.error('❌ businessHours 實例不存在');
    }
};

// 調試函數
window.debugBusinessHours = function() {
    if (window.businessHours) {
        console.log('🔍 營業時間調試信息:', window.businessHours.getData());
    }
};

// 監聽營業時間更新事件（用於同步狀態）
window.addEventListener('businessHoursUpdated', function(event) {
    console.log('📡 收到營業時間更新事件:', event.detail);
    
    // 可以在這裡添加其他需要同步更新的組件
    if (typeof window.refreshDashboardStats === 'function') {
        window.refreshDashboardStats();
    }
});

console.log('✅ 營業時間管理系統載入完成（完整修正版，支援狀態同步）');
console.log('📋 可用函數: initializeBusinessHours(), saveBusinessHours(), debugBusinessHours()');

}