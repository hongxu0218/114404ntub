// static/js/medical-theme.js - 醫療風格主題控制器

class MedicalThemeController {
    constructor() {
        this.themes = {
            'veterinarian': 'vet-theme',      // 獸醫師 - 專業醫療藍
            'clinic_admin': 'admin-theme',     // 診所管理員 - 管理紫
            'pet_owner': 'owner-theme',        // 飼主 - 溫暖橙
            'staff': 'vet-theme',              // 員工 - 使用獸醫師主題
            'default': 'owner-theme'           // 預設 - 飼主主題
        };
        
        this.currentTheme = null;
        this.init();
    }
    
    init() {
        // 從DOM獲取用戶角色資訊
        const userRole = this.getUserRole();
        
        // 應用對應主題
        this.applyTheme(userRole);
        
        // 綁定主題切換事件
        this.bindThemeEvents();
        
        // 初始化醫療風格組件
        this.initMedicalComponents();
        
        // console.log(`🏥 Medical Theme Initialized: ${userRole} -> ${this.currentTheme}`);
    }
    
    getUserRole() {
        // 從DOM元素獲取用戶角色
        const userData = document.querySelector('[data-user-authenticated]');
        if (!userData) return 'default';
        
        const userProfile = userData.getAttribute('data-user-profile');
        const userType = userData.getAttribute('data-user-type');
        
        // 根據profile和type判斷角色
        if (userProfile === 'clinic_admin' || userType === 'clinic_admin') {
            return 'clinic_admin';
        } else if (userProfile === 'veterinarian' || userType === 'veterinarian') {
            return 'veterinarian';
        } else if (userProfile === 'vet_doctor' || userType === 'vet_doctor') {
            return 'veterinarian';
        } else if (userProfile === 'pet_owner' || userType === 'pet_owner') {
            return 'pet_owner';
        } else if (userProfile === 'staff') {
            return 'staff';
        }
        
        // 根據URL路徑判斷
        const path = window.location.pathname;
        if (path.includes('/vet/') || path.includes('/clinic/')) {
            return 'veterinarian';
        } else if (path.includes('/admin/')) {
            return 'clinic_admin';
        }
        
        return 'default';
    }
    
    applyTheme(userRole) {
        const themeClass = this.themes[userRole] || this.themes.default;
        
        // 移除所有主題類別
        Object.values(this.themes).forEach(theme => {
            document.body.classList.remove(theme);
        });
        
        // 應用新主題
        document.body.classList.add(themeClass);
        this.currentTheme = themeClass;
        
        // 更新頁面元素樣式
        this.updatePageElements(userRole);
    }
    
    updatePageElements(userRole) {
        // 更新導航欄
        this.updateNavbar(userRole);
        
        // 更新按鈕樣式
        this.updateButtons();
        
        // 更新卡片樣式
        this.updateCards();
        
        // 更新表單樣式
        this.updateForms();
        
        // 更新表格樣式
        this.updateTables();
    }
    
    updateNavbar(userRole) {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;
        
        // 添加醫療導航欄樣式
        navbar.classList.add('medical-navbar');
        
        // 根據角色添加特定樣式
        const roleClass = `navbar-${userRole}`;
        navbar.classList.add(roleClass);
        
        // 更新導航欄內容
        const brandElement = navbar.querySelector('.navbar-brand');
        if (brandElement && userRole === 'veterinarian') {
            // 獸醫師專業標識
            const icon = brandElement.querySelector('i') || document.createElement('i');
            icon.className = 'bi bi-heart-pulse me-2';
            if (!brandElement.querySelector('i')) {
                brandElement.prepend(icon);
            }
        }
    }
    
    updateButtons() {
        // 更新主要按鈕為醫療風格
        const primaryButtons = document.querySelectorAll('.btn-primary:not(.medical-updated)');
        primaryButtons.forEach(btn => {
            btn.classList.add('btn-medical', 'medical-updated');
        });
        
        // 更新輔助按鈕
        const outlineButtons = document.querySelectorAll('.btn-outline-primary:not(.medical-updated)');
        outlineButtons.forEach(btn => {
            btn.classList.add('btn-medical-outline', 'medical-updated');
        });
    }
    
