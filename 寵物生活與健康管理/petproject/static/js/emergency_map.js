// emergency_map.js - 24小時急診地圖應用程式

/**
 * 24小時急診地圖應用程式
 * 專門顯示緊急醫療服務的地圖功能
 */
class EmergencyMapApp {
    constructor() {
        // 地圖相關變數
        this.map = null;
        this.markers = null;
        this.userLocationMarker = null;
        this.emergencyMarkers = [];
        
        // 資料變數
        this.allHospitals = [];
        this.filteredHospitals = [];
        this.userLocation = null;
        
        // 篩選狀態
        this.currentFilters = {
            search: null,
            emergency24hrs: true, // 預設只顯示24小時急診
            surgery: false,
            icu: false,
            nearby: false
        };
        
        // UI 狀態
        this.isSidebarOpen = window.innerWidth > 1024;
        this.isLoading = false;
        this.selectedHospital = null;
        this.selectedHospitalMarker = null;
        
        // 配置
        this.config = {
            defaultCenter: [25.0330, 121.5654], // 台北市
            defaultZoom: 12,
            maxZoom: 19,
            nearbyRadius: 5000, // 5公里（急診搜尋範圍較大）
            clusterRadius: 40,
            animationDuration: 300,
            emergencyUpdateInterval: 30000 // 30秒更新一次
        };
        
        // 緊急狀態監控
        this.emergencyUpdateTimer = null;
        
        this.init();
    }
    
