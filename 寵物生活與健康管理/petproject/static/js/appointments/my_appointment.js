/**
 * 我的預約管理 - 精簡版本
 * 專注於核心功能，最佳性能
 */

class MyAppointments {
    constructor() {
        this.currentFilter = 'all';
        this.init();
    }

    init() {
        this.setupFilters();
        this.setupDetails();
    }

    // 設置篩選功能
    setupFilters() {
        // 移除所有篩選按鈕的onclick屬性，改用事件委託
        document.querySelectorAll('.filter-tab').forEach(tab => {
            const onclick = tab.getAttribute('onclick');
            if (onclick) {
                const match = onclick.match(/filterAppointments\('([^']+)'\)/);
                if (match) {
                    tab.dataset.filter = match[1];
                    tab.removeAttribute('onclick');
                }
            }
        });

        // 使用事件委託處理篩選
        document.addEventListener('click', (e) => {
            const filterTab = e.target.closest('.filter-tab');
            if (filterTab) {
                const filter = filterTab.dataset.filter;
                if (filter) {
                    this.filterAppointments(filter);
                    return; // 防止事件冒泡
                }
            }

            // 處理詳細資料切換
            const detailBtn = e.target.closest('.view-details');
            if (detailBtn) {
                // console.log('詳細資料按鈕被點擊:', detailBtn);
                this.toggleDetails(detailBtn);
                e.preventDefault();
                e.stopPropagation();
                return;
            }

            // 處理完整醫療記錄按鈕
            const medicalBtn = e.target.closest('.view-medical-record');
            if (medicalBtn) {
                const recordId = medicalBtn.dataset.recordId;
                if (recordId) {
                    this.viewMedicalRecord(recordId);
                }
                e.preventDefault();
                e.stopPropagation();
                return;
            }
        });
    }

    // 設置詳細資料切換
    setupDetails() {
        // 使用事件委託，無需單獨綁定
    }

