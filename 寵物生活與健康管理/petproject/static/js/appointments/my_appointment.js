/**
 * 我的預約管理 JavaScript 控制器
 * 提供流暢的用戶體驗和動畫效果
 */

class MyAppointmentsController {
    constructor() {
        this.currentFilter = 'upcoming';
        this.appointments = [];
        this.isLoading = false;
        
        this.init();
    }

    // ===== 初始化 =====
    init() {
        console.log('🚀 預約管理系統初始化...');
        
        this.setupEventListeners();
        this.setupAnimations();
        this.loadAppointments();
        this.initializeTooltips();
        
        console.log('✅ 預約管理系統初始化完成');
    }

    // ===== 事件監聽器 =====
    setupEventListeners() {
        // 取消預約表單提交
        document.querySelectorAll('.cancel-form').forEach(form => {
            form.addEventListener('submit', (e) => this.handleCancelSubmit(e));
        });

        // 確認對話框
        document.querySelectorAll('.cancel-button').forEach(button => {
            button.addEventListener('click', (e) => this.handleCancelClick(e));
        });

        // 卡片懸停效果
        document.querySelectorAll('.appointment-card-modern').forEach(card => {
            this.setupCardHoverEffects(card);
        });

        // 鍵盤快捷鍵
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // 滾動動畫
        this.setupScrollAnimations();
    }

    setupCardHoverEffects(card) {
        card.addEventListener('mouseenter', () => {
            this.animateCardEntry(card);
        });

        card.addEventListener('mouseleave', () => {
            this.animateCardExit(card);
        });
    }

    // ===== 篩選功能 =====
    filterAppointments(status) {
        if (this.isLoading) return;
        
        console.log(`🔍 篩選預約: ${status}`);
        
        // 更新活動標籤
        this.updateActiveTab(status);
        
        // 顯示載入狀態
        this.showLoadingState();
        
        // 執行篩選
        setTimeout(() => {
            this.executeFilter(status);
        }, 300);
    }