    updateCards() {
        // 更新卡片樣式
        const cards = document.querySelectorAll('.card:not(.medical-updated)');
        cards.forEach(card => {
            card.classList.add('medical-card', 'medical-updated');
            
            // 更新卡片標題
            const cardHeader = card.querySelector('.card-header');
            if (cardHeader) {
                cardHeader.classList.add('medical-card-header');
            }
        });
        
        // 更新統計卡片
        const statsCards = document.querySelectorAll('.stats-card-container .card:not(.stats-updated)');
        statsCards.forEach(card => {
            card.classList.add('stats-card', 'stats-updated');
        });
    }
    
    updateForms() {
        // 更新表單控件
        const formControls = document.querySelectorAll('.form-control:not(.medical-updated)');
        formControls.forEach(control => {
            control.classList.add('medical-input', 'medical-updated');
        });
    }
    
    updateTables() {
        // 更新表格樣式
        const tables = document.querySelectorAll('.table:not(.medical-updated)');
        tables.forEach(table => {
            table.classList.add('medical-table', 'medical-updated');
        });
    }
    
    bindThemeEvents() {
        // 綁定主題切換按鈕事件
        const themeToggle = document.querySelector('[data-theme-toggle]');
        if (themeToggle) {
            themeToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
            });
        }
        
        // 監聽頁面內容變化，動態應用樣式
        this.observeContentChanges();
    }
    
    observeContentChanges() {
        // 使用 MutationObserver 監聽DOM變化
        const observer = new MutationObserver((mutations) => {
            let needsUpdate = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            needsUpdate = true;
                        }
                    });
                }
            });
            
            if (needsUpdate) {
                // 延遲更新，避免過於頻繁
                setTimeout(() => {
                    this.updateButtons();
                    this.updateCards();
                    this.updateForms();
                    this.updateTables();
                }, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    initMedicalComponents() {
        // 初始化狀態指示器
        this.initStatusIndicators();
        
        // 初始化醫療徽章
        this.initMedicalBadges();
        
        // 初始化工具提示
        this.initTooltips();
    }
    
    initStatusIndicators() {
        // 為狀態元素添加指示器
        const statusElements = document.querySelectorAll('[data-status]');
        statusElements.forEach(element => {
            const status = element.getAttribute('data-status');
            const indicator = document.createElement('span');
            indicator.className = `status-indicator status-${status}`;
            
            // 如果元素還沒有指示器，則添加
            if (!element.querySelector('.status-indicator')) {
                element.prepend(indicator);
            }
        });
    }
    
    initMedicalBadges() {
        // 更新徽章樣式
        const badges = document.querySelectorAll('.badge:not(.medical-updated)');
        badges.forEach(badge => {
            badge.classList.add('medical-badge', 'medical-updated');
        });
    }
    
    initTooltips() {
        // 初始化醫療風格的工具提示
        const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipElements.forEach(element => {
            // 使用Bootstrap tooltip，但應用醫療風格
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(element, {
                    customClass: 'medical-tooltip'
                });
            }
        });
    }
    
    toggleTheme() {
        // 手動主題切換（開發模式）
        const themes = Object.values(this.themes);
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        const nextTheme = themes[nextIndex];
        
        // 移除當前主題
        document.body.classList.remove(this.currentTheme);
        
        // 應用新主題
        document.body.classList.add(nextTheme);
        this.currentTheme = nextTheme;
        
        // console.log(`🎨 Theme switched to: ${nextTheme}`);
    }
    
    // 公共API方法
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    setTheme(themeName) {
        if (this.themes[themeName]) {
            this.applyTheme(themeName);
        }
    }
}

// 自動初始化
document.addEventListener('DOMContentLoaded', () => {
    window.medicalTheme = new MedicalThemeController();
});

// 導出控制器類別
window.MedicalThemeController = MedicalThemeController;