// 優化後的寵物地圖應用程式
class PetMapApp {
    constructor() {
        // 地圖相關
        this.map = null;
        this.markers = null;
        this.userLocationMarker = null;
        this.currentMapLayer = 'osm';
        this.mapLayers = {};
        this.selectedMarker = null;
        
        // 資料
        this.allLocations = [];
        this.filteredLocations = [];
        this.userLocation = null;
        
        // 篩選狀態
        this.currentFilters = {
            type: null,
            search: null,
            petTypes: [],
            emergency: false,
            highRating: false,
            nearby: false
        };
        
        // UI 狀態
        this.isSidebarOpen = window.innerWidth > 1024;
        this.selectedLocation = null;
        
        // 配置
        this.config = {
            defaultCenter: [25.0330, 121.5654],
            defaultZoom: 13,
            nearbyRadius: 2000,
            highRatingThreshold: 4.0
        };
        
        // 圖標配置
        this.icons = {
            hospital: '🏥',
            cosmetic: '✂️',
            park: '🌳',
            product: '🛒',
            shelter: '🏠',
            funeral: '⚱️',
            boarding: '🐕',
            live: '🏨',        // 住宿
            restaurant: '🍽️', // 餐廳
            default: '📍'
        };
        
        this.init();
    }
    
    /**
     * 初始化應用程式
     */
    async init() {
        console.log('🚀 初始化寵物地圖...');
        
        try {
            this.showLoading(true);
            await this.initMap();
            this.setupEventListeners();
            await this.getUserLocation();
            await this.loadLocations();
            console.log('✅ 地圖初始化完成');
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
        this.map = L.map('pet-map', {
            center: this.config.defaultCenter,
            zoom: this.config.defaultZoom,
            zoomControl: false
        });
        
        this.setupMapLayers();
        
        this.markers = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 50,
            iconCreateFunction: (cluster) => this.createClusterIcon(cluster)
        });
        
