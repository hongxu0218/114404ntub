// map_redesign.js - 重新設計的寵物地圖功能

/**
 * 寵物地圖應用程式
 * 提供地點搜尋、篩選和顯示功能
 */
class PetMapApp {
    constructor() {
        // 地圖相關變數
        this.map = null;
        this.markers = null;
        this.userLocationMarker = null;
        this.currentMapLayer = 'osm';
        this.mapLayers = {};
        
        // 資料變數
        this.allLocations = [];
        this.filteredLocations = [];
        this.userLocation = null;
        
        // 篩選狀態
        this.currentFilters = {
            type: null,
            city: null,
            search: null,
            petTypes: [],
            emergency: false,
            highRating: false,
            nearby: false
        };
        
        // UI 狀態
        this.isSidebarOpen = window.innerWidth > 1024;
        this.isLoading = false;
        this.selectedLocation = null;
        
        // 配置
        this.config = {
            defaultCenter: [25.0330, 121.5654], // 台北市
            defaultZoom: 13,
            maxZoom: 19,
            nearbyRadius: 2000, // 2公里
            highRatingThreshold: 4.0,
            clusterRadius: 50,
            animationDuration: 300
        };
        
        // 圖標配置
        this.icons = {
            services: {
                hospital: '🏥',
                cosmetic: '✂️',
                park: '🌳',
                product: '🛒',
                shelter: '🏠',
                funeral: '⚱️',
                live: '🏨',
                boarding: '🐕',
                restaurant: '🍽️',
                default: '📍'
            },
            petTypes: {
                small_dog: '🐕‍',
                medium_dog: '🐕',
                large_dog: '🦮',
                cat: '🐈',
                bird: '🦜',
                rodent: '🐹',
                reptile: '🦎',
                other: '🦝'
            }
        };
        
        this.init();
    }
    
    /**
     * 初始化應用程式
     */
    async init() {
        console.log('🚀 初始化寵物地圖應用程式...');
        
        try {
            this.showLoading(true);
            
            // 初始化地圖
            await this.initMap();
            
            // 設置事件監聽器
            this.setupEventListeners();
            
            // 嘗試獲取用戶位置
            await this.getUserLocation();
            
            // 載入初始資料
            await this.loadLocations();
            
            console.log('✅ 地圖應用程式初始化完成');
        } catch (error) {
            console.error('❌ 初始化失敗:', error);
            this.showError('地圖初始化失敗，請重新整理頁面');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 初始化地圖
     */
    async initMap() {
        console.log('🗺️ 初始化地圖...');
        
        // 創建地圖
        this.map = L.map('pet-map', {
            center: this.config.defaultCenter,
            zoom: this.config.defaultZoom,
            zoomControl: false, // 自定義控制項
            attributionControl: true
        });
        
        // 添加地圖圖層
        this.setupMapLayers();
        
        // 創建標記群組
        this.markers = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: this.config.clusterRadius,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            iconCreateFunction: (cluster) => this.createClusterIcon(cluster)
        });
        
        this.map.addLayer(this.markers);
        
        // 設置地圖事件
        this.setupMapEvents();
        
        console.log('✅ 地圖初始化完成');
    }
    
