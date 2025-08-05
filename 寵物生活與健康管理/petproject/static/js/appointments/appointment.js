/**
 * 現代化預約表單 - JavaScript控制器
 * 提供流暢的用戶體驗、智能表單驗證和動態內容載入
 */

class AppointmentFormController {
    constructor() {
        this.currentStep = 1;
        this.maxStep = 4;
        this.isSubmitting = false;
        this.touchDevice = this.isTouchDevice();
        this.loadingStates = new Map();
        this.validationRules = this.setupValidationRules();
        this.debounceTimers = new Map();
        
        // 檢查依賴
        this.jQueryAvailable = typeof $ !== 'undefined';
        this.modernBrowser = this.checkModernBrowser();
        
        this.init();
    }

    // ===== 初始化與設置 =====
    init() {
        this.setupEventListeners();
        this.initializeForm();
        this.setupAnimations();
        this.setupAccessibility();
        
        console.log('✅ 現代化預約表單已初始化', {
            jQuery: this.jQueryAvailable,
            modernBrowser: this.modernBrowser,
            touchDevice: this.touchDevice
        });
    }

    checkModernBrowser() {
        return 'fetch' in window && 
               'Promise' in window && 
               'localStorage' in window &&
               CSS.supports('backdrop-filter', 'blur(10px)');
    }

    isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }

    setupValidationRules() {
        return {
            clinic: {
                required: true,
                message: '請選擇診所',
                validator: (value) => value && value.trim() !== ''
            },
            appointment_date: {
                required: true,
                message: '請選擇預約日期',
                validator: (value) => {
                    if (!value) return false;
                    const selectedDate = new Date(value);
                    const tomorrow = new Date();
                    tomorrow.setDate(tomorrow.getDate() + 1);
                    tomorrow.setHours(0, 0, 0, 0);
                    return selectedDate >= tomorrow;
                },
                customMessage: '預約日期必須是明天以後'
            },
            time_slot: {
                required: true,
                message: '請選擇預約時段',
                validator: (value) => value && value.trim() !== ''
            },
            contact_phone: {
                required: true,
                message: '請輸入聯絡電話',
                validator: (value) => /^09\d{8}$/.test(value?.replace(/[-\s]/g, '') || ''),
                customMessage: '請輸入正確的台灣手機號碼格式'
            }
        };
    }

    // ===== 事件監聽器設置 =====
    setupEventListeners() {
        // 表單提交
        this.addListener('#appointmentForm', 'submit', (e) => this.handleFormSubmit(e));
        
        // 診所選擇變更
        this.addListener('#id_clinic', 'change', (e) => this.handleClinicChange(e.target.value));
        
        // 醫師選擇變更
        this.addListener('#id_doctor', 'change', () => this.loadAvailableSlots());
        
        // 日期選擇變更
        this.addListener('#id_appointment_date', 'change', () => {
            this.validateField('appointment_date');
            this.loadAvailableSlots();
        });
        
        // 時段選擇變更
        this.addListener('#id_time_slot', 'change', (e) => {
            this.validateField('time_slot');
            this.updateProgress();
        });
        
        // 實時驗證
        this.setupRealTimeValidation();
        
        // 字符計數
        this.setupCharacterCounters();
        
        // 電話格式化
        this.addListener('#id_contact_phone', 'input', (e) => this.formatPhoneNumber(e.target));
        
        // 進度追蹤
        this.setupProgressTracking();
        
        // 幫助面板
        window.toggleHelpPanel = () => this.toggleHelpPanel();
        
        // 全局錯誤處理
        window.addEventListener('error', (e) => this.handleGlobalError(e));
        
        // 鍵盤快捷鍵
        this.setupKeyboardShortcuts();
    }

    addListener(selector, event, handler) {
        const element = document.querySelector(selector);
        if (element) {
            element.addEventListener(event, handler);
        }
    }

    setupRealTimeValidation() {
        ['clinic', 'appointment_date', 'time_slot', 'contact_phone'].forEach(fieldName => {
            const element = document.getElementById(`id_${fieldName}`);
            if (element) {
                element.addEventListener('blur', () => this.validateField(fieldName));
                element.addEventListener('change', () => this.validateField(fieldName));
            }
        });
    }

    setupCharacterCounters() {
        this.setupCounter('reason', 500);
        this.setupCounter('notes', 300);
    }

    setupCounter(fieldName, maxLength) {
        const field = document.getElementById(`id_${fieldName}`);
        const counter = document.getElementById(`${fieldName}Counter`);
        
        if (field && counter) {
            field.addEventListener('input', () => {
                this.updateCharacterCounter(fieldName, maxLength);
            });
            this.updateCharacterCounter(fieldName, maxLength); // 初始化
        }
    }

    setupProgressTracking() {
        // 自動進度追蹤
        const fieldSteps = {
            'id_clinic': 2,
            'id_doctor': 2,
            'id_appointment_date': 3,
            'id_time_slot': 3,
            'id_reason': 4,
            'id_notes': 4,
            'id_contact_phone': 4
        };

        Object.entries(fieldSteps).forEach(([fieldId, step]) => {
            const element = document.getElementById(fieldId);
            if (element) {
                element.addEventListener('focus', () => {
                    if (step > this.currentStep) {
                        this.setStep(step);
                    }
                });
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter 提交表單
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const form = document.getElementById('appointmentForm');
                if (form && !this.isSubmitting) {
                    this.handleFormSubmit(new Event('submit'));
                }
            }
            
            // Escape 關閉幫助面板
            if (e.key === 'Escape') {
                const helpPanel = document.getElementById('helpPanel');
                if (helpPanel?.classList.contains('open')) {
                    this.toggleHelpPanel();
                }
            }
        });
    }

    // ===== 表單初始化 =====
    initializeForm() {
        this.updateProgress();
        this.setMinDate();
        this.populateInitialData();
        this.setupFormSteps();
    }

    setMinDate() {
        const dateInput = document.getElementById('id_appointment_date');
        if (dateInput) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            dateInput.min = tomorrow.toISOString().split('T')[0];
        }
    }

    populateInitialData() {
        // 如果有預設聯絡電話，格式化它
        const phoneField = document.getElementById('id_contact_phone');
        if (phoneField && phoneField.value) {
            this.formatPhoneNumber(phoneField);
        }
    }

    setupFormSteps() {
        // 初始化表單步驟顯示
        document.querySelectorAll('.form-step').forEach((step, index) => {
            if (index === 0) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
    }

    // ===== 動畫設置 =====
    setupAnimations() {
        if (this.modernBrowser) {
            this.setupScrollAnimations();
            this.setupHoverEffects();
            this.setupRippleEffects();
        }
    }

    setupScrollAnimations() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
                    }
                });
            }, { threshold: 0.1 });

            document.querySelectorAll('.modern-card, .tip-item').forEach(el => {
                observer.observe(el);
            });
        }
    }

    setupHoverEffects() {
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                if (!this.touchDevice) {
                    btn.style.transform = 'translateY(-2px)';
                }
            });
            
            btn.addEventListener('mouseleave', () => {
                if (!this.touchDevice) {
                    btn.style.transform = '';
                }
            });
        });
    }

    setupRippleEffects() {
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.createRipple(e, btn);
            });
        });
    }

    createRipple(event, element) {
        const ripple = element.querySelector('.btn-ripple');
        if (!ripple) return;

        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.style.transform = 'scale(0)';
        
        requestAnimationFrame(() => {
            ripple.style.transform = 'scale(1)';
        });
    }

    // ===== 無障礙性設置 =====
    setupAccessibility() {
        // 為表單控件添加 aria 標籤
        this.setupAriaLabels();
        
        // 設置焦點管理
        this.setupFocusManagement();
        
        // 設置屏幕閱讀器公告
        this.setupScreenReaderAnnouncements();
    }

    setupAriaLabels() {
        const fieldMappings = {
            'id_clinic': '選擇診所',
            'id_doctor': '選擇醫師',
            'id_appointment_date': '選擇預約日期',
            'id_time_slot': '選擇預約時段',
            'id_reason': '預約原因',
            'id_notes': '其他備註',
            'id_contact_phone': '聯絡電話'
        };

        Object.entries(fieldMappings).forEach(([id, label]) => {
            const element = document.getElementById(id);
            if (element && !element.getAttribute('aria-label')) {
                element.setAttribute('aria-label', label);
            }
        });
    }

    setupFocusManagement() {
        // 確保表單步驟間的焦點管理
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                this.handleTabNavigation(e);
            }
        });
    }

    handleTabNavigation(event) {
        const focusableElements = this.getFocusableElements();
        const currentIndex = focusableElements.indexOf(document.activeElement);
        
        if (event.shiftKey) {
            // Shift + Tab (向後)
            if (currentIndex === 0) {
                event.preventDefault();
                focusableElements[focusableElements.length - 1].focus();
            }
        } else {
            // Tab (向前)
            if (currentIndex === focusableElements.length - 1) {
                event.preventDefault();
                focusableElements[0].focus();
            }
        }
    }

    getFocusableElements() {
        const selector = 'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
        return Array.from(document.querySelectorAll(selector)).filter(el => {
            return el.offsetParent !== null; // 確保元素可見
        });
    }

    setupScreenReaderAnnouncements() {
        // 創建 live region 用於動態公告
        if (!document.getElementById('sr-announcements')) {
            const liveRegion = document.createElement('div');
            liveRegion.id = 'sr-announcements';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
            document.body.appendChild(liveRegion);
        }
    }

    announceToScreenReader(message) {
        const liveRegion = document.getElementById('sr-announcements');
        if (liveRegion) {
            liveRegion.textContent = message;
            setTimeout(() => {
                liveRegion.textContent = '';
            }, 1000);
        }
    }

    // ===== 進度管理 =====
    setStep(step) {
        if (step >= 1 && step <= this.maxStep && step !== this.currentStep) {
            this.currentStep = step;
            this.updateProgress();
            this.updateFormSteps();
            this.announceToScreenReader(`現在在第 ${step} 步，共 ${this.maxStep} 步`);
        }
    }

    updateProgress() {
        this.updateProgressIndicator();
        this.updateProgressFill();
    }

    updateProgressIndicator() {
        document.querySelectorAll('.progress-step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            } else if (stepNumber === this.currentStep) {
                step.classList.add('active');
            }
        });
    }

    updateProgressFill() {
        const progressFill = document.getElementById('progressFill');
        if (progressFill) {
            const percentage = ((this.currentStep - 1) / (this.maxStep - 1)) * 100;
            progressFill.style.width = `${percentage}%`;
        }
    }

    updateFormSteps() {
        // 更新表單步驟的可見性
        document.querySelectorAll('.form-step').forEach((step, index) => {
            const stepNumber = index + 1;
            if (stepNumber <= this.currentStep) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
    }

    // ===== 診所和時段載入 =====
    async handleClinicChange(clinicId) {
        if (!clinicId) {
            this.resetDoctorOptions();
            this.resetTimeSlotOptions();
            return;
        }

        try {
            this.setLoadingState('doctor', true);
            await this.loadDoctors(clinicId);
            this.setStep(2);
            this.loadAvailableSlots();
            this.showFieldFeedback('clinic', 'success', '診所已選擇');
        } catch (error) {
            this.showFieldFeedback('clinic', 'error', '載入診所資訊失敗');
            console.error('載入醫師失敗:', error);
        } finally {
            this.setLoadingState('doctor', false);
        }
    }

    async loadDoctors(clinicId) {
        const response = await this.fetchWithRetry('/api/doctors/', {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            signal: AbortSignal.timeout(10000)
        }, { clinic_id: clinicId });

        const data = await response.json();
        this.updateDoctorOptions(data.doctors || []);
    }

    updateDoctorOptions(doctors) {
        const doctorSelect = document.getElementById('id_doctor');
        if (!doctorSelect) return;

        doctorSelect.innerHTML = '<option value="">任何醫師</option>';
        
        doctors.forEach(doctor => {
            const option = document.createElement('option');
            option.value = doctor.id;
            option.textContent = doctor.name + (doctor.specialization ? ` (${doctor.specialization})` : '');
            doctorSelect.appendChild(option);
        });

        this.animateUpdate(doctorSelect);
    }

    resetDoctorOptions() {
        const doctorSelect = document.getElementById('id_doctor');
        if (doctorSelect) {
            doctorSelect.innerHTML = '<option value="">請先選擇診所</option>';
        }
    }

    async loadAvailableSlots() {
        const clinicId = this.getFieldValue('clinic');
        const doctorId = this.getFieldValue('doctor');
        const date = this.getFieldValue('appointment_date');
        
        if (!clinicId || !date) {
            this.resetTimeSlotOptions();
            this.updateSlotsStatus('請先選擇診所和日期');
            return;
        }

        try {
            this.setLoadingState('slots', true);
            this.updateSlotsStatus('載入可用時段中...', 'loading');
            
            const params = { clinic_id: clinicId, date: date };
            if (doctorId) params.doctor_id = doctorId;

            const response = await this.fetchWithRetry('/api/time-slots/', {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: AbortSignal.timeout(10000)
            }, params);

            const data = await response.json();
            this.updateTimeSlotOptions(data.slots || []);
            
        } catch (error) {
            this.updateSlotsStatus('載入時段失敗，請重試', 'error');
            console.error('載入時段失敗:', error);
        } finally {
            this.setLoadingState('slots', false);
        }
    }

    updateTimeSlotOptions(slots) {
        const slotSelect = document.getElementById('id_time_slot');
        if (!slotSelect) return;

        slotSelect.innerHTML = '<option value="">請選擇時段</option>';
        
        if (slots.length > 0) {
            slots.forEach(slot => {
                const option = document.createElement('option');
                option.value = slot.id;
                option.textContent = `${slot.start_time} - ${slot.end_time} (${slot.doctor_name})`;
                slotSelect.appendChild(option);
            });
            
            this.updateSlotsStatus(`找到 ${slots.length} 個可用時段`, 'success');
        } else {
            slotSelect.innerHTML = '<option value="">此日期沒有可用時段</option>';
            this.updateSlotsStatus('此日期沒有可用時段，請選擇其他日期', 'info');
        }

        this.animateUpdate(slotSelect);
    }

    resetTimeSlotOptions() {
        const slotSelect = document.getElementById('id_time_slot');
        if (slotSelect) {
            slotSelect.innerHTML = '<option value="">請先選擇日期</option>';
        }
    }

    updateSlotsStatus(message, type = 'info') {
        const statusElement = document.getElementById('slotsStatus');
        if (!statusElement) return;

        const statusContent = statusElement.querySelector('.status-content span');
        if (statusContent) {
            statusContent.textContent = message;
        }

        statusElement.className = 'slots-status';
        if (type !== 'info') {
            statusElement.classList.add(type);
        }
    }

    // ===== 載入狀態管理 =====
    setLoadingState(key, loading) {
        this.loadingStates.set(key, loading);
        
        const overlayMap = {
            'doctor': '#doctorLoading',
            'slots': '#slotsLoading'
        };
        
        const overlay = document.querySelector(overlayMap[key]);
        if (overlay) {
            if (loading) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }
    }

    // ===== 表單驗證 =====
    validateField(fieldName) {
        const rule = this.validationRules[fieldName];
        if (!rule) return true;

        const value = this.getFieldValue(fieldName);
        const isValid = rule.validator(value);
        
        if (!isValid) {
            const message = rule.customMessage || rule.message;
            this.showFieldFeedback(fieldName, 'error', message);
            return false;
        } else {
            this.showFieldFeedback(fieldName, 'success', '✓');
            return true;
        }
    }

    validateAllFields() {
        const requiredFields = Object.keys(this.validationRules);
        let allValid = true;
        let firstInvalidField = null;

        requiredFields.forEach(fieldName => {
            const isValid = this.validateField(fieldName);
            if (!isValid) {
                allValid = false;
                if (!firstInvalidField) {
                    firstInvalidField = document.getElementById(`id_${fieldName}`);
                }
            }
        });

        if (firstInvalidField) {
            this.scrollToElement(firstInvalidField);
            firstInvalidField.focus();
        }

        return allValid;
    }

    showFieldFeedback(fieldName, type, message) {
        const feedback = document.querySelector(`[data-field="${fieldName}"]`);
        if (!feedback) return;

        feedback.className = 'field-feedback show ' + type;
        feedback.innerHTML = `<i class="fas fa-${this.getFeedbackIcon(type)}"></i> ${message}`;
        
        // 自動隱藏成功訊息
        if (type === 'success') {
            setTimeout(() => {
                if (feedback.classList.contains('success')) {
                    feedback.classList.remove('show');
                }
            }, 3000);
        }
    }

    getFeedbackIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // ===== 字符計數 =====
    updateCharacterCounter(fieldName, maxLength) {
        const field = document.getElementById(`id_${fieldName}`);
        const counter = document.getElementById(`${fieldName}Counter`);
        
        if (!field || !counter) return;
        
        const currentLength = field.value.length;
        counter.textContent = currentLength;
        
        // 更新樣式
        counter.style.color = this.getCounterColor(currentLength, maxLength);
        
        // 接近限制時的警告
        if (currentLength > maxLength * 0.9) {
            this.showFieldFeedback(fieldName, 'error', `字符數量即將超過限制 (${currentLength}/${maxLength})`);
        } else if (currentLength > maxLength * 0.8) {
            this.showFieldFeedback(fieldName, 'info', `注意字符數量 (${currentLength}/${maxLength})`);
        }
    }

    getCounterColor(current, max) {
        const percentage = current / max;
        if (percentage > 0.9) return '#ef4444'; // 紅色
        if (percentage > 0.8) return '#f59e0b'; // 橙色
        return '#64748b'; // 灰色
    }

    // ===== 電話格式化 =====
    formatPhoneNumber(input) {
        let value = input.value.replace(/\D/g, ''); // 移除所有非數字
        
        if (value.length > 10) {
            value = value.substring(0, 10);
        }
        
        // 台灣手機號碼格式：09XX-XXX-XXX
        if (value.length >= 7) {
            value = value.replace(/(\d{4})(\d{3})(\d{3})/, '$1-$2-$3');
        } else if (value.length >= 4) {
            value = value.replace(/(\d{4})(\d+)/, '$1-$2');
        }
        
        input.value = value;
    }

    // ===== 表單提交 =====
    async handleFormSubmit(event) {
        event.preventDefault();
        
        if (this.isSubmitting) {
            return false;
        }

        // 驗證所有欄位
        if (!this.validateAllFields()) {
            this.showNotification('請檢查並修正表單中的錯誤', 'error');
            return false;
        }

        try {
            this.setSubmitLoading(true);
            this.announceToScreenReader('正在處理您的預約請求');
            
            // 使用原生表單提交或 AJAX
            if (this.jQueryAvailable) {
                await this.submitWithAjax();
            } else {
                // 讓瀏覽器處理原生表單提交
                event.target.submit();
            }
            
        } catch (error) {
            this.handleSubmitError(error);
        }
    }

    async submitWithAjax() {
        const form = document.getElementById('appointmentForm');
        const formData = new FormData(form);
        
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (response.ok) {
            // 處理成功回應
            const result = await response.text();
            if (result.includes('success')) {
                this.showNotification('預約成功！正在跳轉...', 'success');
                setTimeout(() => {
                    window.location.href = response.url || '/appointments/success/';
                }, 1500);
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    }

    handleSubmitError(error) {
        console.error('提交預約失敗:', error);
        this.showNotification('提交失敗，請稍後重試', 'error');
        this.setSubmitLoading(false);
        this.announceToScreenReader('預約提交失敗，請檢查網路連線後重試');
    }

    setSubmitLoading(loading) {
        this.isSubmitting = loading;
        const submitBtn = document.getElementById('submitBtn');
        
        if (!submitBtn) return;
        
        if (loading) {
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
            submitBtn.setAttribute('aria-busy', 'true');
        } else {
            submitBtn.disabled = false;
            submitBtn.classList.remove('loading');
            submitBtn.setAttribute('aria-busy', 'false');
        }
    }

    // ===== 通知系統 =====
    showNotification(message, type = 'info', duration = 5000) {
        // 移除舊通知
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // 創建新通知
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getFeedbackIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        // 添加樣式
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '16px',
            borderRadius: '12px',
            background: type === 'error' ? '#fee2e2' : type === 'success' ? '#dcfce7' : '#dbeafe',
            border: `1px solid ${type === 'error' ? '#fecaca' : type === 'success' ? '#bbf7d0' : '#bfdbfe'}`,
            color: type === 'error' ? '#991b1b' : type === 'success' ? '#166534' : '#1e40af',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            zIndex: '9999',
            animation: 'slideInRight 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            maxWidth: '400px'
        });

        document.body.appendChild(notification);

        // 自動移除
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.animation = 'slideOutRight 0.3s ease';
                    setTimeout(() => notification.remove(), 300);
                }
            }, duration);
        }

        // 通知屏幕閱讀器
        this.announceToScreenReader(message);
    }

    // ===== 工具函數 =====
    getFieldValue(fieldName) {
        const element = document.getElementById(`id_${fieldName}`);
        return element ? element.value.trim() : '';
    }

    async fetchWithRetry(url, options = {}, params = {}) {
        const searchParams = new URLSearchParams(params);
        const fullUrl = params ? `${url}?${searchParams}` : url;
        
        let lastError;
        for (let i = 0; i < 3; i++) {
            try {
                const response = await fetch(fullUrl, options);
                if (response.ok) {
                    return response;
                }
                throw new Error(`HTTP ${response.status}`);
            } catch (error) {
                lastError = error;
                if (i < 2) {
                    await this.delay(1000 * (i + 1)); // 指數退避
                }
            }
        }
        throw lastError;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    animateUpdate(element) {
        if (!element || !this.modernBrowser) return;
        
        element.style.animation = 'none';
        element.offsetHeight; // 觸發重排
        element.style.animation = 'fieldUpdate 0.3s ease';
    }

    scrollToElement(element) {
        if (!element) return;
        
        const rect = element.getBoundingClientRect();
        const offset = window.pageYOffset + rect.top - 100;
        
        window.scrollTo({
            top: offset,
            behavior: 'smooth'
        });
    }

    // ===== 幫助面板 =====
    toggleHelpPanel() {
        const helpPanel = document.getElementById('helpPanel');
        if (!helpPanel) return;
        
        const isOpen = helpPanel.classList.contains('open');
        
        if (isOpen) {
            helpPanel.classList.remove('open');
            this.announceToScreenReader('幫助面板已關閉');
        } else {
            helpPanel.classList.add('open');
            this.announceToScreenReader('幫助面板已開啟');
            
            // 焦點到第一個可聚焦元素
            const firstFocusable = helpPanel.querySelector('button, [tabindex]');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 100);
            }
        }
    }

    // ===== 錯誤處理 =====
    handleGlobalError(event) {
        console.error('全局錯誤:', event.error);
        
        // 不干擾用戶，只在控制台記錄
        if (this.isSubmitting) {
            this.setSubmitLoading(false);
            this.showNotification('發生未預期的錯誤，請重試', 'error');
        }
    }

    // ===== 清理 =====
    destroy() {
        // 清理定時器
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
        
        // 移除事件監聽器
        // 注意：在實際應用中，你可能需要保存監聽器引用以便正確移除
        console.log('預約表單控制器已清理');
    }
}