    /**
     * 初始化應用程式
     */
    async init() {
        console.log('🚨 初始化24小時急診地圖應用程式...');
        
        try {
            this.showLoading(true);
            
            // 初始化地圖
            await this.initMap();
            
            // 設置事件監聽器
            this.setupEventListeners();
            
            // 嘗試獲取用戶位置（急診時特別重要）
            await this.getUserLocation();
            
            // 載入急診醫院資料
            await this.loadEmergencyHospitals();
            
            // 開始定期更新
            this.startEmergencyUpdates();
            
            console.log('✅ 急診地圖應用程式初始化完成');
        } catch (error) {
            console.error('❌ 急診地圖初始化失敗:', error);
            this.showError('急診地圖初始化失敗，請重新整理頁面');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 初始化地圖
     */
    async initMap() {
        console.log('🗺️ 初始化急診地圖...');
        
        // 創建地圖
        this.map = L.map('emergency-map', {
            center: this.config.defaultCenter,
            zoom: this.config.defaultZoom,
            zoomControl: false,
            attributionControl: true
        });
        
        // 添加地圖圖層（使用適合急診的圖層）
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: this.config.maxZoom
        }).addTo(this.map);
        
        // 創建標記群組
        this.markers = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: this.config.clusterRadius,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: true,
            zoomToBoundsOnClick: true,
            iconCreateFunction: (cluster) => this.createEmergencyClusterIcon(cluster)
        });
        
        this.map.addLayer(this.markers);
        
        // 設置地圖事件
        this.setupMapEvents();
        
        console.log('✅ 急診地圖初始化完成');
    }
    
    /**
     * 設置地圖事件
     */
    setupMapEvents() {
        // 地圖點擊事件
        this.map.on('click', () => {
            this.hideHospitalInfo();
        });
        
        // 視圖變更事件
        this.map.on('moveend zoomend', () => {
            this.updateNearbyFilter();
            this.updateHospitalDistances();
        });
    }
    
    /**
     * 設置事件監聽器
     */
    setupEventListeners() {
        // 側邊欄切換
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }
        
        // 搜尋功能
        const searchInput = document.getElementById('emergencySearchInput');
        const searchBtn = document.getElementById('emergencySearchBtn');
        
        if (searchInput && searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.performSearch();
            });
            
            // 即時搜尋
            let searchTimeout;
            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    if (searchInput.value.trim().length >= 2) {
                        this.performSearch();
                    } else if (searchInput.value.trim().length === 0) {
                        this.currentFilters.search = null;
                        this.updateFilters();
                    }
                }, 300); // 急診搜尋回應要快
            });
        }
        
        // 篩選功能
        document.querySelectorAll('.emergency-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const filter = checkbox.dataset.filter;
                this.toggleFilter(filter, checkbox.checked);
            });
        });
        
        // 地圖控制按鈕
        this.setupMapControls();
        
        // 響應式處理
        window.addEventListener('resize', () => this.handleResize());
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // 醫院列表點擊事件
        document.addEventListener('click', (e) => {
            if (e.target.closest('.hospital-item')) {
                const hospitalItem = e.target.closest('.hospital-item');
                const hospitalId = hospitalItem.dataset.hospitalId;
                this.selectHospitalFromList(hospitalId);
            }
        });
    }
    
    /**
     * 設置地圖控制項
     */
    setupMapControls() {
        // 定位按鈕
        const locateBtn = document.getElementById('locateBtn');
        if (locateBtn) {
            locateBtn.addEventListener('click', () => this.locateUser());
        }
        
        // 重新整理按鈕
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshEmergencyData());
        }
        
        // 緊急電話按鈕
        const callEmergencyBtn = document.getElementById('callEmergencyBtn');
        if (callEmergencyBtn) {
            callEmergencyBtn.addEventListener('click', () => this.showEmergencyCallModal());
        }
    }
    
    /**
     * 載入急診醫院資料
     */
    async loadEmergencyHospitals() {
        console.log('🏥 載入急診醫院資料...');
        
        try {
            this.showLoading(true, '搜尋24小時急診醫院...');
            
            // 構建查詢參數 - 只搜尋急診醫院
            const params = new URLSearchParams();
            params.append('type', 'hospital');
            params.append('emergency', 'true'); // 只要有急診服務的
            
            if (this.currentFilters.search) {
                params.append('search', this.currentFilters.search);
            }
            
            const url = `/api/locations/?${params.toString()}`;
            console.log('🔍 急診醫院 API 請求:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('🏥 載入了', data.features?.length || 0, '家急診醫院');
            
            if (data.features) {
                this.allHospitals = data.features.filter(hospital => 
                    hospital.properties.has_emergency || 
                    hospital.properties.service_types?.some(service => 
                        service.includes('急診') || service.includes('24')
                    )
                );
                
                this.applyEmergencyFilters();
                this.displayEmergencyMarkers();
                this.updateHospitalList();
                this.updateStatusDisplay();
            } else {
                throw new Error('API 回應格式錯誤');
            }
            
        } catch (error) {
            console.error('❌ 載入急診醫院失敗:', error);
            this.showError('無法載入急診醫院資料，請稍後再試');
            this.allHospitals = [];
            this.filteredHospitals = [];
            this.displayEmergencyMarkers();
            this.updateHospitalList();
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 應用急診篩選條件
     */
    applyEmergencyFilters() {
        this.filteredHospitals = this.allHospitals.filter(hospital => {
            const props = hospital.properties;
            
            // 24小時急診篩選
            if (this.currentFilters.emergency24hrs && !props.has_emergency) {
                return false;
            }
            
            // 外科手術篩選
            if (this.currentFilters.surgery) {
                const hasServices = props.service_types?.some(service => 
                    service.includes('外科') || service.includes('手術')
                );
                if (!hasServices) return false;
            }
            
            // 重症監護篩選
            if (this.currentFilters.icu) {
                const hasICU = props.service_types?.some(service => 
                    service.includes('重症') || service.includes('ICU') || service.includes('加護')
                );
                if (!hasICU) return false;
            }
            
            // 附近距離篩選
            if (this.currentFilters.nearby && this.userLocation) {
                const distance = this.calculateDistance(
                    this.userLocation.lat,
                    this.userLocation.lng,
                    hospital.geometry.coordinates[1],
                    hospital.geometry.coordinates[0]
                );
                
                if (distance > this.config.nearbyRadius) {
                    return false;
                }
            }
            
            return true;
        });
        
        // 按距離排序（如果有用戶位置）
        if (this.userLocation) {
            this.filteredHospitals.sort((a, b) => {
                const distanceA = this.calculateDistance(
                    this.userLocation.lat, this.userLocation.lng,
                    a.geometry.coordinates[1], a.geometry.coordinates[0]
                );
                const distanceB = this.calculateDistance(
                    this.userLocation.lat, this.userLocation.lng,
                    b.geometry.coordinates[1], b.geometry.coordinates[0]
                );
                return distanceA - distanceB;
            });
        }
        
        console.log(`🏥 篩選後顯示 ${this.filteredHospitals.length} 家急診醫院`);
    }
    
    /**
     * 顯示急診醫院標記
     */
    displayEmergencyMarkers() {
        console.log('🚨 更新急診醫院標記...');
        
        // 清除現有標記
        this.markers.clearLayers();
        this.emergencyMarkers = [];
        
        if (!this.filteredHospitals || this.filteredHospitals.length === 0) {
            console.log('⚠️ 沒有急診醫院資料要顯示');
            return;
        }
        
        let successCount = 0;
        let errorCount = 0;
        
        this.filteredHospitals.forEach((hospital, index) => {
            try {
                if (!hospital.geometry?.coordinates) {
                    errorCount++;
                    return;
                }
                
                const [lng, lat] = hospital.geometry.coordinates;
                const props = hospital.properties;
                
                // 創建急診標記
                const marker = this.createEmergencyMarker(lat, lng, props);
                
                // 創建彈出視窗
                const popupContent = this.createEmergencyPopupContent(props);
                marker.bindPopup(popupContent, {
                    maxWidth: 320,
                    className: 'emergency-popup'
                });
                
                // 標記點擊事件
                marker.on('click', () => {
                    this.selectHospital(hospital, marker);
                });
                
                // 保存標記引用
                marker.hospitalId = props.id || index;
                this.emergencyMarkers.push(marker);
                this.markers.addLayer(marker);
                successCount++;
                
            } catch (error) {
                console.error(`❌ 處理急診醫院 ${index} 時發生錯誤:`, error);
                errorCount++;
            }
        });
        
        console.log(`🏥 急診標記處理完成: 成功 ${successCount} 個, 失敗 ${errorCount} 個`);
        
        // 調整地圖視角
        this.fitMapToEmergencyHospitals();
    }
    
    /**
     * 創建急診醫院標記
     */
    createEmergencyMarker(lat, lng, props) {
        // 判斷急診醫院等級
        const isLevel1Trauma = props.service_types?.some(service => 
            service.includes('一級') || service.includes('重度')
        );
        const hasICU = props.service_types?.some(service => 
            service.includes('重症') || service.includes('ICU')
        );
        const hasSurgery = props.service_types?.some(service => 
            service.includes('外科') || service.includes('手術')
        );
        
        // 決定圖標和顏色
        let icon = '🏥';
        let color = '#dc3545';
        let size = 45;
        
        if (isLevel1Trauma) {
            icon = '🚑';
            color = '#8b0000';
            size = 50;
        } else if (hasICU && hasSurgery) {
            icon = '🏥';
            color = '#dc3545';
            size = 47;
        }
        
        // 24小時服務標誌
        const is24Hours = props.has_emergency;
        const borderColor = is24Hours ? '#fff' : '#ffc107';
        const borderWidth = is24Hours ? '4px' : '3px';
        
        const customIcon = L.divIcon({
            html: `<div class="emergency-marker-icon" style="
                background: ${color};
                color: white;
                border-radius: 50%;
                width: ${size}px;
                height: ${size}px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: ${borderWidth} solid ${borderColor};
                box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
                font-size: ${size > 45 ? '20px' : '18px'};
                font-weight: bold;
                position: relative;
                cursor: pointer;
                transition: all 0.3s ease;
                z-index: 100;
            " data-emergency="${is24Hours}" data-level="${isLevel1Trauma ? 'trauma' : 'regular'}">${icon}</div>`,
            className: 'emergency-marker',
            iconSize: [size, size],
            iconAnchor: [size/2, size/2],
            popupAnchor: [0, -size/2]
        });
        
        const marker = L.marker([lat, lng], { icon: customIcon });
        
        // 添加動畫效果
        marker.on('mouseover', function() {
            const iconElement = this.getElement().querySelector('.emergency-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1.1)';
                iconElement.style.zIndex = '1000';
                iconElement.style.boxShadow = '0 6px 20px rgba(220, 53, 69, 0.6)';
            }
        });
        
        marker.on('mouseout', function() {
            const iconElement = this.getElement().querySelector('.emergency-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1)';
                iconElement.style.zIndex = '100';
                iconElement.style.boxShadow = '0 4px 15px rgba(220, 53, 69, 0.4)';
            }
        });
        
        return marker;
    }
    
    /**
     * 創建急診叢集圖標
     */
    createEmergencyClusterIcon(cluster) {
        const count = cluster.getChildCount();
        let size = 50;
        let className = 'emergency-cluster-small';
        
        if (count >= 20) {
            size = 70;
            className = 'emergency-cluster-large';
        } else if (count >= 5) {
            size = 60;
            className = 'emergency-cluster-medium';
        }
        
        return L.divIcon({
            html: `<div style="
                background: linear-gradient(135deg, #dc3545 0%, #8b0000 100%);
                color: white;
                border-radius: 50%;
                width: ${size}px;
                height: ${size}px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: ${size > 60 ? '18px' : '16px'};
                border: 4px solid white;
                box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
                cursor: pointer;
                position: relative;
            ">${count}<div style="
                position: absolute;
                top: -3px;
                right: -3px;
                width: 12px;
                height: 12px;
                background: #ffc107;
                border-radius: 50%;
                border: 2px solid white;
            "></div></div>`,
            className: `emergency-cluster ${className}`,
            iconSize: [size, size]
        });
    }
    
    /**
     * 創建急診彈出視窗內容
     */
    createEmergencyPopupContent(props) {
        let html = `<div class="emergency-popup-content">
            <h3 style="color: #dc3545; margin-bottom: 10px;">${props.name || '急診醫院'}</h3>`;
        
        // 24小時急診標誌
        if (props.has_emergency) {
            html += `<div style="background: #dc3545; color: white; padding: 5px 10px; 
                     border-radius: 15px; font-size: 12px; font-weight: bold; 
                     margin-bottom: 10px; display: inline-block; animation: pulse 2s infinite;">
                🚨 24小時急診服務
            </div>`;
        }
        
        // 地址
        if (props.address) {
            html += `<div style="margin-bottom: 8px;">
                <i class="bi bi-geo-alt" style="color: #dc3545; margin-right: 5px;"></i>
                ${props.address}
            </div>`;
        }
        
        // 電話（緊急聯絡）
        if (props.phone) {
            html += `<div style="margin-bottom: 8px;">
                <i class="bi bi-telephone-fill" style="color: #dc3545; margin-right: 5px;"></i>
                <a href="tel:${props.phone}" style="color: #dc3545; font-weight: bold; text-decoration: none;">
                    ${props.phone}
                </a>
            </div>`;
        }
        
        // 評分
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            html += `<div style="margin-bottom: 10px;">
                <span>${stars}</span>
                <span style="margin-left: 5px; color: #666;">${props.rating} (${props.rating_count || 0}評價)</span>
            </div>`;
        }
        
        // 距離資訊
        if (this.userLocation) {
            const distance = this.calculateDistance(
                this.userLocation.lat,
                this.userLocation.lng,
                parseFloat(props.lat) || 0,
                parseFloat(props.lon) || 0
            );
            
            const distanceText = distance < 1000 
                ? `${Math.round(distance)} 公尺`
                : `${(distance / 1000).toFixed(1)} 公里`;
                
            html += `<div style="margin-bottom: 10px; color: #dc3545; font-weight: bold;">
                📍 距離約 ${distanceText}
            </div>`;
        }
        
        // 緊急操作按鈕
        html += `<div style="display: flex; gap: 8px; margin-top: 12px;">`;
        
        if (props.phone) {
            html += `<a href="tel:${props.phone}" style="
                background: #dc3545; color: white; padding: 8px 12px; 
                border-radius: 6px; text-decoration: none; font-size: 12px; 
                font-weight: bold; display: flex; align-items: center; gap: 4px;
                flex: 1; justify-content: center;">
                <i class="bi bi-telephone-fill"></i> 緊急聯絡
            </a>`;
        }
        
        if (props.address) {
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(props.address)}`;
            html += `<a href="${mapUrl}" target="_blank" style="
                background: #28a745; color: white; padding: 8px 12px; 
                border-radius: 6px; text-decoration: none; font-size: 12px; 
                font-weight: bold; display: flex; align-items: center; gap: 4px;
                flex: 1; justify-content: center;">
                <i class="bi bi-navigation"></i> 導航
            </a>`;
        }
        
        html += `</div></div>`;
        return html;
    }
    
    /**
     * 更新醫院列表
     */
    updateHospitalList() {
        const hospitalList = document.getElementById('hospitalList');
        const hospitalCount = document.getElementById('hospitalCount');
        
        if (!hospitalList || !hospitalCount) return;
        
        // 更新數量
        hospitalCount.textContent = `(${this.filteredHospitals.length})`;
        
        // 清空列表
        hospitalList.innerHTML = '';
        
        if (this.filteredHospitals.length === 0) {
            hospitalList.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #dc3545;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <h4>找不到符合條件的急診醫院</h4>
                    <p>請嘗試調整篩選條件或擴大搜尋範圍</p>
                </div>
            `;
            return;
        }
        
        // 生成醫院列表項目
        this.filteredHospitals.forEach((hospital, index) => {
            const props = hospital.properties;
            const hospitalItem = this.createHospitalListItem(props, hospital, index);
            hospitalList.appendChild(hospitalItem);
        });
    }
    
    /**
     * 創建醫院列表項目
     */
    createHospitalListItem(props, hospital, index) {
        const item = document.createElement('div');
        item.className = 'hospital-item';
        item.dataset.hospitalId = props.id || index;
        
        // 計算距離
        let distanceHtml = '';
        if (this.userLocation) {
            const distance = this.calculateDistance(
                this.userLocation.lat,
                this.userLocation.lng,
                hospital.geometry.coordinates[1],
                hospital.geometry.coordinates[0]
            );
            
            const distanceText = distance < 1000 
                ? `${Math.round(distance)} 公尺`
                : `${(distance / 1000).toFixed(1)} 公里`;
                
            distanceHtml = `<div class="hospital-distance">📍 ${distanceText}</div>`;
        }
        
        // 生成服務標籤
        let badgesHtml = '';
        if (props.has_emergency) {
            badgesHtml += '<span class="hospital-badge emergency">🚨 24H急診</span>';
        }
        if (props.service_types?.some(s => s.includes('外科'))) {
            badgesHtml += '<span class="hospital-badge surgery">🔬 外科</span>';
        }
        if (props.service_types?.some(s => s.includes('重症') || s.includes('ICU'))) {
            badgesHtml += '<span class="hospital-badge icu">🏥 ICU</span>';
        }
        
        item.innerHTML = `
            <div class="hospital-name">${props.name || '急診醫院'}</div>
            <div class="hospital-info">
                ${props.address || '地址資訊不詳'}
                ${props.phone ? `<br>📞 ${props.phone}` : ''}
            </div>
            ${distanceHtml}
            <div class="hospital-badges">${badgesHtml}</div>
        `;
        
        return item;
    }
    
    /**
     * 切換篩選條件
     */
    toggleFilter(filter, isChecked) {
        this.currentFilters[filter] = isChecked;
        
        // 特殊處理
        if (filter === 'nearby' && isChecked && !this.userLocation) {
            this.locateUser();
            return;
        }
        
        this.updateFilters();
    }
    
    /**
     * 執行搜尋
     */
    performSearch() {
        const searchInput = document.getElementById('emergencySearchInput');
        const searchText = searchInput.value.trim();
        
        this.currentFilters.search = searchText || null;
        this.updateFilters();
    }
    
    /**
     * 更新篩選
     */
    async updateFilters() {
        console.log('🔄 更新急診篩選條件:', this.currentFilters);
        
        try {
            // 重新載入資料（如果需要）
            if (this.currentFilters.search) {
                await this.loadEmergencyHospitals();
            } else {
                this.applyEmergencyFilters();
                this.displayEmergencyMarkers();
                this.updateHospitalList();
                this.updateStatusDisplay();
            }
        } catch (error) {
            console.error('❌ 更新急診篩選失敗:', error);
            this.showError('篩選更新失敗');
        }
    }
    
    /**
     * 從列表選擇醫院
     */
    selectHospitalFromList(hospitalId) {
        // 在列表中標記選中
        document.querySelectorAll('.hospital-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = document.querySelector(`[data-hospital-id="${hospitalId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        // 找到對應的醫院和標記
        const hospital = this.filteredHospitals.find((h, index) => 
            (h.properties.id || index).toString() === hospitalId.toString()
        );
        
        const marker = this.emergencyMarkers.find(m => 
            m.hospitalId.toString() === hospitalId.toString()
        );
        
        if (hospital && marker) {
            this.selectHospital(hospital, marker);
            
            // 移動地圖到選中的醫院
            this.map.setView(marker.getLatLng(), Math.max(this.map.getZoom(), 15));
            
            // 在手機版關閉側邊欄
            if (window.innerWidth <= 768 && this.isSidebarOpen) {
                this.toggleSidebar();
            }
        }
    }
    
    /**
     * 選擇醫院
     */
    selectHospital(hospital, marker) {
        this.selectedHospital = hospital;
        this.selectedHospitalMarker = marker;
        
        this.showHospitalInfo(hospital);
        this.highlightSelectedMarker(marker);
        
        // 記錄選擇（用於統計）
        console.log('用戶選擇急診醫院:', hospital.properties.name);
        
        // 可選：Google Analytics 追蹤
        if (typeof gtag !== 'undefined') {
            gtag('event', 'emergency_hospital_select', {
                'event_category': 'emergency_map',
                'event_label': hospital.properties.name,
                'hospital_type': hospital.properties.has_emergency ? '24hrs' : 'regular'
            });
        }
    }
    
    /**
     * 顯示醫院詳細資訊
     */
    showHospitalInfo(hospital) {
        const infoCard = document.getElementById('hospitalInfoCard');
        const hospitalName = document.getElementById('hospitalName');
        const hospitalBadges = document.getElementById('hospitalBadges');
        const hospitalContent = document.getElementById('hospitalInfoContent');
        
        if (!infoCard || !hospitalName || !hospitalBadges || !hospitalContent) return;
        
        const props = hospital.properties;
        
        // 設置標題
        hospitalName.textContent = props.name || '急診醫院';
        
        // 設置標籤
        let badgesHtml = '';
        if (props.has_emergency) {
            badgesHtml += '<span class="emergency-badge">🚨 24小時急診</span>';
        }
        if (props.service_types?.some(s => s.includes('外科'))) {
            badgesHtml += '<span class="service-badge">🔬 外科手術</span>';
        }
        if (props.service_types?.some(s => s.includes('重症') || s.includes('ICU'))) {
            badgesHtml += '<span class="service-badge">🏥 重症監護</span>';
        }
        hospitalBadges.innerHTML = badgesHtml;
        
        // 設置詳細內容
        hospitalContent.innerHTML = this.createDetailedHospitalInfo(props);
        
        // 顯示資訊卡
        infoCard.style.display = 'block';
        
        // 動畫效果
        infoCard.style.opacity = '0';
        infoCard.style.transform = 'translateY(-20px)';
        
        requestAnimationFrame(() => {
            infoCard.style.transition = 'all 0.3s ease';
            infoCard.style.opacity = '1';
            infoCard.style.transform = 'translateY(0)';
        });
        
        // 設置關閉按鈕
        const closeBtn = document.getElementById('closeInfoBtn');
        if (closeBtn) {
            closeBtn.onclick = () => this.hideHospitalInfo();
        }
    }
    
    /**
     * 創建詳細醫院資訊
     */
    createDetailedHospitalInfo(props) {
        let html = '';
        
        // 緊急聯絡區塊
        if (props.phone) {
            html += `
                <div class="info-section" style="background: linear-gradient(135deg, #dc3545 0%, #8b0000 100%); 
                     color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <h4 style="color: white; margin-bottom: 0.5rem;">
                        <i class="bi bi-telephone-fill"></i> 緊急聯絡
                    </h4>
                    <a href="tel:${props.phone}" style="color: white; font-size: 1.2rem; 
                       font-weight: bold; text-decoration: none;">
                        📞 ${props.phone}
                    </a>
                    <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">
                        點擊立即撥打緊急電話
                    </p>
                </div>
            `;
        }
        
        // 地址資訊
        if (props.address) {
            html += `
                <div class="info-section">
                    <h4><i class="bi bi-geo-alt"></i> 醫院地址</h4>
                    <p>${props.address}</p>
                    ${props.city && props.district ? `<p class="text-muted">${props.city} ${props.district}</p>` : ''}
                </div>
            `;
        }
        
        // 距離和導航
        if (this.userLocation) {
            const distance = this.calculateDistance(
                this.userLocation.lat,
                this.userLocation.lng,
                parseFloat(props.lat) || 0,
                parseFloat(props.lon) || 0
            );
            
            const distanceText = distance < 1000 
                ? `${Math.round(distance)} 公尺`
                : `${(distance / 1000).toFixed(1)} 公里`;
                
            // 估算車程時間（假設平均時速30公里）
            const timeMinutes = Math.round((distance / 1000) / 30 * 60);
            const timeText = timeMinutes < 60 ? `${timeMinutes} 分鐘` : `${Math.round(timeMinutes/60)} 小時`;
            
            html += `
                <div class="info-section" style="background: #fff3cd; padding: 1rem; border-radius: 8px; border: 1px solid #ffeaa7;">
                    <h4 style="color: #856404;"><i class="bi bi-signpost"></i> 距離資訊</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span><strong>直線距離：</strong>${distanceText}</span>
                        <span><strong>預估車程：</strong>${timeText}</span>
                    </div>
                </div>
            `;
        }
        
        // 評分資訊
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            const emptyStars = '☆'.repeat(5 - Math.round(props.rating));
            html += `
                <div class="info-section">
                    <h4><i class="bi bi-star"></i> 評分與評價</h4>
                    <div class="rating-display">
                        <span class="stars">${stars}${emptyStars}</span>
                        <span class="rating-text">${props.rating} / 5.0</span>
                    </div>
                    <p class="review-count">${props.rating_count || 0} 則評價</p>
                </div>
            `;
        }
        
        // 急診服務項目
        if (props.service_types && props.service_types.length > 0) {
            html += `
                <div class="info-section">
                    <h4><i class="bi bi-heart-pulse"></i> 急診服務項目</h4>
                    <div class="service-tags">
            `;
            props.service_types.forEach(service => {
                let serviceClass = 'service-tag';
                if (service.includes('急診') || service.includes('24')) {
                    serviceClass += ' emergency-service';
                }
                html += `<span class="${serviceClass}">${service}</span>`;
            });
            html += `</div></div>`;
        }
        
        // 支援寵物類型
        if (props.supported_pet_types && props.supported_pet_types.length > 0) {
            html += `
                <div class="info-section">
                    <h4><i class="bi bi-heart"></i> 支援寵物類型</h4>
                    <div class="pet-tags">
            `;
            props.supported_pet_types.forEach(petType => {
                let icon = '🐾';
                if (petType.includes('狗') || petType.includes('犬')) icon = '🐕';
                else if (petType.includes('貓')) icon = '🐈';
                else if (petType.includes('鳥')) icon = '🦜';
                else if (petType.includes('鼠')) icon = '🐹';
                else if (petType.includes('爬蟲')) icon = '🦎';
                
                html += `<span class="pet-tag">${icon} ${petType}</span>`;
            });
            html += `</div></div>`;
        }
        
        // 緊急操作按鈕
        html += `
            <div class="info-actions">
                <div class="action-buttons">
        `;
        
        if (props.phone) {
            html += `
                <a href="tel:${props.phone}" class="info-btn emergency-call">
                    <i class="bi bi-telephone-fill"></i> 緊急撥號
                </a>
            `;
        }
        
        if (props.address) {
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(props.address)}`;
            html += `
                <a href="${mapUrl}" target="_blank" class="info-btn navigation">
                    <i class="bi bi-navigation"></i> 立即導航
                </a>
            `;
        }
        
        // 分享按鈕
        html += `
            <button onclick="emergencyMapApp.shareHospital('${props.name}', '${props.address || ''}', '${props.phone || ''}')" class="info-btn share">
                <i class="bi bi-share"></i> 分享醫院
            </button>
        `;
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    /**
     * 分享醫院資訊
     */
    shareHospital(name, address, phone) {
        const shareText = `🚨 緊急醫院資訊 🚨\n\n` +
                         `醫院：${name}\n` +
                         `地址：${address}\n` +
                         (phone ? `電話：${phone}\n` : '') +
                         `\n24小時急診地圖：${window.location.href}`;
        
        if (navigator.share) {
            navigator.share({
                title: `${name} - 急診醫院`,
                text: shareText,
                url: window.location.href
            }).catch(err => {
                console.log('分享失敗:', err);
                this.fallbackShare(shareText);
            });
        } else {
            this.fallbackShare(shareText);
        }
    }
    
    /**
     * 備用分享方式
     */
    fallbackShare(shareText) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(shareText).then(() => {
                this.showNotification('醫院資訊已複製到剪貼簿', 'success');
            }).catch(() => {
                this.showShareModal(shareText);
            });
        } else {
            this.showShareModal(shareText);
        }
    }
    
    /**
     * 獲取用戶位置
     */
    async getUserLocation() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                console.log('瀏覽器不支援定位功能');
                resolve(null);
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    console.log('✅ 獲取用戶位置成功:', this.userLocation);
                    resolve(this.userLocation);
                },
                (error) => {
                    console.log('無法獲取用戶位置:', error.message);
                    // 急診情況下提示用戶開啟定位
                    this.showNotification('建議開啟定位功能以找到最近的急診醫院', 'warning', 5000);
                    resolve(null);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 8000, // 急診時縮短超時時間
                    maximumAge: 60000 // 1分鐘快取
                }
            );
        });
    }
    
    /**
     * 定位用戶
     */
    async locateUser() {
        try {
            this.showLoading(true, '正在定位您的位置...');
            
            const location = await this.getUserLocation();
            
            if (location) {
                // 移動地圖到用戶位置
                this.map.setView([location.lat, location.lng], 14);
                
                // 添加或更新用戶位置標記
                if (this.userLocationMarker) {
                    this.map.removeLayer(this.userLocationMarker);
                }
                
                this.userLocationMarker = L.marker([location.lat, location.lng], {
                    icon: L.divIcon({
                        html: `<div style="
                            background: #007cff;
                            color: white;
                            border-radius: 50%;
                            width: 25px;
                            height: 25px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border: 4px solid white;
                            box-shadow: 0 3px 10px rgba(0,123,255,0.4);
                            font-size: 14px;
                            animation: userLocationPulse 2s infinite;
                        ">📍</div>`,
                        className: 'user-location-marker',
                        iconSize: [25, 25],
                        iconAnchor: [12.5, 12.5]
                    })
                }).addTo(this.map);
                
                this.userLocationMarker.bindPopup('<b>您的位置</b><br>點擊找尋最近的急診醫院').openPopup();
                
                // 重新排序醫院列表（按距離）
                this.applyEmergencyFilters();
                this.updateHospitalList();
                
                this.showNotification('定位成功！已按距離排序急診醫院', 'success');
            } else {
                this.showNotification('無法取得位置，請手動搜尋急診醫院', 'warning');
            }
        } catch (error) {
            console.error('定位失敗:', error);
            this.showNotification('定位失敗，請手動搜尋', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 顯示緊急電話模態框
     */
    showEmergencyCallModal() {
        const modal = new bootstrap.Modal(document.getElementById('emergencyCallModal'));
        modal.show();
        
        // 記錄緊急電話使用
        if (typeof gtag !== 'undefined') {
            gtag('event', 'emergency_call_modal_open', {
                'event_category': 'emergency_interaction'
            });
        }
    }
    
    /**
     * 刷新急診資料
     */
    async refreshEmergencyData() {
        this.showNotification('正在更新急診醫院資料...', 'info');
        await this.loadEmergencyHospitals();
        this.showNotification('急診資料已更新', 'success');
    }
    
    /**
     * 開始急診資料定期更新
     */
    startEmergencyUpdates() {
        // 每30秒更新一次急診資料（在實際應用中可能需要調整）
        this.emergencyUpdateTimer = setInterval(() => {
            console.log('🔄 定期更新急診資料...');
            this.loadEmergencyHospitals();
        }, this.config.emergencyUpdateInterval);
    }
    
    /**
     * 停止急診資料更新
     */
    stopEmergencyUpdates() {
        if (this.emergencyUpdateTimer) {
            clearInterval(this.emergencyUpdateTimer);
            this.emergencyUpdateTimer = null;
        }
    }
    
    /**
     * 調整地圖視角到急診醫院
     */
    fitMapToEmergencyHospitals() {
        if (this.filteredHospitals.length === 0) return;
        
        try {
            // 如果有用戶位置，優先顯示用戶位置附近的醫院
            if (this.userLocation && this.filteredHospitals.length > 0) {
                // 找最近的3家醫院
                const nearbyHospitals = this.filteredHospitals.slice(0, 3);
                const bounds = L.latLngBounds();
                
                // 添加用戶位置
                bounds.extend([this.userLocation.lat, this.userLocation.lng]);
                
                // 添加最近的醫院
                nearbyHospitals.forEach(hospital => {
                    bounds.extend([
                        hospital.geometry.coordinates[1],
                        hospital.geometry.coordinates[0]
                    ]);
                });
                
                this.map.fitBounds(bounds, {
                    padding: [50, 50],
                    maxZoom: 14
                });
            } else {
                // 沒有用戶位置時，顯示所有醫院
                const markerBounds = this.markers.getBounds();
                if (markerBounds.isValid()) {
                    this.map.fitBounds(markerBounds, {
                        padding: [20, 20],
                        maxZoom: 13
                    });
                }
            }
        } catch (error) {
            console.error('調整地圖視角失敗:', error);
        }
    }
    
    /**
     * 更新狀態顯示
     */
    updateStatusDisplay() {
        const statusCount = document.getElementById('statusCount');
        if (statusCount) {
            const count = this.filteredHospitals.length;
            const text = count === 0 ? '找不到急診醫院' : `找到 ${count} 家急診醫院`;
            statusCount.textContent = text;
            
            // 根據數量改變顏色
            if (count === 0) {
                statusCount.style.color = '#dc3545';
            } else if (count < 3) {
                statusCount.style.color = '#ffc107';
            } else {
                statusCount.style.color = '#28a745';
            }
        }
    }
    
    /**
     * 更新醫院距離
     */
    updateHospitalDistances() {
        if (!this.userLocation) return;
        
        // 重新計算並更新距離顯示
        const hospitalItems = document.querySelectorAll('.hospital-item');
        hospitalItems.forEach((item, index) => {
            if (index < this.filteredHospitals.length) {
                const hospital = this.filteredHospitals[index];
                const distance = this.calculateDistance(
                    this.userLocation.lat,
                    this.userLocation.lng,
                    hospital.geometry.coordinates[1],
                    hospital.geometry.coordinates[0]
                );
                
                const distanceText = distance < 1000 
                    ? `${Math.round(distance)} 公尺`
                    : `${(distance / 1000).toFixed(1)} 公里`;
                
                const distanceEl = item.querySelector('.hospital-distance');
                if (distanceEl) {
                    distanceEl.textContent = `📍 ${distanceText}`;
                }
            }
        });
    }
    
    /**
     * 更新附近篩選
     */
    updateNearbyFilter() {
        if (this.currentFilters.nearby && this.userLocation) {
            this.applyEmergencyFilters();
            this.displayEmergencyMarkers();
            this.updateHospitalList();
            this.updateStatusDisplay();
        }
    }
    
    /**
     * 高亮選中的標記
     */
    highlightSelectedMarker(marker) {
        // 清除之前的高亮
        this.clearMarkerHighlight();
        
        const iconElement = marker.getElement()?.querySelector('.emergency-marker-icon');
        if (iconElement) {
            iconElement.style.transform = 'scale(1.2)';
            iconElement.style.zIndex = '10000';
            iconElement.style.boxShadow = '0 0 25px rgba(220, 53, 69, 0.8)';
            iconElement.classList.add('selected-emergency-marker');
            
            this.selectedHospitalMarker = marker;
        }
    }
    
    /**
     * 清除標記高亮
     */
    clearMarkerHighlight() {
        if (this.selectedHospitalMarker) {
            const iconElement = this.selectedHospitalMarker.getElement()?.querySelector('.emergency-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1)';
                iconElement.style.zIndex = '100';
                iconElement.style.boxShadow = '0 4px 15px rgba(220, 53, 69, 0.4)';
                iconElement.classList.remove('selected-emergency-marker');
            }
            this.selectedHospitalMarker = null;
        }
    }
    
    /**
     * 隱藏醫院資訊
     */
    hideHospitalInfo() {
        const infoCard = document.getElementById('hospitalInfoCard');
        if (infoCard) {
            infoCard.style.transition = 'all 0.3s ease';
            infoCard.style.opacity = '0';
            infoCard.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                infoCard.style.display = 'none';
            }, 300);
        }
        
        this.selectedHospital = null;
        this.clearMarkerHighlight();
        
        // 清除列表選中狀態
        document.querySelectorAll('.hospital-item').forEach(item => {
            item.classList.remove('selected');
        });
    }
    
    /**
     * 切換側邊欄
     */
    toggleSidebar() {
        const sidebar = document.getElementById('emergencySidebar');
        const toggle = document.getElementById('sidebarToggle');
        
        this.isSidebarOpen = !this.isSidebarOpen;
        
        if (this.isSidebarOpen) {
            sidebar.classList.add('show');
            toggle.innerHTML = '<i class="bi bi-x"></i>';
        } else {
            sidebar.classList.remove('show');
            toggle.innerHTML = '<i class="bi bi-list"></i>';
        }
        
        setTimeout(() => this.map.invalidateSize(), 300);
    }
    
    /**
     * 響應式處理
     */
    handleResize() {
        if (window.innerWidth > 1024) {
            const sidebar = document.getElementById('emergencySidebar');
            const toggle = document.getElementById('sidebarToggle');
            
            sidebar.classList.add('show');
            toggle.style.display = 'none';
            this.isSidebarOpen = true;
        } else {
            const toggle = document.getElementById('sidebarToggle');
            toggle.style.display = 'flex';
        }
        
        setTimeout(() => this.map.invalidateSize(), 100);
    }
    
    /**
     * 鍵盤快捷鍵處理
     */
    handleKeyboardShortcuts(e) {
        // Escape 關閉資訊卡或側邊欄
        if (e.key === 'Escape') {
            if (this.selectedHospital) {
                this.hideHospitalInfo();
            } else if (this.isSidebarOpen && window.innerWidth <= 1024) {
                this.toggleSidebar();
            }
        }
        
        // Ctrl+F 聚焦搜尋框
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('emergencySearchInput');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl+L 定位
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            this.locateUser();
        }
        
        // F1 顯示緊急電話
        if (e.key === 'F1') {
            e.preventDefault();
            this.showEmergencyCallModal();
        }
    }
    
    /**
     * 計算兩點間距離
     */
    calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371000; // 地球半徑（公尺）
        const dLat = this.toRadians(lat2 - lat1);
        const dLng = this.toRadians(lng2 - lng1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
    
    /**
     * 度數轉弧度
     */
    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
    
    /**
     * 顯示載入狀態
     */
    showLoading(show, message = '載入中...') {
        const loadingOverlay = document.getElementById('loadingOverlay');
        const loadingText = document.querySelector('.loading-text');
        
        if (loadingOverlay) {
            if (show) {
                loadingOverlay.style.display = 'flex';
                if (loadingText) {
                    loadingText.textContent = message;
                }
            } else {
                loadingOverlay.style.display = 'none';
            }
        }
        
        this.isLoading = show;
    }
    
    /**
     * 顯示通知訊息
     */
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `emergency-notification emergency-notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="bi bi-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        // 樣式
        notification.style.cssText = `
            position: fixed;
            top: 200px;
            right: 20px;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 320px;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
            font-family: "Noto Sans TC", sans-serif;
            font-weight: 500;
        `;
        
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.animation = 'slideOutRight 0.3s ease';
                    setTimeout(() => notification.remove(), 300);
                }
            }, duration);
        }
    }
    
    /**
     * 獲取通知圖標
     */
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }
    
    /**
     * 獲取通知顏色
     */
    getNotificationColor(type) {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        return colors[type] || colors.info;
    }
    
    /**
     * 顯示錯誤訊息
     */
    showError(message) {
        this.showNotification(message, 'error', 5000);
    }
    
    /**
     * 銷毀應用程式
     */
    destroy() {
        // 停止定期更新
        this.stopEmergencyUpdates();
        
        if (this.map) {
            this.map.remove();
        }
        
        // 移除事件監聽器
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('keydown', this.handleKeyboardShortcuts);
    }
}

// 全域變數和初始化
let emergencyMapApp;

// 頁面載入完成後初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚨 24小時急診地圖載入完成，初始化應用程式...');
    
    try {
        emergencyMapApp = new EmergencyMapApp();
        
        // 全域快捷鍵：F1 顯示緊急電話
        document.addEventListener('keydown', function(e) {
            if (e.key === 'F1') {
                e.preventDefault();
                emergencyMapApp.showEmergencyCallModal();
            }
        });
        
    } catch (error) {
        console.error('❌ 急診地圖初始化失敗:', error);
        
        const mapArea = document.querySelector('.emergency-map-area');
        if (mapArea) {
            mapArea.innerHTML = `
                <div style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    text-align: center;
                    padding: 2rem;
                    background: #fff5f5;
                ">
                    <i class="bi bi-exclamation-triangle" style="font-size: 4rem; color: #dc3545; margin-bottom: 1rem;"></i>
                    <h3 style="color: #dc3545; margin-bottom: 1rem;">急診地圖載入失敗</h3>
                    <p style="margin-bottom: 2rem; color: #666;">
                        很抱歉，急診地圖服務暫時無法使用。<br>
                        請直接撥打 <a href="tel:119" style="color: #dc3545; font-weight: bold;">119</a> 或聯絡就近醫院。
                    </p>
                    <div style="display: flex; gap: 1rem;">
                        <a href="tel:119" style="
                            background: #dc3545; color: white; padding: 12px 24px; 
                            border-radius: 8px; text-decoration: none; font-weight: bold;
                        ">
                            <i class="bi bi-telephone-fill me-1"></i>撥打 119
                        </a>
                        <button onclick="location.reload()" style="
                            background: #6c757d; color: white; padding: 12px 24px; 
                            border: none; border-radius: 8px; font-weight: bold; cursor: pointer;
                        ">
                            <i class="bi bi-arrow-clockwise me-1"></i>重新載入
                        </button>
                    </div>
                </div>
            `;
        }
    }
});

// 頁面卸載時清理資源
window.addEventListener('beforeunload', function() {
    if (emergencyMapApp) {
        emergencyMapApp.destroy();
    }
});

// 錯誤處理
window.addEventListener('error', function(e) {
    console.error('JavaScript 錯誤:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('未處理的 Promise 拒絕:', e.reason);
});

// 導出給其他腳本使用
window.EmergencyMapApp = EmergencyMapApp;
        