    // 篩選預約
    filterAppointments(status) {
        this.currentFilter = status;
        
        // 更新按鈕狀態
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.filter === status);
        });

        // 篩選卡片
        const cards = document.querySelectorAll('.appointment-card');
        let visibleCount = 0;

        cards.forEach(card => {
            const shouldShow = this.shouldShowCard(card, status);
            card.style.display = shouldShow ? 'block' : 'none';
            if (shouldShow) visibleCount++;
        });

        // 更新空狀態
        this.updateEmptyState(visibleCount === 0, status);
    }

    // 判斷卡片是否應該顯示
    shouldShowCard(card, status) {
        if (status === 'all') return true;

        const cardStatus = card.dataset.status;
        
        // 狀態分組
        const statusGroups = {
            'active': ['pending', 'confirmed'],
            'completed': ['completed'],
            'cancelled': ['cancelled']
        };

        const group = statusGroups[status];
        return group ? group.includes(cardStatus) : cardStatus === status;
    }

    // 切換詳細資料
    toggleDetails(button) {
        // console.log('toggleDetails 被調用', button);
        
        const card = button.closest('.appointment-card');
        const secondaryInfo = card ? card.querySelector('.secondary-info') : null;
        const icon = button.querySelector('i');
        const span = button.querySelector('span');

        // console.log('找到的元素:', { card, secondaryInfo, icon, span });

        if (!card || !secondaryInfo) {
            console.error('找不到必要的 DOM 元素');
            return;
        }

        if (secondaryInfo.style.display === 'none' || !secondaryInfo.style.display) {
            secondaryInfo.style.display = 'block';
            icon.className = 'fas fa-chevron-up';
            span.textContent = '收起';
            // console.log('展開詳細資料');
        } else {
            secondaryInfo.style.display = 'none';
            icon.className = 'fas fa-info-circle';
            span.textContent = '詳細資料';
            // console.log('收起詳細資料');
        }
    }

    // 查看完整醫療記錄
    viewMedicalRecord(recordId) {
        // 創建模態框顯示完整醫療記錄
        this.createMedicalRecordModal(recordId);
    }

    // 創建醫療記錄模態框
    async createMedicalRecordModal(recordId) {
        try {
            // 獲取醫療記錄詳情 - 需要實作API端點
            const response = await fetch(`/api/medical-records/${recordId}/`);
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || '獲取醫療記錄失敗');
            }

            const record = data.record;

            // 創建模態框
            const modal = document.createElement('div');
            modal.className = 'medical-record-modal';
            modal.innerHTML = `
                <div class="modal-overlay" onclick="window.myAppointments.closeMedicalModal(this.closest('.medical-record-modal'))"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>完整診療記錄</h3>
                        <button class="modal-close" onclick="window.myAppointments.closeMedicalModal(this.closest('.medical-record-modal'))">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="record-details">
                            <div class="detail-section">
                                <h4>基本資訊</h4>
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <span class="detail-label">寵物姓名:</span>
                                        <span class="detail-value">${record.pet_name}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">看診日期:</span>
                                        <span class="detail-value">${record.visit_date}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">主治醫師:</span>
                                        <span class="detail-value">${record.attending_vet || '未指定'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">診所位置:</span>
                                        <span class="detail-value">${record.clinic_location}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="detail-section diagnosis-section">
                                <div class="section-header">
                                    <i class="fas fa-stethoscope"></i>
                                    <h4>診斷內容</h4>
                                </div>
                                <div class="diagnosis-content-card">
                                    <div class="content-text">
                                        ${this.cleanText(record.diagnosis) || '無診斷資訊'}
                                    </div>
                                </div>
                            </div>

                            <div class="detail-section treatment-section">
                                <div class="section-header">
                                    <i class="fas fa-clipboard-list"></i>
                                    <h4>治療計畫</h4>
                                </div>
                                <div class="treatment-content-card">
                                    <div class="content-text">
                                        ${this.formatTreatmentPlan(this.cleanText(record.treatment)) || '無治療資訊'}
                                    </div>
                                </div>
                            </div>

                            ${record.medical_details ? this.renderMedicalDetails(record.medical_details) : ''}
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            document.body.style.overflow = 'hidden';

            // 添加 ESC 鍵關閉功能
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    this.closeMedicalModal(modal);
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);

        } catch (error) {
            console.error('獲取醫療記錄失敗:', error);
            alert('無法獲取醫療記錄詳情，請稍後再試');
        }
    }

    // 渲染醫療詳細資訊
    renderMedicalDetails(details) {
        let html = '';

        // 生命徵象
        if (details.weight || details.temperature || details.heart_rate || details.respiratory_rate) {
            html += `
                <div class="detail-section">
                    <h4>生命徵象</h4>
                    <div class="vital-signs-grid">
                        ${details.weight ? `<div class="vital-item">體重: ${details.weight}kg</div>` : ''}
                        ${details.temperature ? `<div class="vital-item">體溫: ${details.temperature}°C</div>` : ''}
                        ${details.heart_rate ? `<div class="vital-item">心率: ${details.heart_rate}bpm</div>` : ''}
                        ${details.respiratory_rate ? `<div class="vital-item">呼吸: ${details.respiratory_rate}/min</div>` : ''}
                    </div>
                </div>
            `;
        }

        // 症狀記錄
        if (details.symptoms && details.symptoms.length > 0) {
            html += `
                <div class="detail-section">
                    <h4>症狀記錄</h4>
                    <div class="symptoms-list">
                        ${details.symptoms.map(symptom => `
                            <div class="symptom-item">
                                <span class="symptom-name">${symptom.name}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // 處方用藥
        if (details.prescriptions && details.prescriptions.length > 0) {
            html += `
                <div class="detail-section">
                    <h4>處方用藥</h4>
                    <div class="prescriptions-list">
                        ${details.prescriptions.map(prescription => `
                            <div class="prescription-item">
                                <div class="prescription-header">
                                    <strong>${prescription.medication || '未指定藥物'}</strong>
                                    <span class="prescription-dosage">${prescription.dosage || ''}</span>
                                </div>
                                <div class="prescription-details">
                                    <span>給藥方式: ${this.translateRoute(prescription.route) || '口服'}</span>
                                    <span>次數: ${this.translateFrequency(prescription.frequency) || '依醫師指示'}</span>
                                </div>
                                ${prescription.instructions ? `<div class="prescription-instructions">${prescription.instructions}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        return html;
    }

    // 關閉醫療記錄模態框
    closeMedicalModal(modal) {
        if (modal) {
            modal.remove();
            document.body.style.overflow = '';
        }
    }

    // 清理文字格式
    cleanText(text) {
        if (!text) return '';
        return text.toString()
            .trim()                           // 移除前後空格
            .replace(/\s+/g, ' ')            // 將多個空格合併為單個空格
            .replace(/[\u00A0\u2000-\u200B\u2028\u2029\u3000]/g, ' ') // 移除特殊空格字元
            .trim();                         // 再次移除前後空格
    }

    // 格式化治療計畫
    formatTreatmentPlan(text) {
        if (!text || text.trim() === '') return '';

        // 清理文字並按行分割
        const cleanedText = this.cleanText(text);
        if (!cleanedText) return '';

        // 將治療計畫按行分割並格式化
        const formattedContent = cleanedText.split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map((line, index) => {
                // 如果行包含數字開頭（如 1. 2. 等），保持原樣
                if (/^\d+\./.test(line)) {
                    return `<div class="treatment-step">${line}</div>`;
                }
                // 如果行包含 "•" 或 "-" 開頭，轉換為列表項
                else if (/^[•\-]/.test(line)) {
                    return `<div class="treatment-item">${line}</div>`;
                }
                // 其他情況作為普通段落
                else {
                    return `<div class="treatment-paragraph">${line}</div>`;
                }
            })
            .join('');

        return formattedContent || '';
    }

    // 翻譯頻率
    translateFrequency(value) {
        if (!value) return '';
        const frequencyMap = {
            'bid': '一日兩次',
            'tid': '一日三次',
            'qd': '一日一次',
            'qid': '一日四次',
            'once': '單次使用',
            'twice': '兩次',
            'three_times': '三次',
            'four_times': '四次',
            'as_needed': '需要時使用',
            'prn': '需要時使用',
            'daily': '每日',
            'weekly': '每週',
            'monthly': '每月'
        };
        return frequencyMap[value.toLowerCase()] || value;
    }

    // 翻譯給藥方式
    translateRoute(value) {
        if (!value) return '';
        const routeMap = {
            'oral': '口服',
            'topical': '外用',
            'iv': '靜脈注射',
            'im': '肌肉注射',
            'sc': '皮下注射',
            'subcutaneous': '皮下注射',
            'injection': '注射',
            'eye': '點眼',
            'ear': '點耳',
            'nasal': '鼻噴',
            'rectal': '直腸給藥',
            'inhalation': '吸入'
        };
        return routeMap[value.toLowerCase()] || value;
    }

    // 更新空狀態
    updateEmptyState(isEmpty, status) {
        const existingEmpty = document.querySelector('.empty-state-modern');
        const grid = document.querySelector('.appointments-grid');

        if (isEmpty && !existingEmpty && grid) {
            let message = '暫無預約記錄';
            
            if (status === 'active') {
                message = '您目前沒有進行中的預約';
            } else if (status === 'completed') {
                message = '您沒有已完成的預約記錄';
            } else if (status === 'cancelled') {
                message = '您沒有已取消的預約記錄';
            }

            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state-modern';
            emptyState.innerHTML = `
                <div class="empty-icon-modern">
                    <i class="fas fa-calendar-times"></i>
                </div>
                <h3 class="empty-title-modern">${message}</h3>
                <p class="empty-description-modern">
                    立即開始您的寵物健康管理之旅
                </p>
                <a href="/pets/" class="cta-button">
                    <i class="fas fa-plus"></i>
                    <span>立即預約</span>
                </a>
            `;
            grid.appendChild(emptyState);
        } else if (!isEmpty && existingEmpty) {
            existingEmpty.remove();
        }
    }
}

// 全域函數（向後相容）
function filterAppointments(status) {
    if (window.myAppointments) {
        window.myAppointments.filterAppointments(status);
    }
}

function toggleDetails(button) {
    if (window.myAppointments) {
        window.myAppointments.toggleDetails(button);
    }
}

// 初始化
function initMyAppointments() {
    if (document.querySelector('.appointments-wrapper')) {
        window.myAppointments = new MyAppointments();
        // console.log('✅ 預約管理系統已初始化');
    }
}

// 多種初始化方式
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMyAppointments);
} else {
    initMyAppointments();
}

// 確保全域函數可用
window.filterAppointments = filterAppointments;
window.toggleDetails = toggleDetails;