// ===== 全局樣式注入 =====
function injectGlobalStyles() {
    if (document.getElementById('appointment-dynamic-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'appointment-dynamic-styles';
    style.textContent = `
        /* 動態注入的樣式 */
        @keyframes slideInRight {
            0% { transform: translateX(100%); opacity: 0; }
            100% { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            0% { transform: translateX(0); opacity: 1; }
            100% { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes fieldUpdate {
            0% { border-color: #3b82f6; transform: scale(1); }
            50% { border-color: #22c55e; transform: scale(1.02); }
            100% { border-color: #e2e8f0; transform: scale(1); }
        }
        
        .notification {
            animation: slideInRight 0.3s ease;
        }
        
        .field-feedback {
            transition: all 0.3s ease;
        }
        
        .loading-overlay {
            backdrop-filter: blur(4px);
        }
        
        /* 高對比模式支援 */
        @media (prefers-contrast: high) {
            .modern-input-wrapper,
            .modern-select-wrapper,
            .modern-textarea-wrapper {
                border: 2px solid #000 !important;
            }
        }
        
        /* 減少動畫偏好 */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
    `;
    document.head.appendChild(style);
}

// ===== 初始化 =====
function initializeAppointmentForm() {
    // 檢查是否為預約頁面
    if (!document.getElementById('appointmentForm')) {
        return;
    }

    try {
        injectGlobalStyles();
        
        // 創建控制器實例
        window.appointmentController = new AppointmentFormController();
        
        console.log('✅ 現代化預約表單已完全初始化');
        
    } catch (error) {
        console.error('❌ 預約表單初始化失敗:', error);
        
        // 降級處理 - 確保基本功能可用
        const form = document.getElementById('appointmentForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                const timeSlot = document.getElementById('id_time_slot');
                if (!timeSlot || !timeSlot.value) {
                    e.preventDefault();
                    alert('請選擇預約時段');
                    return false;
                }
            });
        }
    }
}

