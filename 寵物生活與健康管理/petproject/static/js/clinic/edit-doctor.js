// static/js/clinic/edit-doctor.js

// 等待頁面載入完成後執行
document.addEventListener('DOMContentLoaded', function() {
    
    // ========== 初始化所有功能 ==========
    initCharCounter();
    initMultiSelect();
    initPreviewModal();
    initFormValidation();
    initTooltips();
    
    // ========== 多選下拉組件 ==========
    function initMultiSelect() {
        const container = document.getElementById('specializationContainer');
        const trigger = document.getElementById('specializationTrigger');
        const dropdown = document.getElementById('specializationDropdown');
        const searchInput = document.getElementById('specializationSearch');
        const optionsContainer = document.getElementById('specializationOptions');
        const selectedItemsContainer = document.getElementById('selectedItems');
        const hiddenInput = document.getElementById('specializationHidden');
        
        if (!container || !trigger || !dropdown) return;
        
        let selectedValues = [];
        
        // 初始化已選擇的值
        const initialValue = hiddenInput.value;
        if (initialValue) {
            // 如果有初始值，解析並設置選中狀態
            const initialSpecializations = initialValue.split(',').map(s => s.trim()).filter(s => s);
            selectedValues = [];
            
            // 找到對應的選項並標記為選中
            const options = optionsContainer.querySelectorAll('input[type="checkbox"]');
            options.forEach(option => {
                const optionText = option.parentElement.querySelector('.option-text').textContent;
                if (initialSpecializations.includes(optionText)) {
                    option.checked = true;
                    selectedValues.push({
                        value: option.value,
                        text: optionText
                    });
                }
            });
            updateSelectedDisplay();
        }
        
        // 點擊觸發器開關下拉選單
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleDropdown();
        });
        
        // 處理選項選擇
        optionsContainer.addEventListener('change', function(e) {
            if (e.target.type === 'checkbox') {
                const checkbox = e.target;
                const optionText = checkbox.parentElement.querySelector('.option-text').textContent;
                const optionItem = checkbox.parentElement;
                
                if (checkbox.checked) {
                    // 添加到已選擇列表
                    selectedValues.push({
                        value: checkbox.value,
                        text: optionText
                    });
                    optionItem.classList.add('selected');
                } else {
                    // 從已選擇列表移除
                    selectedValues = selectedValues.filter(item => item.value !== checkbox.value);
                    optionItem.classList.remove('selected');
                }
                
                updateSelectedDisplay();
                updateHiddenInput();
            }
        });
        
        // 搜尋功能
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const options = optionsContainer.querySelectorAll('.option-item');
            
            options.forEach(option => {
                const text = option.querySelector('.option-text').textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    option.classList.remove('hidden');
                } else {
                    option.classList.add('hidden');
                }
            });
        });
        
        // 點擊外部關閉下拉選單
        document.addEventListener('click', function(e) {
            if (!container.contains(e.target)) {
                closeDropdown();
            }
        });
        
        // 開關下拉選單
        function toggleDropdown() {
            if (dropdown.classList.contains('show')) {
                closeDropdown();
            } else {
                openDropdown();
            }
        }
        
        // 打開下拉選單
        function openDropdown() {
            dropdown.classList.add('show');
            trigger.classList.add('active');
            searchInput.focus();
        }
        
        // 關閉下拉選單
        function closeDropdown() {
            dropdown.classList.remove('show');
            trigger.classList.remove('active');
            searchInput.value = '';
            // 重置搜尋結果
            const options = optionsContainer.querySelectorAll('.option-item');
            options.forEach(option => option.classList.remove('hidden'));
        }
        
        // 更新已選擇項目的顯示
        function updateSelectedDisplay() {
            if (selectedValues.length === 0) {
                selectedItemsContainer.innerHTML = '<span class="placeholder">請選擇專科領域</span>';
            } else {
                selectedItemsContainer.innerHTML = selectedValues.map(item => `
                    <div class="selected-tag" data-value="${item.value}">
                        <span>${item.text}</span>
                        <div class="remove-tag" onclick="removeSelectedItem('${item.value}')">
                            <i class="fas fa-times"></i>
                        </div>
                    </div>
                `).join('');
            }
        }
        
        // 更新隱藏欄位的值
        function updateHiddenInput() {
            const selectedTexts = selectedValues.map(item => item.text);
            hiddenInput.value = selectedTexts.join(', ');
        }
        
        // 移除選中項目的全域函數
        window.removeSelectedItem = function(value) {
            // 取消勾選對應的複選框
            const checkbox = optionsContainer.querySelector(`input[value="${value}"]`);
            if (checkbox) {
                checkbox.checked = false;
                checkbox.parentElement.classList.remove('selected');
            }
            
            // 從已選擇列表移除
            selectedValues = selectedValues.filter(item => item.value !== value);
            
            updateSelectedDisplay();
            updateHiddenInput();
        };
    }
    
    // ========== 字數計數器 ==========
    function initCharCounter() {
        const bioTextarea = document.getElementById('bio');
        const charCounter = document.getElementById('bioCounter');
        const maxLength = 500;
        
        if (bioTextarea && charCounter) {
            // 初始化計數
            updateCharCount();
            
            // 監聽輸入事件
            bioTextarea.addEventListener('input', updateCharCount);
            
            function updateCharCount() {
                const currentLength = bioTextarea.value.length;
                charCounter.textContent = currentLength;
                
                // 更新樣式
                const counterElement = charCounter.parentElement;
                counterElement.classList.remove('warning', 'danger');
                
                if (currentLength > maxLength * 0.9) {
                    counterElement.classList.add('danger');
                } else if (currentLength > maxLength * 0.8) {
                    counterElement.classList.add('warning');
                }
                
                // 限制最大長度
                if (currentLength > maxLength) {
                    bioTextarea.value = bioTextarea.value.substring(0, maxLength);
                    charCounter.textContent = maxLength;
                }
            }
        }
    }
    
    // ========== 預覽模態視窗 ==========
    function initPreviewModal() {
        const previewBtn = document.getElementById('previewBtn');
        const previewModal = document.getElementById('previewModal');
        const closePreview = document.getElementById('closePreview');
        const closePreviewBtn = document.getElementById('closePreviewBtn');
        
        if (previewBtn && previewModal) {
            previewBtn.addEventListener('click', function(e) {
                e.preventDefault();
                generatePreview();
                showModal(previewModal);
            });
            
            // 關閉預覽
            [closePreview, closePreviewBtn].forEach(btn => {
                if (btn) {
                    btn.addEventListener('click', function() {
                        hideModal(previewModal);
                    });
                }
            });
        }
    }
    
    // 生成預覽內容
    function generatePreview() {
        const previewContainer = document.getElementById('doctorPreview');
        const formData = collectFormData();
        
        previewContainer.innerHTML = `
            <div class="doctor-preview-content">
                <div class="preview-header">
                    <div class="preview-avatar">
                        <i class="fas fa-user-md"></i>
                    </div>
                    <div class="preview-info">
                        <h4>${formData.first_name || '未填寫姓名'}</h4>
                        <p>${formData.email || '未填寫信箱'}</p>
                        ${formData.phone_number ? `<p><i class="fas fa-phone"></i> ${formData.phone_number}</p>` : ''}
                    </div>
                </div>
                
                <div class="preview-sections">
                    <div class="preview-section">
                        <h5><i class="fas fa-certificate"></i> 專業資格</h5>
                        ${formData.vet_license_number ? `<p><strong>執照號碼：</strong>${formData.vet_license_number}</p>` : '<p>未填寫執照號碼</p>'}
                        ${formData.years_of_experience ? `<p><strong>年資：</strong>${formData.years_of_experience} 年</p>` : ''}
                    </div>
                    
                    ${formData.specialization ? `
                    <div class="preview-section">
                        <h5><i class="fas fa-stethoscope"></i> 專科領域</h5>
                        <div class="preview-specializations">
                            ${formData.specialization.split(',').map(spec => 
                                `<span class="preview-specialty">${spec.trim()}</span>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${formData.bio ? `
                    <div class="preview-section">
                        <h5><i class="fas fa-quote-left"></i> 醫師簡介</h5>
                        <p>${formData.bio}</p>
                    </div>
                    ` : ''}
                    
                    <div class="preview-section">
                        <h5><i class="fas fa-cog"></i> 系統設定</h5>
                        <div class="permission-status">
                            <p><span class="status-label">帳號狀態：</span>
                               <span class="status-value ${formData.is_active ? 'active' : 'inactive'}">${formData.is_active ? '啟用' : '停用'}</span></p>
                            <p><span class="status-label">獸醫師身份：</span>
                               <span class="status-value ${formData.is_active_veterinarian ? 'active' : 'inactive'}">${formData.is_active_veterinarian ? '啟用' : '停用'}</span></p>
                            <p><span class="status-label">管理員權限：</span>
                               <span class="status-value ${formData.is_clinic_admin ? 'active' : 'inactive'}">${formData.is_clinic_admin ? '是' : '否'}</span></p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 收集表單資料
    function collectFormData() {
        const form = document.getElementById('doctorForm');
        const formData = new FormData(form);
        
        // 基本資料
        const data = {
            first_name: formData.get('first_name') || '',
            email: formData.get('email') || '',
            phone_number: formData.get('phone_number') || '',
            vet_license_number: formData.get('vet_license_number') || '',
            years_of_experience: formData.get('years_of_experience') || '',
            specialization: formData.get('specialization') || '',
            bio: formData.get('bio') || '',
            is_active: formData.has('is_active'),
            is_active_veterinarian: formData.has('is_active_veterinarian'),
            is_clinic_admin: formData.has('is_clinic_admin')
        };
        
        return data;
    }
    
    // ========== 表單驗證 ==========
    function initFormValidation() {
        const form = document.getElementById('doctorForm');
        const saveBtn = document.getElementById('saveBtn');
        
        if (form) {
            // 即時驗證
            const requiredFields = form.querySelectorAll('input[required], select[required]');
            requiredFields.forEach(field => {
                field.addEventListener('blur', function() {
                    validateField(this);
                });
                
                field.addEventListener('input', function() {
                    clearFieldError(this);
                });
            });
            
            // 表單提交驗證
            form.addEventListener('submit', function(e) {
                if (!validateForm()) {
                    e.preventDefault();
                    showMessage('請檢查並修正表單中的錯誤', 'error');
                    return;
                }
                
                // 顯示提交中狀態
                if (saveBtn) {
                    saveBtn.disabled = true;
                    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 儲存中...';
                }
            });
        }
    }
    
    // 驗證單個欄位
    function validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        // 必填驗證
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = '此欄位為必填';
        }
        
        // 電子信箱格式驗證
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = '請輸入有效的電子信箱格式';
            }
        }
        
        // 電話格式驗證（台灣格式）
        if (field.type === 'tel' && value) {
            const phoneRegex = /^09\d{8}$/;
            if (!phoneRegex.test(value.replace(/[-\s]/g, ''))) {
                isValid = false;
                errorMessage = '請輸入有效的台灣手機號碼格式（09xxxxxxxx）';
            }
        }
        
        // 顯示錯誤或清除錯誤
        if (!isValid) {
            showFieldError(field, errorMessage);
        } else {
            clearFieldError(field);
        }
        
        return isValid;
    }
    
    // 驗證整個表單
    function validateForm() {
        const form = document.getElementById('doctorForm');
        const requiredFields = form.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    // 顯示欄位錯誤
    function showFieldError(field, message) {
        clearFieldError(field);
        
        field.classList.add('error');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        
        field.parentNode.appendChild(errorDiv);
    }
    
    // 清除欄位錯誤
    function clearFieldError(field) {
        field.classList.remove('error');
        
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }
    
    // ========== 工具提示功能 ==========
    function initTooltips() {
        // 為有 title 屬性的元素添加工具提示
        const elementsWithTooltips = document.querySelectorAll('[title]');
        
        elementsWithTooltips.forEach(element => {
            // 可以使用第三方庫如 Tippy.js 或自己實現
            // 這裡先保留原生 title 屬性
        });
    }
    
    // ========== 工具函數 ==========
    
    // 顯示模態視窗
    function showModal(modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    // 隱藏模態視窗
    function hideModal(modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    // 顯示訊息提示
    function showMessage(message, type = 'info') {
        const messageToast = document.createElement('div');
        messageToast.className = `message-toast message-${type}`;
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        messageToast.innerHTML = `
            <div class="message-content">
                <i class="fas ${icons[type]}"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="message-close">&times;</button>
        `;
        
        document.body.appendChild(messageToast);
        
        // 關閉按鈕
        const closeBtn = messageToast.querySelector('.message-close');
        closeBtn.addEventListener('click', function() {
            removeMessage(messageToast);
        });
        
        // 自動關閉
        setTimeout(() => {
            removeMessage(messageToast);
        }, 5000);
    }
    
    // 移除訊息提示
    function removeMessage(messageElement) {
        messageElement.classList.add('fade-out');
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, 300);
    }
    
    // 點擊模態視窗外部關閉
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-overlay')) {
            hideModal(e.target);
        }
    });
    
    // ESC 鍵關閉模態視窗
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal-overlay.show');
            if (openModal) {
                hideModal(openModal);
            }
        }
    });
    
    // ========== 頁面初始化完成提示 ==========
//     console.log('醫師編輯頁面功能已初始化完成');
    
});

// ========== 表單錯誤樣式 ==========
const style = document.createElement('style');
style.textContent = `
    .form-control.error {
        border-color: var(--danger-color) !important;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
    }
    
    .field-error {
        color: var(--danger-color);
        font-size: 0.75rem;
        margin-top: var(--spacing-xs);
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
    }
    
    .field-error i {
        font-size: 0.875rem;
    }
    
    .preview-specializations {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-sm);
    }
    
    .preview-specialty {
        background: var(--primary-color);
        color: white;
        padding: var(--spacing-xs) var(--spacing-md);
        border-radius: var(--radius-lg);
        font-size: 0.75rem;
        font-weight: 500;
    }
`;
document.head.appendChild(style);