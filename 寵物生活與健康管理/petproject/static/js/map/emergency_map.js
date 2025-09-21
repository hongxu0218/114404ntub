// 24小時急診地圖應用程式 - 使用 Leaflet + OpenStreetMap - Part 1

class EmergencyMapApp {
    constructor() {
        // Leaflet 地圖相關
        this.map = null;
        this.markers = null;
        this.userLocationMarker = null;
        this.selectedMarker = null;
        this.routingControl = null;
        
        // 資料
        this.allHospitals = [];
        this.filteredHospitals = [];
        this.userLocation = null;
        
        // 篩選狀態
        this.currentFilters = {
            search: null,
            city: null,
            petTypes: [],
            distance: null
        };
        
        // UI 狀態
        this.isSidebarOpen = window.innerWidth > 1024;
        this.selectedHospital = null;
        
        // 配置
        this.config = {
            defaultCenter: [25.0330, 121.5654], // 台北
            defaultZoom: 13,
            emergencyIcon: '🏥',
            userIcon: '📍'
        };
        
//         console.log('🚨 急診地圖初始化 (Leaflet版本)...');
    }
    
    /**
     * 初始化應用程式
     */
    async init() {
        try {
            this.showLoading(true);
            this.initLeafletMap();
            this.setupEventListeners();
            await this.getUserLocation();
            await this.loadEmergencyHospitals();
//             console.log('✅ 急診地圖初始化完成');
        } catch (error) {
            console.error('❌ 急診地圖初始化失敗:', error);
            this.showError('急診地圖初始化失敗，請重新整理頁面');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 初始化 Leaflet 地圖
     */
    initLeafletMap() {
        const center = this.userLocation || this.config.defaultCenter;
        
        this.map = L.map('emergency-map', {
            center: center,
            zoom: this.config.defaultZoom,
            zoomControl: false
        });
        
        // 添加 OpenStreetMap 圖層
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);
        
        // 初始化標記集群
        this.markers = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 50,
            iconCreateFunction: (cluster) => this.createClusterIcon(cluster)
        });
        
        this.map.addLayer(this.markers);
        