// ===== 多種初始化方式 =====
// 1. DOM 內容載入完成
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAppointmentForm);
} else {
    initializeAppointmentForm();
}

// 2. 頁面完全載入
window.addEventListener('load', () => {
    // 確保所有資源都已載入
    setTimeout(() => {
        if (window.appointmentController) {
            window.appointmentController.announceToScreenReader('預約表單已完全載入');
        }
    }, 500);
});

// 3. jQuery 支援（如果可用）
if (typeof $ !== 'undefined') {
    $(document).ready(function() {
        console.log('jQuery 可用，增強功能已啟用');
        
        // 額外的 jQuery 增強功能
        if (window.appointmentController) {
            // 平滑滾動
            $('a[href^="#"]').on('click', function(e) {
                e.preventDefault();
                const target = $(this.getAttribute('href'));
                if (target.length) {
                    $('html, body').animate({
                        scrollTop: target.offset().top - 100
                    }, 500);
                }
            });
        }
    });
}

// ===== 匯出給其他腳本使用 =====
window.AppointmentFormUtils = {
    showNotification: (message, type, duration) => {
        if (window.appointmentController) {
            window.appointmentController.showNotification(message, type, duration);
        }
    },
    
    validateForm: () => {
        if (window.appointmentController) {
            return window.appointmentController.validateAllFields();
        }
        return true;
    },
    
    setStep: (step) => {
        if (window.appointmentController) {
            window.appointmentController.setStep(step);
        }
    }
};

console.log('🎉 預約表單 JavaScript 模組已載入完成');