    /**
     * 設置地圖圖層
     */
    setupMapLayers() {
        // OpenStreetMap
        this.mapLayers.osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: this.config.maxZoom
        });
        
        // 衛星圖層
        this.mapLayers.satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '© Esri',
            maxZoom: this.config.maxZoom
        });
        
        // 地形圖層
        this.mapLayers.terrain = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenTopoMap contributors',
            maxZoom: 15
        });
        
        // 預設使用 OSM
        this.mapLayers.osm.addTo(this.map);
    }
    
    /**
     * 設置地圖事件
     */
    setupMapEvents() {
        // 地圖點擊事件
        this.map.on('click', () => {
            this.hideLocationInfo();
        });
        
        // 視圖變更事件
        this.map.on('moveend zoomend', () => {
            this.updateNearbyFilter();
        });
        
        // 全螢幕事件
        this.map.on('fullscreenchange', () => {
            setTimeout(() => this.map.invalidateSize(), 100);
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
        const searchInput = document.getElementById('mapSearchInput');
        const searchBtn = document.getElementById('mapSearchBtn');
        
        if (searchInput && searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.performSearch();
            });
            
            // 即時搜尋（延遲執行）
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
                }, 500);
            });
        }
        
        // 服務分類篩選
        document.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (item.hasAttribute('disabled')) {
                    this.showNotification('此服務類型的資料即將上線，敬請期待！', 'info');
                    return;
                }
                
                const type = item.dataset.type;
                this.toggleServiceFilter(type, item);
            });
        });
        
        // 寵物類型篩選
        document.querySelectorAll('.pet-type-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const petType = checkbox.dataset.petType;
                this.togglePetTypeFilter(petType, checkbox.checked);
            });
        });
        
        // 快速篩選
        document.querySelectorAll('.quick-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const filter = checkbox.dataset.filter;
                this.toggleQuickFilter(filter, checkbox.checked);
            });
        });
        
        // 地圖控制按鈕
        this.setupMapControls();
        
        // 篩選控制
        const clearFiltersBtn = document.getElementById('clearFilters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearAllFilters());
        }
        
        // 響應式處理
        window.addEventListener('resize', () => this.handleResize());
        
        // 鍵盤快捷鍵
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
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
        
        // 全螢幕按鈕
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }
        
        // 圖層切換按鈕
        const layerBtn = document.getElementById('layerBtn');
        if (layerBtn) {
            layerBtn.addEventListener('click', () => this.toggleMapLayer());
        }
        
        // 重新整理按鈕
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshLocations());
        }
    }
    
    /**
     * 載入地點資料
     */
    async loadLocations() {
        console.log('📡 載入地點資料...');
        console.log('當前篩選條件:', this.currentFilters);
        
        try {
            this.showLoading(true);
            
            // 構建查詢參數
            const params = new URLSearchParams();
            
            if (this.currentFilters.type) {
                params.append('type', this.currentFilters.type);
            }
            if (this.currentFilters.city) {
                params.append('city', this.currentFilters.city);
            }
            if (this.currentFilters.search) {
                params.append('search', this.currentFilters.search);
            }
            
            // 寵物類型篩選
            this.currentFilters.petTypes.forEach(petType => {
                params.append(`support_${petType}`, 'true');
            });
            
            const url = `/api/locations/?${params.toString()}`;
            console.log('API 請求 URL:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 載入了', data.features?.length || 0, '個地點');
            
            if (data.features) {
                this.allLocations = data.features;
                this.applyClientSideFilters();
                this.displayMarkers();
                this.updateFilterDisplay();
            } else {
                throw new Error('API 回應格式錯誤');
            }
            
        } catch (error) {
            console.error('❌ 載入地點資料失敗:', error);
            this.showError('無法載入地點資料，請稍後再試');
            this.allLocations = [];
            this.filteredLocations = [];
            this.displayMarkers();
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 應用客戶端篩選
     */
    applyClientSideFilters() {
        this.filteredLocations = this.allLocations.filter(location => {
            const props = location.properties;
            
            // 24小時急診篩選
            if (this.currentFilters.emergency && !props.has_emergency) {
                return false;
            }
            
            // 高評分篩選
            if (this.currentFilters.highRating) {
                const rating = parseFloat(props.rating);
                if (isNaN(rating) || rating < this.config.highRatingThreshold) {
                    return false;
                }
            }
            
            // 附近距離篩選
            if (this.currentFilters.nearby && this.userLocation) {
                const distance = this.calculateDistance(
                    this.userLocation.lat,
                    this.userLocation.lng,
                    location.geometry.coordinates[1],
                    location.geometry.coordinates[0]
                );
                
                if (distance > this.config.nearbyRadius) {
                    return false;
                }
            }
            
            return true;
        });
        
        console.log(`🔍 篩選後顯示 ${this.filteredLocations.length} 個地點`);
    }
    
    /**
     * 顯示地圖標記
     */
    displayMarkers() {
        console.log('📍 更新地圖標記...');
        
        // 清除現有標記
        this.markers.clearLayers();
        
        if (!this.filteredLocations || this.filteredLocations.length === 0) {
            console.log('⚠️ 沒有地點資料要顯示');
            return;
        }
        
        let successCount = 0;
        let errorCount = 0;
        
        this.filteredLocations.forEach((location, index) => {
            try {
                if (!location.geometry?.coordinates) {
                    errorCount++;
                    return;
                }
                
                const [lng, lat] = location.geometry.coordinates;
                const props = location.properties;
                
                // 創建自定義標記
                const marker = this.createMarker(lat, lng, props);
                
                // 創建彈出視窗
                const popupContent = this.createPopupContent(props);
                marker.bindPopup(popupContent, {
                    maxWidth: 300,
                    className: 'custom-popup'
                });
                
                // 標記點擊事件
                marker.on('click', () => {
                    this.selectLocation(location);
                });
                
                this.markers.addLayer(marker);
                successCount++;
                
            } catch (error) {
                console.error(`❌ 處理地點 ${index} 時發生錯誤:`, error);
                errorCount++;
            }
        });
        
        console.log(`📊 標記處理完成: 成功 ${successCount} 個, 失敗 ${errorCount} 個`);
        
        // 調整地圖視角
        this.fitMapBounds();
    }
    
    /**
     * 創建地圖標記
     */
    createMarker(lat, lng, props) {
        // 決定圖標
        let icon = this.icons.services.default;
        let color = '#ffaa00';
        
        if (props.service_types && props.service_types.length > 0) {
            const serviceType = props.service_types[0].toLowerCase();
            
            if (serviceType.includes('醫療') || serviceType.includes('醫院')) {
                icon = this.icons.services.hospital;
                color = '#dc3545';
            } else if (serviceType.includes('美容')) {
                icon = this.icons.services.cosmetic;
                color = '#e91e63';
            } else if (serviceType.includes('公園')) {
                icon = this.icons.services.park;
                color = '#28a745';
            } else if (serviceType.includes('用品')) {
                icon = this.icons.services.product;
                color = '#007bff';
            } else if (serviceType.includes('收容')) {
                icon = this.icons.services.shelter;
                color = '#6f42c1';
            } else if (serviceType.includes('殯葬')) {
                icon = this.icons.services.funeral;
                color = '#6c757d';
            } else if (serviceType.includes('寄宿')) {
                icon = this.icons.services.boarding;
                color = '#fd7e14';
            }
        }
        
        // 24小時急診特殊樣式
        const isEmergency = props.has_emergency;
        const borderColor = isEmergency ? '#dc3545' : '#ffffff';
        const borderWidth = isEmergency ? '4px' : '3px';
        
        const customIcon = L.divIcon({
            html: `<div style="
                background: ${color};
                color: white;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: ${borderWidth} solid ${borderColor};
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                font-size: 18px;
                font-weight: bold;
                position: relative;
                cursor: pointer;
                transition: all 0.3s ease;
            " class="custom-marker-icon" data-emergency="${isEmergency}">${icon}</div>`,
            className: 'custom-marker',
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            popupAnchor: [0, -20]
        });
        
        const marker = L.marker([lat, lng], { icon: customIcon });
        
        // 添加 hover 效果
        marker.on('mouseover', function() {
            const iconElement = this.getElement().querySelector('.custom-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1.1)';
                iconElement.style.zIndex = '1000';
            }
        });
        
        marker.on('mouseout', function() {
            const iconElement = this.getElement().querySelector('.custom-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1)';
                iconElement.style.zIndex = 'auto';
            }
        });
        
        return marker;
    }
    
    /**
     * 創建叢集圖標
     */
    createClusterIcon(cluster) {
        const count = cluster.getChildCount();
        let size = 40;
        let className = 'marker-cluster-small';
        
        if (count >= 100) {
            size = 60;
            className = 'marker-cluster-large';
        } else if (count >= 10) {
            size = 50;
            className = 'marker-cluster-medium';
        }
        
        return L.divIcon({
            html: `<div style="
                background: rgba(255, 170, 0, 0.8);
                color: white;
                border-radius: 50%;
                width: ${size}px;
                height: ${size}px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: ${size > 40 ? '16px' : '14px'};
                border: 3px solid white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                cursor: pointer;
            ">${count}</div>`,
            className: `marker-cluster ${className}`,
            iconSize: [size, size]
        });
    }
    
    /**
     * 創建彈出視窗內容
     */
    createPopupContent(props) {
        let html = `<div class="popup-content">
            <h3>${props.name || '未命名地點'}</h3>`;
        
        // 地址
        if (props.address) {
            html += `<div class="popup-section">
                <div class="popup-address">
                    <i class="bi bi-geo-alt"></i>
                    ${props.address}
                </div>
            </div>`;
        }
        
        // 評分
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            html += `<div class="popup-section">
                <div class="popup-rating">
                    <span class="popup-stars">${stars}</span>
                    <span>${props.rating} (${props.rating_count || 0}則評價)</span>
                </div>
            </div>`;
        }
        
        // 24小時急診
        if (props.has_emergency) {
            html += `<div class="popup-section">
                <div class="popup-emergency">
                    <i class="bi bi-exclamation-triangle"></i>
                    24小時急診服務
                </div>
            </div>`;
        }
        
        // 服務類型
        if (props.service_types && props.service_types.length > 0) {
            html += `<div class="popup-section">
                <div class="popup-services">`;
            props.service_types.forEach(service => {
                html += `<span class="popup-service-tag">${service}</span>`;
            });
            html += `</div></div>`;
        }
        
        // 支援的寵物類型
        if (props.supported_pet_types && props.supported_pet_types.length > 0) {
            html += `<div class="popup-section">
                <div class="popup-pet-types">
                    <strong>支援寵物類型：</strong>
                    <div class="popup-pet-tags">`;
            
            props.supported_pet_types.forEach(petType => {
                let petIcon = '🐾';
                let tagClass = 'pet-type-tag';
                
                // 根據寵物類型設置圖標
                for (const [code, icon] of Object.entries(this.icons.petTypes)) {
                    if (petType.includes('小型犬') && code === 'small_dog') petIcon = icon;
                    else if (petType.includes('中型犬') && code === 'medium_dog') petIcon = icon;
                    else if (petType.includes('大型犬') && code === 'large_dog') petIcon = icon;
                    else if (petType.includes('貓') && code === 'cat') petIcon = icon;
                    else if (petType.includes('鳥') && code === 'bird') petIcon = icon;
                    else if (petType.includes('鼠') && code === 'rodent') petIcon = icon;
                    else if (petType.includes('爬蟲') && code === 'reptile') petIcon = icon;
                }
                
                html += `<span class="${tagClass}">${petIcon} ${petType}</span>`;
            });
            html += `</div></div>`;
        }
        
        // 聯絡資訊
        if (props.phone) {
            html += `<div class="popup-section">
                <div class="popup-contact">
                    <i class="bi bi-telephone"></i>
                    <a href="tel:${props.phone}">${props.phone}</a>
                </div>
            </div>`;
        }
        
        // 操作按鈕
        html += `<div class="popup-actions">`;
        if (props.phone) {
            html += `<a href="tel:${props.phone}" class="popup-btn secondary">
                <i class="bi bi-telephone"></i> 撥打電話
            </a>`;
        }
        if (props.address) {
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(props.address)}`;
            html += `<a href="${mapUrl}" target="_blank" class="popup-btn primary">
                <i class="bi bi-navigation"></i> 導航
            </a>`;
        }
        html += `</div></div>`;
        
        return html;
    }
    
    /**
     * 切換服務類型篩選
     */
    toggleServiceFilter(type, element) {
        const categoryItems = document.querySelectorAll('.category-item');
        categoryItems.forEach(item => item.classList.remove('active'));
        
        if (this.currentFilters.type === type) {
            this.currentFilters.type = null;
        } else {
            this.currentFilters.type = type;
            element.classList.add('active');
        }
        
        this.updateFilters();
    }
    
    /**
     * 切換寵物類型篩選
     */
    togglePetTypeFilter(petType, isChecked) {
        if (isChecked) {
            if (!this.currentFilters.petTypes.includes(petType)) {
                this.currentFilters.petTypes.push(petType);
            }
        } else {
            this.currentFilters.petTypes = this.currentFilters.petTypes.filter(type => type !== petType);
        }
        
        this.updateFilters();
    }
    
    /**
     * 切換快速篩選
     */
    toggleQuickFilter(filter, isChecked) {
        switch (filter) {
            case 'emergency':
                this.currentFilters.emergency = isChecked;
                break;
            case 'high-rating':
                this.currentFilters.highRating = isChecked;
                break;
            case 'nearby':
                this.currentFilters.nearby = isChecked;
                if (isChecked && !this.userLocation) {
                    this.locateUser();
                }
                break;
        }
        
        this.updateFilters();
    }
    
    /**
     * 執行搜尋
     */
    performSearch() {
        const searchInput = document.getElementById('mapSearchInput');
        const searchText = searchInput.value.trim();
        
        this.currentFilters.search = searchText || null;
        this.updateFilters();
    }
    
    /**
     * 更新篩選
     */
    async updateFilters() {
        console.log('🔄 更新篩選條件:', this.currentFilters);
        
        try {
            // 如果有伺服器端篩選需要重新載入
            const needsServerUpdate = this.currentFilters.type || this.currentFilters.search || this.currentFilters.petTypes.length > 0;
            
            if (needsServerUpdate) {
                await this.loadLocations();
            } else {
                this.applyClientSideFilters();
                this.displayMarkers();
                this.updateFilterDisplay();
            }
        } catch (error) {
            console.error('❌ 更新篩選失敗:', error);
            this.showError('篩選更新失敗');
        }
    }
    
    /**
     * 更新篩選顯示
     */
    updateFilterDisplay() {
        const activeFiltersEl = document.getElementById('activeFilters');
        const filterTagsEl = document.getElementById('filterTags');
        const filterCountEl = document.getElementById('filterCount');
        
        if (!activeFiltersEl || !filterTagsEl || !filterCountEl) return;
        
        // 更新地點數量
        filterCountEl.textContent = `顯示 ${this.filteredLocations.length} 個地點`;
        
        // 清空現有標籤
        filterTagsEl.innerHTML = '';
        
        let hasActiveFilters = false;
        
        // 服務類型標籤
        if (this.currentFilters.type) {
            const typeNames = {
                'hospital': '醫院',
                'cosmetic': '美容',
                'park': '公園',
                'product': '寵物用品',
                'shelter': '收容所',
                'funeral': '寵物殯葬',
                'boarding': '寄宿'
            };
            
            this.createFilterTag(
                typeNames[this.currentFilters.type] || this.currentFilters.type,
                () => this.clearServiceFilter()
            );
            hasActiveFilters = true;
        }
        
        // 寵物類型標籤
        this.currentFilters.petTypes.forEach(petType => {
            const petTypeNames = {
                'small_dog': '小型犬',
                'medium_dog': '中型犬',
                'large_dog': '大型犬',
                'cat': '貓咪',
                'bird': '鳥類',
                'rodent': '齧齒動物',
                'reptile': '爬蟲類',
                'other': '其他'
            };
            
            this.createFilterTag(
                petTypeNames[petType] || petType,
                () => this.removePetTypeFilter(petType)
            );
            hasActiveFilters = true;
        });
        
        // 搜尋標籤
        if (this.currentFilters.search) {
            this.createFilterTag(
                `搜尋: ${this.currentFilters.search}`,
                () => this.clearSearchFilter()
            );
            hasActiveFilters = true;
        }
        
        // 快速篩選標籤
        const quickFilterNames = {
            emergency: '🚨 24小時急診',
            highRating: '⭐ 高評分',
            nearby: '📍 附近2公里'
        };
        
        Object.entries(quickFilterNames).forEach(([key, name]) => {
            if (this.currentFilters[key === 'highRating' ? 'highRating' : key]) {
                this.createFilterTag(name, () => this.clearQuickFilter(key));
                hasActiveFilters = true;
            }
        });
        
        // 顯示/隱藏篩選狀態區域
        activeFiltersEl.style.display = hasActiveFilters ? 'flex' : 'none';
    }
    
    /**
     * 創建篩選標籤
     */
    createFilterTag(text, onRemove) {
        const filterTagsEl = document.getElementById('filterTags');
        
        const tag = document.createElement('span');
        tag.className = 'filter-tag';
        tag.innerHTML = `
            ${text}
            <span class="remove-tag" title="移除篩選">×</span>
        `;
        
        const removeBtn = tag.querySelector('.remove-tag');
        removeBtn.addEventListener('click', onRemove);
        
        filterTagsEl.appendChild(tag);
    }
    
    /**
     * 清除服務篩選
     */
    clearServiceFilter() {
        this.currentFilters.type = null;
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.remove('active');
        });
        this.updateFilters();
    }
    
    /**
     * 移除寵物類型篩選
     */
    removePetTypeFilter(petType) {
        this.currentFilters.petTypes = this.currentFilters.petTypes.filter(type => type !== petType);
        const checkbox = document.querySelector(`[data-pet-type="${petType}"]`);
        if (checkbox) checkbox.checked = false;
        this.updateFilters();
    }
    
    /**
     * 清除搜尋篩選
     */
    clearSearchFilter() {
        this.currentFilters.search = null;
        const searchInput = document.getElementById('mapSearchInput');
        if (searchInput) searchInput.value = '';
        this.updateFilters();
    }
    
    /**
     * 清除快速篩選
     */
    clearQuickFilter(filter) {
        if (filter === 'highRating') {
            this.currentFilters.highRating = false;
        } else {
            this.currentFilters[filter] = false;
        }
        
        const checkbox = document.querySelector(`[data-filter="${filter}"]`);
        if (checkbox) checkbox.checked = false;
        this.updateFilters();
    }
    
    /**
     * 清除所有篩選
     */
    clearAllFilters() {
        // 重置篩選條件
        this.currentFilters = {
            type: null,
            city: null,
            search: null,
            petTypes: [],
            emergency: false,
            highRating: false,
            nearby: false
        };
        
        // 重置 UI
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.remove('active');
        });
        
        document.querySelectorAll('.pet-type-filter, .quick-filter').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        const searchInput = document.getElementById('mapSearchInput');
        if (searchInput) searchInput.value = '';
        
        this.updateFilters();
        this.showNotification('已清除所有篩選條件', 'success');
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
                    resolve(null);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000 // 5分鐘快取
                }
            );
        });
    }
    
    /**
     * 定位用戶
     */
    async locateUser() {
        try {
            this.showLoading(true, '正在定位...');
            
            const location = await this.getUserLocation();
            
            if (location) {
                // 移動地圖到用戶位置
                this.map.setView([location.lat, location.lng], 15);
                
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
                            width: 20px;
                            height: 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border: 3px solid white;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                            font-size: 12px;
                        ">📍</div>`,
                        className: 'user-location-marker',
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    })
                }).addTo(this.map);
                
                this.userLocationMarker.bindPopup('<b>您的位置</b>').openPopup();
                
                this.showNotification('定位成功', 'success');
            } else {
                this.showNotification('無法取得您的位置，請檢查定位權限', 'warning');
            }
        } catch (error) {
            console.error('定位失敗:', error);
            this.showNotification('定位失敗', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 切換全螢幕
     */
    toggleFullscreen() {
        const mapContainer = document.querySelector('.map-main-container');
        
        if (!document.fullscreenElement) {
            mapContainer.requestFullscreen().then(() => {
                setTimeout(() => this.map.invalidateSize(), 100);
            }).catch(err => {
                console.error('無法進入全螢幕:', err);
            });
        } else {
            document.exitFullscreen().then(() => {
                setTimeout(() => this.map.invalidateSize(), 100);
            });
        }
    }
    
    /**
     * 切換地圖圖層
     */
    toggleMapLayer() {
        const layers = ['osm', 'satellite', 'terrain'];
        const currentIndex = layers.indexOf(this.currentMapLayer);
        const nextIndex = (currentIndex + 1) % layers.length;
        const nextLayer = layers[nextIndex];
        
        // 移除當前圖層
        this.map.removeLayer(this.mapLayers[this.currentMapLayer]);
        
        // 添加新圖層
        this.mapLayers[nextLayer].addTo(this.map);
        this.currentMapLayer = nextLayer;
        
        const layerNames = {
            osm: '街道地圖',
            satellite: '衛星影像',
            terrain: '地形圖'
        };
        
        this.showNotification(`已切換至${layerNames[nextLayer]}`, 'info');
    }
    
    /**
     * 重新載入地點
     */
    async refreshLocations() {
        this.showNotification('正在重新載入地點...', 'info');
        await this.loadLocations();
        this.showNotification('地點資料已更新', 'success');
    }
    
    /**
     * 調整地圖視角
     */
    fitMapBounds() {
        if (this.filteredLocations.length === 0) return;
        
        try {
            const bounds = this.markers.getBounds();
            if (bounds.isValid()) {
                this.map.fitBounds(bounds, {
                    padding: [20, 20],
                    maxZoom: 16
                });
            }
        } catch (error) {
            console.error('調整地圖視角失敗:', error);
        }
    }
    
    /**
     * 切換側邊欄
     */
    toggleSidebar() {
        const sidebar = document.getElementById('mapSidebar');
        const toggle = document.getElementById('sidebarToggle');
        
        this.isSidebarOpen = !this.isSidebarOpen;
        
        if (this.isSidebarOpen) {
            sidebar.classList.add('show');
            toggle.innerHTML = '<i class="bi bi-x"></i>';
        } else {
            sidebar.classList.remove('show');
            toggle.innerHTML = '<i class="bi bi-list"></i>';
        }
        
        // 重新調整地圖大小
        setTimeout(() => this.map.invalidateSize(), 300);
    }
    
    /**
     * 響應式處理
     */
    handleResize() {
        // 在桌面版自動顯示側邊欄
        if (window.innerWidth > 1024) {
            const sidebar = document.getElementById('mapSidebar');
            const toggle = document.getElementById('sidebarToggle');
            
            sidebar.classList.add('show');
            toggle.style.display = 'none';
            this.isSidebarOpen = true;
        } else {
            const toggle = document.getElementById('sidebarToggle');
            toggle.style.display = 'flex';
        }
        
        // 重新調整地圖大小
        setTimeout(() => this.map.invalidateSize(), 100);
    }
    
    /**
     * 鍵盤快捷鍵處理
     */
    handleKeyboardShortcuts(e) {
        // Escape 關閉側邊欄或資訊卡
        if (e.key === 'Escape') {
            if (this.selectedLocation) {
                this.hideLocationInfo();
            } else if (this.isSidebarOpen && window.innerWidth <= 1024) {
                this.toggleSidebar();
            }
        }
        
        // Ctrl+F 聚焦搜尋框
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('mapSearchInput');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl+L 定位
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            this.locateUser();
        }
    }
    
    /**
     * 選擇地點
     */
    selectLocation(location) {
        this.selectedLocation = location;
        this.showLocationInfo(location);
    }
    
        /**
     * 顯示地點資訊
     */
    showLocationInfo(location) {
        const infoCard = document.getElementById('locationInfoCard');
        const locationName = document.getElementById('locationName');
        const locationContent = document.getElementById('locationInfoContent');
        
        if (!infoCard || !locationName || !locationContent) return;
        
        const props = location.properties;
        
        // 設置標題
        locationName.textContent = props.name || '未命名地點';
        
        // 設置內容
        locationContent.innerHTML = this.createDetailedLocationInfo(props);
        
        // 顯示資訊卡
        infoCard.style.display = 'block';
        
        // 設置動畫效果
        infoCard.style.opacity = '0';
        infoCard.style.transform = 'translateY(-20px)';
        
        requestAnimationFrame(() => {
            infoCard.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            infoCard.style.opacity = '1';
            infoCard.style.transform = 'translateY(0)';
        });
        
        // 設置關閉按鈕事件
        const closeBtn = document.getElementById('closeInfoBtn');
        if (closeBtn) {
            closeBtn.onclick = () => this.hideLocationInfo();
        }
        
        // 設置滾動到頂部
        locationContent.scrollTop = 0;
        
        // 如果在手機版，隱藏側邊欄以顯示更多空間
        if (window.innerWidth <= 768 && this.isSidebarOpen) {
            this.toggleSidebar();
        }
        
        // 在地圖上高亮顯示選中的標記
        this.highlightSelectedMarker(location);
        
        // 記錄選中的地點（用於分析）
        console.log('用戶選擇地點:', props.name);
        
        // 可選：追蹤使用者行為分析
        if (typeof gtag !== 'undefined') {
            gtag('event', 'location_select', {
                'event_category': 'map_interaction',
                'event_label': props.name,
                'location_type': props.service_types?.[0] || 'unknown'
            });
        }
    }
        /**
     * 計算兩點間距離（公尺）
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
     * 更新附近篩選
     */
    updateNearbyFilter() {
        if (this.currentFilters.nearby && this.userLocation) {
            // 當地圖移動時重新應用附近篩選
            this.applyClientSideFilters();
            this.displayMarkers();
            this.updateFilterDisplay();
        }
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
        // 創建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="bi bi-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        // 添加樣式
        notification.style.cssText = `
            position: fixed;
            top: 120px;
            right: 20px;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 300px;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
        `;
        
        // 添加到頁面
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
        if (this.map) {
            this.map.remove();
        }
        
        // 移除事件監聽器
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('keydown', this.handleKeyboardShortcuts);
    }

    // 在類別外添加的初始化代碼
    }

    // 動畫樣式 - 添加到頁面
    const animationStyles = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .notification-content {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
        }
        
        .notification-close {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 16px;
            padding: 4px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .notification-close:hover {
            background-color: rgba(255,255,255,0.2);
        }
    `;

    // 添加動畫樣式到頁面
    if (!document.getElementById('map-animations')) {
        const styleSheet = document.createElement('style');
        styleSheet.id = 'map-animations';
        styleSheet.textContent = animationStyles;
        document.head.appendChild(styleSheet);
    }

    // 全域變數和初始化
    let petMapApp;

    // 頁面載入完成後初始化
    document.addEventListener('DOMContentLoaded', function() {
        console.log('📱 頁面載入完成，初始化地圖應用程式...');
        
        try {
            petMapApp = new PetMapApp();
        } catch (error) {
            console.error('❌ 地圖應用程式初始化失敗:', error);
            
            // 顯示錯誤訊息給用戶
            const mapArea = document.querySelector('.map-area');
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
                    ">
                        <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545; margin-bottom: 1rem;"></i>
                        <h3>地圖載入失敗</h3>
                        <p>很抱歉，地圖服務暫時無法使用。請稍後重新整理頁面再試。</p>
                        <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 1rem;">
                            <i class="bi bi-arrow-clockwise me-1"></i>重新載入
                        </button>
                    </div>
                `;
            }
        }
    });

    // 頁面卸載時清理資源
    window.addEventListener('beforeunload', function() {
        if (petMapApp) {
            petMapApp.destroy();
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
    window.PetMapApp = PetMapApp;