        // 添加縮放控制到右下角
        L.control.zoom({
            position: 'bottomright'
        }).addTo(this.map);
    
        
//         console.log('🗺️ Leaflet 地圖初始化完成');
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
                }, 500);
            });
        }
        
        // 城市篩選
        const cityFilter = document.getElementById('cityFilter');
        if (cityFilter) {
            cityFilter.addEventListener('change', () => {
                this.currentFilters.city = cityFilter.value || null;
                this.updateFilters();
            });
        }
        
        // 寵物類型篩選
        document.querySelectorAll('.pet-type-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const petType = checkbox.dataset.petType;
                this.togglePetTypeFilter(petType, checkbox.checked);
            });
        });
        
        // 距離篩選
        document.querySelectorAll('.distance-radio').forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    this.currentFilters.distance = radio.value || null;
                    if (radio.value && !this.userLocation) {
                        this.locateUser();
                    }
                    this.updateFilters();
                }
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
        
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshHospitals());
        }
        
        const routeBtn = document.getElementById('routeBtn');
        if (routeBtn) {
            routeBtn.addEventListener('click', () => this.showRouteToSelected());
        }
    }

    // 24小時急診地圖應用程式 - Part 2: 資料載入與篩選

    /**
     * 載入急診醫院資料
     */
    async loadEmergencyHospitals() {
//         console.log('🏥 載入急診醫院資料...');
        
        try {
            this.showLoading(true, '載入急診醫院資料中...');
            
            const params = new URLSearchParams();
            params.append('emergency', 'true'); // 只要急診醫院
            
            if (this.currentFilters.search) {
                params.append('search', this.currentFilters.search);
            }
            if (this.currentFilters.city) {
                params.append('city', this.currentFilters.city);
            }
            
            this.currentFilters.petTypes.forEach(petType => {
                params.append(`support_${petType}`, 'true');
            });
            
            const url = `/api/emergency-locations/?${params.toString()}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.features) {
                this.allHospitals = data.features;
                this.applyClientSideFilters();
                this.displayHospitalMarkers();
                this.updateHospitalList();
                this.updateFilterDisplay();
//                 console.log(`✅ 載入 ${this.filteredHospitals.length} 間急診醫院`);
            } else {
                throw new Error('API 回應格式錯誤');
            }
            
        } catch (error) {
            console.error('❌ 載入急診醫院失敗:', error);
            this.showError('無法載入急診醫院資料，請稍後再試');
            this.allHospitals = [];
            this.filteredHospitals = [];
            this.displayHospitalMarkers();
            this.updateHospitalList();
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 應用客戶端篩選
     */
    applyClientSideFilters() {
        this.filteredHospitals = this.allHospitals.filter(hospital => {
            // 距離篩選
            if (this.currentFilters.distance && this.userLocation) {
                const distance = this.calculateDistance(
                    this.userLocation.lat,
                    this.userLocation.lng,
                    hospital.geometry.coordinates[1],
                    hospital.geometry.coordinates[0]
                );
                
                if (distance > parseInt(this.currentFilters.distance)) {
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
        
//         console.log(`🔍 篩選後顯示 ${this.filteredHospitals.length} 間急診醫院`);
    }
    
    /**
     * 篩選相關方法
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
    
    performSearch() {
        const searchInput = document.getElementById('emergencySearchInput');
        const searchText = searchInput.value.trim();
        
        this.currentFilters.search = searchText || null;
        this.updateFilters();
    }
    
    async updateFilters() {
        try {
            await this.loadEmergencyHospitals();
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
        
        filterCountEl.textContent = `顯示 ${this.filteredHospitals.length} 間急診醫院`;
        filterTagsEl.innerHTML = '';
        
        let hasActiveFilters = false;
        
        // 搜尋標籤
        if (this.currentFilters.search) {
            this.createFilterTag(
                `搜尋: ${this.currentFilters.search}`,
                () => this.clearSearchFilter()
            );
            hasActiveFilters = true;
        }
        
        // 城市標籤
        if (this.currentFilters.city) {
            this.createFilterTag(
                `地區: ${this.currentFilters.city}`,
                () => this.clearCityFilter()
            );
            hasActiveFilters = true;
        }
        
        // 距離標籤
        if (this.currentFilters.distance) {
            const distanceText = this.formatDistance(parseInt(this.currentFilters.distance));
            this.createFilterTag(
                `距離: ${distanceText}內`,
                () => this.clearDistanceFilter()
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
                () => this.clearPetTypeFilter(petType)
            );
            hasActiveFilters = true;
        });
        
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
    
    clearSearchFilter() {
        this.currentFilters.search = null;
        const searchInput = document.getElementById('emergencySearchInput');
        if (searchInput) searchInput.value = '';
        this.updateFilters();
    }
    
    clearCityFilter() {
        this.currentFilters.city = null;
        const cityFilter = document.getElementById('cityFilter');
        if (cityFilter) cityFilter.value = '';
        this.updateFilters();
    }
    
    clearDistanceFilter() {
        this.currentFilters.distance = null;
        document.querySelectorAll('.distance-radio').forEach(radio => {
            radio.checked = radio.value === '';
        });
        this.updateFilters();
    }
    
    clearPetTypeFilter(petType) {
        this.currentFilters.petTypes = this.currentFilters.petTypes.filter(type => type !== petType);
        const checkbox = document.querySelector(`[data-pet-type="${petType}"]`);
        if (checkbox) checkbox.checked = false;
        this.updateFilters();
    }
    
    clearAllFilters() {
        this.currentFilters = {
            search: null,
            city: null,
            petTypes: [],
            distance: null
        };
        
        // 重置 UI
        const searchInput = document.getElementById('emergencySearchInput');
        if (searchInput) searchInput.value = '';
        
        const cityFilter = document.getElementById('cityFilter');
        if (cityFilter) cityFilter.value = '';
        
        document.querySelectorAll('.pet-type-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        document.querySelectorAll('.distance-radio').forEach(radio => {
            radio.checked = radio.value === '';
        });
        
        this.updateFilters();
        this.showNotification('已清除所有篩選條件', 'success');
    }

    // 24小時急診地圖應用程式 - Part 3: 地圖標記與視覺化

    /**
     * 顯示醫院標記
     */
    displayHospitalMarkers() {
//         console.log('📍 更新急診醫院標記...');
        
        // 清除現有標記
        this.markers.clearLayers();
        
        if (!this.filteredHospitals || this.filteredHospitals.length === 0) {
            return;
        }
        
        this.filteredHospitals.forEach((hospital, index) => {
            try {
                if (!hospital.geometry?.coordinates) return;
                
                const [lng, lat] = hospital.geometry.coordinates;
                const props = hospital.properties;
                
                const marker = this.createHospitalMarker(lat, lng, props, index);
                
                // 創建彈出視窗
                const popupContent = this.createHospitalPopupContent(props, hospital);
                marker.bindPopup(popupContent, {
                    maxWidth: 300,
                    className: 'emergency-popup'
                });
                
                // 點擊標記
                marker.on('click', () => {
                    this.selectHospital(hospital, marker);
                });
                
                this.markers.addLayer(marker);
                
            } catch (error) {
                console.error('❌ 處理醫院標記時發生錯誤:', error);
            }
        });
        
        this.fitMapBounds();
    }
    
    /**
     * 創建醫院標記
     */
    createHospitalMarker(lat, lng, props, index) {
        // 計算距離（如果有用戶位置）
        let distance = null;
        if (this.userLocation) {
            distance = this.calculateDistance(
                this.userLocation.lat, this.userLocation.lng, lat, lng
            );
        }
        
        // 根據距離決定標記顏色
        let color = '#dc3545'; // 預設紅色
        if (distance) {
            if (distance <= 1000) color = '#28a745'; // 綠色：1公里內
            else if (distance <= 3000) color = '#ffc107'; // 黃色：3公里內
            else color = '#dc3545'; // 紅色：3公里以上
        }
        
        // 創建自訂圖標
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
                border: 3px solid #ffffff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
                font-size: 12px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
            " class="emergency-marker-icon">🏥</div>`,
            className: 'emergency-marker',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });
        
        const marker = L.marker([lat, lng], { icon: customIcon });
        
        // hover 效果
        marker.on('mouseover', function() {
            const iconElement = this.getElement().querySelector('.emergency-marker-icon');
            if (iconElement) {
                iconElement.style.transform = 'scale(1.1)';
            }
        });
        
        marker.on('mouseout', function() {
            const iconElement = this.getElement().querySelector('.emergency-marker-icon');
            if (iconElement && this !== emergencyMapApp.selectedMarker) {
                iconElement.style.transform = 'scale(1)';
            }
        });
        
        return marker;
    }
    
    /**
     * 創建標記集群圖標
     */
    createClusterIcon(cluster) {
        const count = cluster.getChildCount();
        let size = count >= 100 ? 60 : count >= 10 ? 50 : 40;
        
        return L.divIcon({
            html: `<div style="
                background: rgba(220, 53, 69, 0.8);
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
            className: 'emergency-marker-cluster',
            iconSize: [size, size]
        });
    }
    
    /**
     * 創建醫院彈出視窗內容
     */
    createHospitalPopupContent(props, hospital) {
        let distance = '';
        if (this.userLocation) {
            const dist = this.calculateDistance(
                this.userLocation.lat, this.userLocation.lng,
                hospital.geometry.coordinates[1], hospital.geometry.coordinates[0]
            );
            distance = `<div class="emergency-popup-distance">📍 距離約 ${this.formatDistance(dist)}</div>`;
        }
        
        let html = `<div class="emergency-popup-content">
            <h3>${props.name || '急診醫院'} 🏥</h3>`;
        
        if (props.address) {
            html += `<div class="emergency-popup-section">
                <div class="emergency-popup-address">
                    <i class="bi bi-geo-alt"></i>
                    ${props.address}
                </div>
            </div>`;
        }
        
        if (props.phone) {
            html += `<div class="emergency-popup-section">
                <div class="emergency-popup-phone">
                    <i class="bi bi-telephone"></i>
                    <a href="tel:${props.phone}">${props.phone}</a>
                </div>
            </div>`;
        }
        
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            html += `<div class="emergency-popup-section">
                <div class="emergency-popup-rating">
                    <span class="emergency-popup-stars">${stars}</span>
                    <span>${props.rating} (${props.rating_count || 0}則評價)</span>
                </div>
            </div>`;
        }
        
        html += `<div class="emergency-popup-section">
                <div class="emergency-popup-badge">
                    🚨 24小時急診服務
                </div>
            </div>`;
        
        html += distance;
        
        html += `<div class="emergency-popup-actions">`;
        if (props.phone) {
            html += `<button onclick="window.open('tel:${props.phone}')" class="emergency-popup-btn primary">
                <i class="bi bi-telephone"></i> 撥打電話
            </button>`;
        }
        if (props.address) {
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(props.address)}`;
            html += `<button onclick="window.open('${mapUrl}', '_blank')" class="emergency-popup-btn secondary">
                <i class="bi bi-navigation"></i> 導航
            </button>`;
        }
        html += `</div></div>`;
        
        return html;
    }
    
    /**
     * 選擇醫院
     */
    selectHospital(hospital, marker) {
        // 重置前一個選中的標記
        if (this.selectedMarker && this.selectedMarker !== marker) {
            const prevIconElement = this.selectedMarker.getElement()?.querySelector('.emergency-marker-icon');
            if (prevIconElement) {
                prevIconElement.style.transform = 'scale(1)';
                prevIconElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)';
            }
        }
        
        // 設置新的選中標記
        this.selectedMarker = marker;
        
        const iconElement = marker.getElement()?.querySelector('.emergency-marker-icon');
        if (iconElement) {
            iconElement.style.transform = 'scale(1.2)';
            iconElement.style.boxShadow = '0 0 20px rgba(220, 53, 69, 0.8)';
        }
        
        // 顯示醫院詳細資訊
        this.showHospitalInfo(hospital);
        
        // 顯示路線按鈕
        const routeBtn = document.getElementById('routeBtn');
        if (routeBtn) {
            routeBtn.style.display = 'flex';
        }
    }
    
    /**
     * 地圖控制
     */
    fitMapBounds() {
        if (this.filteredHospitals.length === 0) return;
        
        try {
            const group = new L.featureGroup();
            
            // 加入用戶位置
            if (this.userLocation) {
                const userMarker = L.marker([this.userLocation.lat, this.userLocation.lng]);
                group.addLayer(userMarker);
            }
            
            // 加入所有醫院位置
            this.filteredHospitals.forEach(hospital => {
                const [lng, lat] = hospital.geometry.coordinates;
                const marker = L.marker([lat, lng]);
                group.addLayer(marker);
            });
            
            this.map.fitBounds(group.getBounds(), {
                padding: [20, 20],
                maxZoom: 16
            });
            
        } catch (error) {
            console.error('調整地圖視角失敗:', error);
        }
    }
    
    async refreshHospitals() {
        this.showNotification('正在重新載入急診醫院...', 'info');
        await this.loadEmergencyHospitals();
        this.showNotification('急診醫院資料已更新', 'success');
    }

    // 24小時急診地圖應用程式 - Part 4: 醫院列表與用戶定位

    /**
     * 更新醫院列表
     */
    updateHospitalList() {
        const hospitalList = document.getElementById('hospitalList');
        const hospitalCount = document.getElementById('hospitalCount');
        
        if (!hospitalList || !hospitalCount) return;
        
        hospitalCount.textContent = this.filteredHospitals.length;
        hospitalList.innerHTML = '';
        
        if (this.filteredHospitals.length === 0) {
            hospitalList.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #666;">
                    <i class="bi bi-hospital" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
                    <p>目前沒有符合條件的急診醫院</p>
                    <p style="font-size: 0.9rem;">請調整篩選條件或擴大搜尋範圍</p>
                </div>
            `;
            return;
        }
        
        this.filteredHospitals.forEach((hospital, index) => {
            const props = hospital.properties;
            const item = this.createHospitalListItem(props, index, hospital);
            hospitalList.appendChild(item);
        });
    }
    
    /**
     * 創建醫院列表項目
     */
    createHospitalListItem(props, index, hospital) {
        const item = document.createElement('div');
        item.className = 'hospital-item';
        item.dataset.hospitalId = props.id;
        
        let distance = '';
        if (this.userLocation) {
            const dist = this.calculateDistance(
                this.userLocation.lat, this.userLocation.lng,
                hospital.geometry.coordinates[1], hospital.geometry.coordinates[0]
            );
            distance = `<div class="hospital-item-distance">📍 ${this.formatDistance(dist)}</div>`;
        }
        
        item.innerHTML = `
            <div class="hospital-item-name">
                <span class="hospital-emergency-badge">24H</span>
                ${props.name || '急診醫院'}
                <span style="color: #999; font-size: 0.8rem; margin-left: auto;">#${index + 1}</span>
            </div>
            <div class="hospital-item-address">
                <i class="bi bi-geo-alt"></i>
                ${props.address || '地址不詳'}
            </div>
            ${distance}
        `;
        
        // 點擊列表項目
        item.addEventListener('click', () => {
            this.selectHospitalFromList(hospital, index);
        });
        
        return item;
    }
    
    /**
     * 從列表選擇醫院
     */
    selectHospitalFromList(hospital, index) {
        // 更新列表選中狀態
        document.querySelectorAll('.hospital-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedItem = document.querySelector(`[data-hospital-id="${hospital.properties.id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
        
        // 移動地圖到該醫院
        const [lng, lat] = hospital.geometry.coordinates;
        this.map.setView([lat, lng], 16);
        
        // 選擇對應的標記
        const allMarkers = [];
        this.markers.eachLayer(marker => allMarkers.push(marker));
        
        if (allMarkers[index]) {
            this.selectHospital(hospital, allMarkers[index]);
            allMarkers[index].openPopup();
        }
        
        // 在手機版本關閉側邊欄
        if (window.innerWidth <= 768 && this.isSidebarOpen) {
            this.toggleSidebar();
        }
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
//                     console.log('✅ 獲取用戶位置成功:', this.userLocation);
                    resolve(this.userLocation);
                },
                (error) => {
//                     console.log('無法獲取用戶位置:', error.message);
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
                
                // 移除舊的用戶位置標記
                if (this.userLocationMarker) {
                    this.map.removeLayer(this.userLocationMarker);
                }
                
                // 添加新的用戶位置標記
                const userIcon = L.divIcon({
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
                });
                
                this.userLocationMarker = L.marker([location.lat, location.lng], { 
                    icon: userIcon 
                }).addTo(this.map);
                
                this.userLocationMarker.bindPopup('<b>您的位置</b>').openPopup();
                
                // 重新篩選並更新顯示
                this.applyClientSideFilters();
                this.displayHospitalMarkers();
                this.updateHospitalList();
                
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
        const R = 6371000; // 地球半徑（公尺）
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
    
    formatDistance(meters) {
        if (meters < 1000) {
            return `${Math.round(meters)}公尺`;
        } else {
            return `${(meters / 1000).toFixed(1)}公里`;
        }
    }

    // 24小時急診地圖應用程式 - Part 5: 路線規劃與UI控制

    /**
     * 路線規劃
     */
    showRouteToSelected() {
        if (!this.selectedHospital || !this.userLocation) {
            this.showNotification('請先定位並選擇一間醫院', 'warning');
            return;
        }
        
        const destination = [
            this.selectedHospital.geometry.coordinates[1],
            this.selectedHospital.geometry.coordinates[0]
        ];
        
        // 移除舊的路線
        if (this.routingControl) {
            this.map.removeControl(this.routingControl);
        }
        
        // 創建新的路線
        this.routingControl = L.Routing.control({
            waypoints: [
                L.latLng(this.userLocation.lat, this.userLocation.lng),
                L.latLng(destination[0], destination[1])
            ],
            routeWhileDragging: false,
            addWaypoints: false,
            createMarker: function() { return null; }, // 不顯示路線標記
            lineOptions: {
                styles: [{ color: '#dc3545', weight: 4, opacity: 0.8 }]
            },
            show: false, // 不顯示路線說明面板
            language: 'zh'
        }).addTo(this.map);
        
        this.routingControl.on('routesfound', (e) => {
            const routes = e.routes;
            const summary = routes[0].summary;
            
            const distance = (summary.totalDistance / 1000).toFixed(1);
            const time = Math.round(summary.totalTime / 60);
            
            this.showNotification(
                `路線規劃完成：${distance}公里，預計 ${time}分鐘`,
                'success',
                5000
            );
        });
        
        this.routingControl.on('routingerror', (e) => {
            console.error('路線規劃失敗:', e);
            this.showNotification('路線規劃失敗，請稍後再試', 'error');
        });
    }
    
    /**
     * UI 控制
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
        
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }
    
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
        
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 100);
    }
    
    handleKeyboardShortcuts(e) {
        if (e.key === 'Escape') {
            if (this.isSidebarOpen && window.innerWidth <= 1024) {
                this.toggleSidebar();
            }
        }
        
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('emergencySearchInput');
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

// 類別結束 - 以下為初始化和輔助程式碼

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
    
    /* Leaflet 彈出視窗樣式覆蓋 */
    .leaflet-popup-content-wrapper {
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        overflow: hidden;
        background: white;
    }
    
    .leaflet-popup-content {
        margin: 0;
        line-height: 1.4;
        font-family: "Noto Sans TC", "標楷體", sans-serif;
    }
    
    /* 確保 Leaflet 路線控制項隱藏 */
    .leaflet-routing-container {
        display: none !important;
    }
    
    /* 自訂標記樣式 */
    .emergency-marker {
        border: none;
        background: transparent;
    }
    
    .emergency-marker-cluster {
        border: none;
        background: transparent;
    }
    
    .user-location-marker {
        border: none;
        background: transparent;
    }
`;

// 添加樣式到頁面
if (!document.getElementById('emergency-map-animations')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'emergency-map-animations';
    styleSheet.textContent = animationStyles;
    document.head.appendChild(styleSheet);
}

// 全域變數
let emergencyMapApp;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
//     console.log('🚨 急診地圖頁面初始化 (Leaflet版本)...');
    
    // 檢查必要的庫是否載入
    if (typeof L === 'undefined') {
        console.error('❌ Leaflet 未載入');
        showErrorMessage('地圖庫載入失敗，請檢查網路連線');
        return;
    }
    
    try {
        emergencyMapApp = new EmergencyMapApp();
        emergencyMapApp.init();
    } catch (error) {
        console.error('❌ 急診地圖初始化失敗:', error);
        showErrorMessage('急診地圖初始化失敗，請重新整理頁面');
    }
});

// 顯示錯誤訊息的輔助函數
function showErrorMessage(message) {
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
            ">
                <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545; margin-bottom: 1rem;"></i>
                <h3>急診地圖載入失敗</h3>
                <p>${message}</p>
                <button onclick="location.reload()" class="btn btn-danger" style="margin-top: 1rem;">
                    <i class="bi bi-arrow-clockwise me-1"></i>重新載入
                </button>
            </div>
        `;
    }
}

// 清理資源
window.addEventListener('beforeunload', function() {
    if (emergencyMapApp && emergencyMapApp.map) {
        emergencyMapApp.map.remove();
//         console.log('🧹 清理急診地圖資源');
    }
});

// 錯誤處理
window.addEventListener('error', function(e) {
    console.error('JavaScript 錯誤:', e.error);
});

// 導出給其他腳本使用
window.EmergencyMapApp = EmergencyMapApp;

// 檢查 Leaflet 相關插件載入狀態
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        // 檢查必要的插件
        const requiredPlugins = [
            { name: 'Leaflet', check: () => typeof L !== 'undefined' },
            { name: 'MarkerCluster', check: () => typeof L.markerClusterGroup !== 'undefined' },
            { name: 'Routing', check: () => typeof L.Routing !== 'undefined' }
        ];
        
        const missingPlugins = requiredPlugins.filter(plugin => !plugin.check());
        
        if (missingPlugins.length > 0) {
            console.warn('⚠️ 缺少插件:', missingPlugins.map(p => p.name).join(', '));
            console.warn('某些功能可能無法正常運作');
        } else {
//             console.log('✅ 所有必要插件已載入');
        }
    }, 1000);
});