    updateActiveTab(status) {
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`[onclick="filterAppointments('${status}')"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            this.animateTabSwitch(activeTab);
        }
    }

    executeFilter(status) {
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('status', status);
        
        // 使用 AJAX 或頁面重載
        if (this.supportsHistory()) {
            this.loadAppointmentsAjax(status);
        } else {
            window.location.href = currentUrl.toString();
        }
    }

    async loadAppointmentsAjax(status) {
        try {
            const response = await fetch(`${window.location.pathname}?status=${status}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const html = await response.text();
                this.updateAppointmentsGrid(html);
            }
        } catch (error) {
            console.error('載入預約失敗:', error);
            // 降級到頁面重載
            this.executeFilter(status);
        } finally {
            this.hideLoadingState();
        }
    }

    // ===== 取消預約處理 =====
    handleCancelClick(event) {
        event.preventDefault();
        
        const button = event.currentTarget;
        const appointmentId = this.extractAppointmentId(button);
        const petName = this.extractPetName(button);
        
        this.showCancelConfirmation(appointmentId, petName, button);
    }

    showCancelConfirmation(appointmentId, petName, button) {
        const modal = this.createCancelModal(appointmentId, petName);
        document.body.appendChild(modal);
        
        // 顯示動畫
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
        
        // 設置事件監聽器
        this.setupModalEvents(modal, appointmentId, button);
    }

    createCancelModal(appointmentId, petName) {
        const modal = document.createElement('div');
        modal.className = 'cancel-modal-overlay';
        modal.innerHTML = `
            <div class="cancel-modal">
                <div class="modal-header">
                    <h3>確認取消預約</h3>
                    <button class="modal-close" type="button">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="warning-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <p>確定要取消 <strong>${petName}</strong> 的預約嗎？</p>
                    <p class="text-muted">此操作無法復原，建議您提前通知診所。</p>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary modal-cancel" type="button">
                        <i class="fas fa-arrow-left"></i>
                        <span>返回</span>
                    </button>
                    <button class="btn-danger modal-confirm" type="button">
                        <i class="fas fa-times-circle"></i>
                        <span>確認取消</span>
                    </button>
                </div>
            </div>
        `;
        
        // 添加樣式
        this.injectModalStyles();
        
        return modal;
    }

    setupModalEvents(modal, appointmentId, originalButton) {
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = modal.querySelector('.modal-cancel');
        const confirmBtn = modal.querySelector('.modal-confirm');
        
        // 關閉事件
        [closeBtn, cancelBtn].forEach(btn => {
            btn.addEventListener('click', () => this.closeModal(modal));
        });
        
        // 點擊背景關閉
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(modal);
            }
        });
        
        // 確認取消
        confirmBtn.addEventListener('click', () => {
            this.executeCancelAppointment(appointmentId, modal, originalButton);
        });
        
        // ESC 鍵關閉
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.closeModal(modal);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    async executeCancelAppointment(appointmentId, modal, originalButton) {
        const confirmBtn = modal.querySelector('.modal-confirm');
        
        try {
            // 顯示載入狀態
            this.setButtonLoading(confirmBtn, true);
            
            // 執行取消請求
            const success = await this.cancelAppointmentRequest(appointmentId);
            
            if (success) {
                this.showSuccessNotification('預約已成功取消');
                this.removeAppointmentCard(originalButton);
                this.closeModal(modal);
            } else {
                throw new Error('取消失敗');
            }
            
        } catch (error) {
            console.error('取消預約錯誤:', error);
            this.showErrorNotification('取消失敗，請稍後重試');
        } finally {
            this.setButtonLoading(confirmBtn, false);
        }
    }

    async cancelAppointmentRequest(appointmentId) {
        try {
            const csrfToken = this.getCSRFToken();
            const response = await fetch(`/appointments/${appointmentId}/cancel/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            return response.ok;
        } catch (error) {
            console.error('網路錯誤:', error);
            return false;
        }
    }

    // ===== 動畫效果 =====
    setupAnimations() {
        // 入場動畫
        this.animateCardsEntry();
        
        // 滾動觸發動畫
        this.setupScrollAnimations();
        
        // 過濾器動畫
        this.setupFilterAnimations();
    }

    animateCardsEntry() {
        const cards = document.querySelectorAll('.appointment-card-modern');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
            card.classList.add('animate-entry');
        });
    }

    animateCardEntry(card) {
        card.style.transform = 'translateY(-8px) scale(1.02)';
        card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    }

    animateCardExit(card) {
        card.style.transform = 'translateY(0) scale(1)';
    }

    animateTabSwitch(tab) {
        tab.style.transform = 'scale(1.05)';
        setTimeout(() => {
            tab.style.transform = 'scale(1)';
        }, 150);
    }

    removeAppointmentCard(button) {
        const card = button.closest('.appointment-card-modern');
        if (card) {
            card.style.animation = 'slideOutUp 0.4s ease forwards';
            setTimeout(() => {
                card.remove();
                this.checkEmptyState();
            }, 400);
        }
    }

    // ===== 工具函數 =====
    extractAppointmentId(button) {
        const form = button.closest('form');
        return form ? form.action.split('/').slice(-2, -1)[0] : null;
    }

    extractPetName(button) {
        const card = button.closest('.appointment-card-modern');
        const nameElement = card?.querySelector('.pet-name');
        return nameElement?.textContent.trim() || '寵物';
    }

    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        
        const cookie = document.cookie.split(';')
            .find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    closeModal(modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            if (modal.parentElement) {
                document.body.removeChild(modal);
            }
        }, 300);
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.innerHTML = `
                <div class="loading-spinner"></div>
                <span>處理中...</span>
            `;
        } else {
            button.disabled = false;
            button.innerHTML = `
                <i class="fas fa-times-circle"></i>
                <span>確認取消</span>
            `;
        }
    }

    // ===== 通知系統 =====
    showSuccessNotification(message) {
        this.showNotification(message, 'success');
    }

    showErrorNotification(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        // 添加到頁面
        document.body.appendChild(notification);

        // 設置樣式
        this.styleNotification(notification, type);

        // 自動關閉
        setTimeout(() => {
            this.removeNotification(notification);
        }, 5000);

        // 手動關閉
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.removeNotification(notification);
        });
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            info: 'info-circle',
            warning: 'exclamation-circle'
        };
        return icons[type] || 'info-circle';
    }

    styleNotification(notification, type) {
        const colors = {
            success: { bg: '#dcfce7', border: '#bbf7d0', text: '#166534' },
            error: { bg: '#fee2e2', border: '#fecaca', text: '#991b1b' },
            info: { bg: '#dbeafe', border: '#bfdbfe', text: '#1e40af' },
            warning: { bg: '#fef3c7', border: '#fde68a', text: '#92400e' }
        };

        const color = colors[type] || colors.info;
        
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: color.bg,
            border: `1px solid ${color.border}`,
            color: color.text,
            padding: '16px',
            borderRadius: '12px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            zIndex: '9999',
            maxWidth: '400px',
            animation: 'slideInRight 0.3s ease'
        });
    }

    removeNotification(notification) {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentElement) {
                document.body.removeChild(notification);
            }
        }, 300);
    }

    // ===== 狀態管理 =====
    showLoadingState() {
        this.isLoading = true;
        const grid = document.querySelector('.appointments-grid');
        if (grid) {
            grid.style.opacity = '0.6';
            grid.style.pointerEvents = 'none';
        }
    }

    hideLoadingState() {
        this.isLoading = false;
        const grid = document.querySelector('.appointments-grid');
        if (grid) {
            grid.style.opacity = '1';
            grid.style.pointerEvents = 'auto';
        }
    }

    checkEmptyState() {
        const cards = document.querySelectorAll('.appointment-card-modern');
        const emptyState = document.querySelector('.empty-state-modern');
        
        if (cards.length === 0 && !emptyState) {
            this.showEmptyState();
        }
    }

    showEmptyState() {
        const grid = document.querySelector('.appointments-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="empty-state-modern">
                    <div class="empty-icon-modern">
                        <i class="fas fa-calendar-times"></i>
                    </div>
                    <h3 class="empty-title-modern">暫無預約記錄</h3>
                    <p class="empty-description-modern">
                        您目前沒有任何預約記錄<br>
                        立即為您的寵物預約健康檢查吧！
                    </p>
                    <a href="/pets/" class="cta-button">
                        <i class="fas fa-plus"></i>
                        <span>立即預約</span>
                    </a>
                </div>
            `;
        }
    }

    // ===== 工具方法 =====
    supportsHistory() {
        return !!(window.history && window.history.pushState);
    }

    setupScrollAnimations() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-visible');
                    }
                });
            }, { threshold: 0.1 });

            document.querySelectorAll('.appointment-card-modern').forEach(card => {
                observer.observe(card);
            });
        }
    }

    injectModalStyles() {
        if (document.getElementById('cancel-modal-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'cancel-modal-styles';
        styles.textContent = `
            .cancel-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(8px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .cancel-modal-overlay.show {
                opacity: 1;
            }
            
            .cancel-modal {
                background: white;
                border-radius: 1.5rem;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                max-width: 500px;
                width: 90%;
                transform: scale(0.95);
                transition: transform 0.3s ease;
            }
            
            .cancel-modal-overlay.show .cancel-modal {
                transform: scale(1);
            }
            
            .modal-header {
                padding: 1.5rem 1.5rem 1rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #e5e7eb;
            }
            
            .modal-header h3 {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 600;
                color: #1f2937;
            }
            
            .modal-close {
                background: none;
                border: none;
                font-size: 1.25rem;
                color: #6b7280;
                cursor: pointer;
                padding: 0.25rem;
                border-radius: 0.375rem;
                transition: all 0.2s ease;
            }
            
            .modal-close:hover {
                background: #f3f4f6;
                color: #374151;
            }
            
            .modal-body {
                padding: 1.5rem;
                text-align: center;
            }
            
            .warning-icon {
                width: 64px;
                height: 64px;
                margin: 0 auto 1rem;
                background: #fef3c7;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #d97706;
                font-size: 1.5rem;
            }
            
            .modal-footer {
                padding: 1rem 1.5rem 1.5rem;
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
            }
            
            .btn-secondary, .btn-danger {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 0.75rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .btn-secondary {
                background: #f3f4f6;
                color: #374151;
            }
            
            .btn-secondary:hover {
                background: #e5e7eb;
            }
            
            .btn-danger {
                background: #ef4444;
                color: white;
            }
            
            .btn-danger:hover {
                background: #dc2626;
            }
            
            .loading-spinner {
                width: 16px;
                height: 16px;
                border: 2px solid #ffffff;
                border-top: 2px solid transparent;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes slideInRight {
                0% { transform: translateX(100%); opacity: 0; }
                100% { transform: translateX(0); opacity: 1; }
            }
            
            @keyframes slideOutRight {
                0% { transform: translateX(0); opacity: 1; }
                100% { transform: translateX(100%); opacity: 0; }
            }
            
            @keyframes slideOutUp {
                0% { transform: translateY(0); opacity: 1; }
                100% { transform: translateY(-20px); opacity: 0; }
            }
        `;
        document.head.appendChild(styles);
    }

    handleKeyboard(event) {
        // 按 R 鍵重新載入
        if (event.key === 'r' && !event.ctrlKey && !event.metaKey) {
            const activeElement = document.activeElement;
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                window.location.reload();
            }
        }
    }
}

// ===== 全局函數 =====
function filterAppointments(status) {
    if (window.appointmentsController) {
        window.appointmentsController.filterAppointments(status);
    } else {
        // 降級處理
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('status', status);
        window.location.href = currentUrl.toString();
    }
}

// ===== 初始化 =====
function initializeMyAppointments() {
    // 檢查是否在正確的頁面
    if (!document.querySelector('.appointments-wrapper')) {
        return;
    }

    try {
        // 創建控制器實例
        window.appointmentsController = new MyAppointmentsController();
        
        console.log('✅ 我的預約管理系統已完全初始化');
        
    } catch (error) {
        console.error('❌ 預約管理系統初始化失敗:', error);
        
        // 確保基本功能可用
        window.filterAppointments = filterAppointments;
    }
}

// ===== 多種初始化方式 =====
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMyAppointments);
} else {
    initializeMyAppointments();
}

// jQuery 支援
if (typeof $ !== 'undefined') {
    $(document).ready(() => {
        console.log('jQuery 增強功能已啟用');
    });
}

console.log('🎉 我的預約管理 JavaScript 模組已載入完成');