        this.map.addLayer(this.markers);
        this.setupMapEvents();
    }
    
    /**
     * 設置地圖圖層
     */
    setupMapLayers() {
        this.mapLayers.osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        });
        
        this.mapLayers.satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '© Esri'
        });
        
        this.mapLayers.osm.addTo(this.map);
    }
    
    /**
     * 設置地圖事件
     */
    setupMapEvents() {
        this.map.on('click', () => {});
        this.map.on('moveend zoomend', () => this.updateNearbyFilter());
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
                }, 500);
            });
        }
        
        // 服務分類篩選
        document.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                const type = item.dataset.type;
                
                // 檢查是否為即將推出的服務
                if (item.classList.contains('coming-soon')) {
                    this.showNotification('此服務類型即將推出，敬請期待！', 'info');
                    return;
                }
                
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
        
        // 清除篩選
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
        const locateBtn = document.getElementById('locateBtn');
        if (locateBtn) {
            locateBtn.addEventListener('click', () => this.locateUser());
        }
        
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }
        
        const layerBtn = document.getElementById('layerBtn');
        if (layerBtn) {
            layerBtn.addEventListener('click', () => this.toggleMapLayer());
        }
        
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
        
        try {
            this.showLoading(true);
            
            const params = new URLSearchParams();
            
            if (this.currentFilters.type) {
                params.append('type', this.currentFilters.type);
            }
            if (this.currentFilters.search) {
                params.append('search', this.currentFilters.search);
            }
            
            this.currentFilters.petTypes.forEach(petType => {
                params.append(`support_${petType}`, 'true');
            });
            
            const url = `/api/locations/?${params.toString()}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
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
            
            if (this.currentFilters.emergency && !props.has_emergency) {
                return false;
            }
            
            if (this.currentFilters.highRating) {
                const rating = parseFloat(props.rating);
                if (isNaN(rating) || rating < this.config.highRatingThreshold) {
                    return false;
                }
            }
            
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
        
        this.markers.clearLayers();
        
        if (!this.filteredLocations || this.filteredLocations.length === 0) {
            return;
        }
        
        this.filteredLocations.forEach((location) => {
            try {
                if (!location.geometry?.coordinates) return;
                
                const [lng, lat] = location.geometry.coordinates;
                const props = location.properties;
                
                const marker = this.createMarker(lat, lng, props);
                const popupContent = this.createPopupContent(props);
                
                marker.bindPopup(popupContent, {
                    maxWidth: 300,
                    className: 'custom-popup'
                });
                
                marker.on('click', () => this.selectLocation(location));
                this.markers.addLayer(marker);
                
            } catch (error) {
                console.error('❌ 處理地點時發生錯誤:', error);
            }
        });
        
        this.fitMapBounds();
    }
    
    /**
     * 創建地圖標記
     */
    createMarker(lat, lng, props) {
        let icon = this.icons.default;
        let color = '#ffaa00';
        
        if (props.service_types && props.service_types.length > 0) {
            const serviceType = props.service_types[0].toLowerCase();
            
            if (serviceType.includes('醫療') || serviceType.includes('醫院')) {
                icon = this.icons.hospital;
                color = '#dc3545';
            } else if (serviceType.includes('美容')) {
                icon = this.icons.cosmetic;
                color = '#e91e63';
            } else if (serviceType.includes('公園')) {
                icon = this.icons.park;
                color = '#28a745';
            } else if (serviceType.includes('用品')) {
                icon = this.icons.product;
                color = '#007bff';
            } else if (serviceType.includes('收容')) {
                icon = this.icons.shelter;
                color = '#6f42c1';
            } else if (serviceType.includes('殯葬')) {
                icon = this.icons.funeral;
                color = '#6c757d';
            } else if (serviceType.includes('寄宿')) {
                icon = this.icons.boarding;
                color = '#fd7e14';
            } else if (serviceType.includes('住宿') || serviceType.includes('旅館')) {
                icon = this.icons.live;
                color = '#20c997';
            } else if (serviceType.includes('餐廳') || serviceType.includes('餐飲')) {
                icon = this.icons.restaurant;
                color = '#fd7e14';
            }
        }
        
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
                cursor: pointer;
                transition: all 0.3s ease;
            " class="custom-marker-icon">${icon}</div>`,
            className: 'custom-marker',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });
        
        const marker = L.marker([lat, lng], { icon: customIcon });
        
        // hover 效果
        marker.on('mouseover', function() {
            const iconElement = this.getElement().querySelector('.custom-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1.1)';
            }
        });
        
        marker.on('mouseout', function() {
            const iconElement = this.getElement().querySelector('.custom-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1)';
            }
        });
        
        return marker;
    }
    
    /**
     * 創建叢集圖標
     */
    createClusterIcon(cluster) {
        const count = cluster.getChildCount();
        let size = count >= 100 ? 60 : count >= 10 ? 50 : 40;
        
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
                border: 3px solid white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                cursor: pointer;
            ">${count}</div>`,
            className: 'marker-cluster',
            iconSize: [size, size]
        });
    }
    
    /**
     * 創建彈出視窗內容
     */
    createPopupContent(props) {
        let html = `<div class="popup-content">
            <h3>${props.name || '未命名地點'}</h3>`;
        
        if (props.address) {
            html += `<div class="popup-section">
                <div class="popup-address">
                    <i class="bi bi-geo-alt"></i>
                    ${props.address}
                </div>
            </div>`;
        }
        
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            html += `<div class="popup-section">
                <div class="popup-rating">
                    <span class="popup-stars">${stars}</span>
                    <span>${props.rating} (${props.rating_count || 0}則評價)</span>
                </div>
            </div>`;
        }
        
        if (props.has_emergency) {
            html += `<div class="popup-section">
                <div class="popup-emergency">
                    <i class="bi bi-exclamation-triangle"></i>
                    24小時急診服務
                </div>
            </div>`;
        }
        
        if (props.service_types && props.service_types.length > 0) {
            html += `<div class="popup-section">
                <div class="popup-services">`;
            props.service_types.forEach(service => {
                html += `<span class="popup-service-tag">${service}</span>`;
            });
            html += `</div></div>`;
        }
        
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
     * 篩選相關方法
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
    
    performSearch() {
        const searchInput = document.getElementById('mapSearchInput');
        const searchText = searchInput.value.trim();
        
        this.currentFilters.search = searchText || null;
        this.updateFilters();
    }
    
    async updateFilters() {
        try {
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
    
    updateFilterDisplay() {
        const activeFiltersEl = document.getElementById('activeFilters');
        const filterTagsEl = document.getElementById('filterTags');
        const filterCountEl = document.getElementById('filterCount');
        
        if (!activeFiltersEl || !filterTagsEl || !filterCountEl) return;
        
        filterCountEl.textContent = `顯示 ${this.filteredLocations.length} 個地點`;
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
                'boarding': '寄宿',
                'live': '住宿',
                'restaurant': '餐廳'
            };
            
            this.createFilterTag(
                typeNames[this.currentFilters.type] || this.currentFilters.type,
                () => this.clearServiceFilter()
            );
            hasActiveFilters = true;
        }
        
        // 其他篩選標籤...
        if (this.currentFilters.search) {
            this.createFilterTag(
                `搜尋: ${this.currentFilters.search}`,
                () => this.clearSearchFilter()
            );
            hasActiveFilters = true;
        }
        
        activeFiltersEl.style.display = hasActiveFilters ? 'flex' : 'none';
    }
    
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
    
    clearServiceFilter() {
        this.currentFilters.type = null;
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.remove('active');
        });
        this.updateFilters();
    }
    
    clearSearchFilter() {
        this.currentFilters.search = null;
        const searchInput = document.getElementById('mapSearchInput');
        if (searchInput) searchInput.value = '';
        this.updateFilters();
    }
    
    clearAllFilters() {
        this.currentFilters = {
            type: null,
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
     * 地理位置相關
     */
    async getUserLocation() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
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
                    maximumAge: 300000
                }
            );
        });
    }
    
    async locateUser() {
        try {
            this.showLoading(true, '正在定位...');
            
            const location = await this.getUserLocation();
            
            if (location) {
                this.map.setView([location.lat, location.lng], 15);
                
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
    
    calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371000;
        const dLat = this.toRadians(lat2 - lat1);
        const dLng = this.toRadians(lng2 - lng1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
    
    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
    
    updateNearbyFilter() {
        if (this.currentFilters.nearby && this.userLocation) {
            this.applyClientSideFilters();
            this.displayMarkers();
            this.updateFilterDisplay();
        }
    }
    
    /**
     * 地圖控制
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
    
    toggleMapLayer() {
        const layers = ['osm', 'satellite'];
        const currentIndex = layers.indexOf(this.currentMapLayer);
        const nextIndex = (currentIndex + 1) % layers.length;
        const nextLayer = layers[nextIndex];
        
        this.map.removeLayer(this.mapLayers[this.currentMapLayer]);
        this.mapLayers[nextLayer].addTo(this.map);
        this.currentMapLayer = nextLayer;
        
        const layerNames = {
            osm: '街道地圖',
            satellite: '衛星影像'
        };
        
        this.showNotification(`已切換至${layerNames[nextLayer]}`, 'info');
    }
    
    async refreshLocations() {
        this.showNotification('正在重新載入地點...', 'info');
        await this.loadLocations();
        this.showNotification('地點資料已更新', 'success');
    }
    
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
     * UI 控制
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
        
        setTimeout(() => this.map.invalidateSize(), 300);
    }
    
    handleResize() {
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
        
        setTimeout(() => this.map.invalidateSize(), 100);
    }
    
    handleKeyboardShortcuts(e) {
        if (e.key === 'Escape') {
            if (this.isSidebarOpen && window.innerWidth <= 1024) {
                this.toggleSidebar();
            }
        }
        
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('mapSearchInput');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            this.locateUser();
        }
    }
    
    /**
     * 地點資訊
     */
    selectLocation(location) {
        this.selectedLocation = location;
    }
        
    highlightSelectedMarker(location) {
        this.clearMarkerHighlight();
        
        this.markers.eachLayer((marker) => {
            const markerLatLng = marker.getLatLng();
            const locationCoords = location.geometry.coordinates;
            
            if (Math.abs(markerLatLng.lat - locationCoords[1]) < 0.0001 && 
                Math.abs(markerLatLng.lng - locationCoords[0]) < 0.0001) {
                
                const iconElement = marker.getElement()?.querySelector('.custom-marker-icon');
                if (iconElement) {
                    iconElement.style.transform = 'scale(1.2)';
                    iconElement.style.zIndex = '10000';
                    iconElement.style.boxShadow = '0 0 20px rgba(255, 170, 0, 0.8)';
                    iconElement.classList.add('marker-selected');
                    this.selectedMarker = marker;
                }
            }
        });
    }
    
    clearMarkerHighlight() {
        if (this.selectedMarker) {
            const iconElement = this.selectedMarker.getElement()?.querySelector('.custom-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1)';
                iconElement.style.zIndex = 'auto';
                iconElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)';
                iconElement.classList.remove('marker-selected');
            }
            this.selectedMarker = null;
        }
    }
    
    /**
     * 工具方法
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
    }
    
    showNotification(message, type = 'info', duration = 3000) {
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
            animation: slideInRight 0.3s ease;
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
    
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }
    
    getNotificationColor(type) {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        return colors[type] || colors.info;
    }
    
    showError(message) {
        this.showNotification(message, 'error', 5000);
    }
}

// 動畫樣式
const animationStyles = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
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
    
    .info-section {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .info-section h4 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-dark);
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .info-section p {
        margin: 0;
        color: #666;
        line-height: 1.5;
    }
    
    .phone-link {
        color: var(--primary-orange);
        text-decoration: none;
        font-weight: 500;
    }
    
    .phone-link:hover {
        text-decoration: underline;
    }
    
    .emergency-badge {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        color: #d32f2f;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #ef5350;
    }
    
    .info-actions {
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 2px solid #f0f0f0;
    }
    
    .action-buttons {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
    }
    
    .info-btn {
        padding: 12px 16px;
        border-radius: 8px;
        text-decoration: none;
        text-align: center;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        cursor: pointer;
    }
    
    .info-btn.primary {
        background: var(--primary-orange);
        color: white;
    }
    
    .info-btn.secondary {
        background: #f8f9fa;
        color: var(--text-dark);
        border: 1px solid #dee2e6;
    }
    
    .info-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
`;

// 添加樣式到頁面
if (!document.getElementById('map-animations')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'map-animations';
    styleSheet.textContent = animationStyles;
    document.head.appendChild(styleSheet);
}

// 全域變數
let petMapApp;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 地圖頁面初始化...');
    
    try {
        petMapApp = new PetMapApp();
    } catch (error) {
        console.error('❌ 地圖初始化失敗:', error);
        
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

// 清理資源
window.addEventListener('beforeunload', function() {
    if (petMapApp && petMapApp.map) {
        petMapApp.map.remove();
    }
});

// 錯誤處理
window.addEventListener('error', function(e) {
    console.error('JavaScript 錯誤:', e.error);
});

// 導出給其他腳本使用
window.PetMapApp = PetMapApp;