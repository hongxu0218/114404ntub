// map.js - 寵物地圖功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('地圖腳本開始初始化...');
    
    // 全域變數
    let map;
    let markers = L.markerClusterGroup();
    let allLocations = [];
    let currentFilters = {
        type: null,
        city: null,
        search: null,
        petTypes: []
    };
    
    // 地圖圖標配置
    const LOCATION_ICONS = {
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
    };
    
    const PET_TYPE_ICONS = {
        small_dog: '🐕‍',
        medium_dog: '🐕',
        large_dog: '🦮',
        cat: '🐈',
        bird: '🦜',
        rodent: '🐹',
        reptile: '🦎',
        other: '🦝'
    };
    
    // 初始化地圖
    function initMap() {
        console.log('🗺️ 初始化地圖...');
        
        // 創建地圖 - 預設中心點為台北
        map = L.map('pet-map').setView([25.0330, 121.5654], 13);
        console.log('✅ 地圖物件創建完成');
        
        // 添加地圖圖層
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        console.log('✅ 地圖圖層添加完成');
        
        // 創建標記群組
        markers = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 50
        });
        console.log('✅ 標記群組創建完成');
        
        // 添加標記群組到地圖
        map.addLayer(markers);
        console.log('✅ 標記群組添加到地圖');
        
        // 設置地圖控制項
        setupMapControls();
        
        console.log('🎉 地圖初始化完成');
    }
    
    // 設置地圖控制項
    function setupMapControls() {
        // 定位按鈕
        document.getElementById('locate-btn').addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    map.setView([lat, lng], 15);
                    
                    // 添加使用者位置標記
                    const userMarker = L.marker([lat, lng], {
                        icon: L.divIcon({
                            html: '<div style="background: #007cff; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;">📍</div>',
                            className: 'user-location-marker'
                        })
                    }).addTo(map);
                    
                    userMarker.bindPopup('<b>您的位置</b>').openPopup();
                }, function() {
                    alert('無法取得您的位置');
                });
            } else {
                alert('您的瀏覽器不支援定位功能');
            }
        });
        
        // 全螢幕按鈕
        document.getElementById('fullscreen-btn').addEventListener('click', function() {
            const mapContainer = document.querySelector('.pet-map-container');
            if (!document.fullscreenElement) {
                mapContainer.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        });
    }
    
    // 載入地點資料
    async function loadLocations() {
        console.log('載入地點資料...');
        console.log('當前篩選條件:', currentFilters);
        
        try {
            // 構建查詢參數
            const params = new URLSearchParams();
            
            if (currentFilters.type) {
                params.append('type', currentFilters.type);
                console.log('添加服務類型篩選:', currentFilters.type);
            }
            if (currentFilters.city) {
                params.append('city', currentFilters.city);
                console.log('添加城市篩選:', currentFilters.city);
            }
            if (currentFilters.search) {
                params.append('search', currentFilters.search);
                console.log('添加搜尋篩選:', currentFilters.search);
            }
            
            // 添加寵物類型篩選
            currentFilters.petTypes.forEach(petType => {
                params.append(`support_${petType}`, 'true');
                console.log('添加寵物類型篩選:', petType);
            });
            
            const url = `/api/locations/?${params.toString()}`;
            console.log('API 請求 URL:', url);
            
            const response = await fetch(url);
            console.log('API 回應狀態:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API 錯誤回應:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, response: ${errorText}`);
            }
            
            const data = await response.json();
            console.log('API 回應資料:', data);
            console.log('載入了', data.features ? data.features.length : 0, '個地點');
            
            if (data.features) {
                allLocations = data.features;
                displayMarkers(allLocations);
            } else {
                console.error('API 回應格式錯誤，沒有 features 屬性');
                allLocations = [];
                displayMarkers([]);
            }
            
        } catch (error) {
            console.error('載入地點資料失敗:', error);
            alert('載入地點資料失敗，請稍後再試。詳細錯誤請查看 Console。');
            
            // 顯示空的結果
            allLocations = [];
            displayMarkers([]);
        }
    }
    
    // 顯示標記
    function displayMarkers(locations) {
        console.log('🎯 displayMarkers 被呼叫');
        console.log('傳入的 locations 數量:', locations ? locations.length : 'null/undefined');
        console.log('locations 資料:', locations);
        
        // 清除現有標記
        markers.clearLayers();
        console.log('✅ 已清除現有標記');
        
        if (!locations || !Array.isArray(locations)) {
            console.error('❌ locations 不是有效的陣列');
            return;
        }
        
        if (locations.length === 0) {
            console.log('⚠️ 沒有地點資料要顯示');
            return;
        }
        
        console.log('🔄 開始處理', locations.length, '個地點...');
        
        let successCount = 0;
        let errorCount = 0;
        
        locations.forEach((location, index) => {
            try {
                if (!location.geometry || !location.geometry.coordinates) {
                    console.error(`❌ 地點 ${index} 沒有座標資料:`, location);
                    errorCount++;
                    return;
                }
                
                const { coordinates } = location.geometry;
                const props = location.properties;
                
                if (!coordinates || coordinates.length < 2) {
                    console.error(`❌ 地點 ${index} 座標格式錯誤:`, coordinates);
                    errorCount++;
                    return;
                }
                
                console.log(`📍 處理地點 ${index + 1}/${locations.length}: ${props.name} (${coordinates[1]}, ${coordinates[0]})`);
                
                // 決定圖標
                let icon = LOCATION_ICONS.default;
                if (props.service_types && props.service_types.length > 0) {
                    const serviceType = props.service_types[0];
                    if (serviceType.includes('醫療') || serviceType.includes('醫院')) {
                        icon = LOCATION_ICONS.hospital;
                    } else if (serviceType.includes('美容')) {
                        icon = LOCATION_ICONS.cosmetic;
                    } else if (serviceType.includes('公園')) {
                        icon = LOCATION_ICONS.park;
                    } else if (serviceType.includes('用品')) {
                        icon = LOCATION_ICONS.product;
                    } else if (serviceType.includes('收容')) {
                        icon = LOCATION_ICONS.shelter;
                    } else if (serviceType.includes('殯葬')) {
                        icon = LOCATION_ICONS.funeral;
                    } else if (serviceType.includes('寄宿')) {
                        icon = LOCATION_ICONS.boarding;
                    }
                }
                
                // 創建自定義標記
                const customIcon = L.divIcon({
                    html: `<div style="
                        background: #FFA726;
                        color: white;
                        border-radius: 50%;
                        width: 35px;
                        height: 35px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 3px solid white;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                        font-size: 16px;
                    ">${icon}</div>`,
                    className: 'custom-marker',
                    iconSize: [35, 35],
                    iconAnchor: [17, 17]
                });
                
                // 創建標記
                const marker = L.marker([coordinates[1], coordinates[0]], { icon: customIcon });
                
                // 創建彈出視窗內容
                const popupContent = createPopupContent(props);
                marker.bindPopup(popupContent, { maxWidth: 300 });
                
                // 添加到標記群組
                markers.addLayer(marker);
                successCount++;
                
                console.log(`✅ 成功添加標記: ${props.name}`);
                
            } catch (error) {
                console.error(`❌ 處理地點 ${index} 時發生錯誤:`, error, location);
                errorCount++;
            }
        });
        
        console.log(`📊 標記處理完成: 成功 ${successCount} 個, 失敗 ${errorCount} 個`);
        
        // 如果有地點，調整地圖視角到包含所有標記
        if (successCount > 0) {
            try {
                const bounds = markers.getBounds();
                if (bounds.isValid()) {
                    console.log('🗺️ 調整地圖視角以包含所有標記');
                    map.fitBounds(bounds, { padding: [20, 20] });
                } else {
                    console.log('⚠️ 標記邊界無效，保持當前視角');
                }
            } catch (error) {
                console.error('❌ 調整地圖視角時發生錯誤:', error);
            }
        } else {
            console.log('❌ 沒有成功添加任何標記');
        }
    }
    
    // 創建彈出視窗內容
    function createPopupContent(props) {
        let html = `
            <div class="popup-content">
                <h3>${props.name || '未命名地點'}</h3>
        `;
        
        // 地址
        if (props.address) {
            html += `<div class="popup-address">📍 ${props.address}</div>`;
        }
        
        // 評分
        if (props.rating) {
            const stars = '⭐'.repeat(Math.round(props.rating));
            html += `<div class="popup-rating">
                <span class="stars">${stars}</span>
                <span>${props.rating} (${props.rating_count || 0}則評價)</span>
            </div>`;
        }
        
        // 服務類型
        if (props.service_types && props.service_types.length > 0) {
            html += `<div class="popup-services">`;
            props.service_types.forEach(service => {
                html += `<span class="popup-service-tag">${service}</span>`;
            });
            html += `</div>`;
        }
        
        // 支援的寵物類型
        if (props.supported_pet_types && props.supported_pet_types.length > 0) {
            html += `<div class="popup-pet-types">
                <strong>支援寵物：</strong>
                <div class="popup-pet-tags">`;
            
            props.supported_pet_types.forEach(petType => {
                // 找到對應的圖標
                let petIcon = '🐾';
                let tagClass = 'pet-type-tag';
                
                // 如果是推測的寵物類型，使用不同樣式
                if (petType.includes('通常接受') || petType.includes('未明確設定')) {
                    petIcon = '❓';
                    tagClass = 'pet-type-tag uncertain';
                } else {
                    for (const [code, icon] of Object.entries(PET_TYPE_ICONS)) {
                        if (petType.includes('小型犬') && code === 'small_dog') petIcon = icon;
                        else if (petType.includes('中型犬') && code === 'medium_dog') petIcon = icon;
                        else if (petType.includes('大型犬') && code === 'large_dog') petIcon = icon;
                        else if (petType.includes('貓') && code === 'cat') petIcon = icon;
                        else if (petType.includes('鳥') && code === 'bird') petIcon = icon;
                        else if (petType.includes('鼠') && code === 'rodent') petIcon = icon;
                        else if (petType.includes('爬蟲') && code === 'reptile') petIcon = icon;
                    }
                }
                html += `<span class="${tagClass}">${petIcon} ${petType}</span>`;
            });
            html += `</div></div>`;
        } else if (currentFilters.petTypes.length > 0) {
            // 如果用戶有篩選寵物類型但地點沒有明確設定，顯示提示
            html += `<div class="popup-pet-types">
                <div class="popup-pet-tags">
                    <span class="pet-type-tag uncertain">❓ 未明確標示寵物類型限制</span>
                </div>
            </div>`;
        }
        
        // 24小時急診標示
        if (props.has_emergency) {
            html += `<div style="color: #e74c3c; font-weight: bold;">🚨 24小時急診</div>`;
        }
        
        // 聯絡資訊
        if (props.phone) {
            html += `<div>📞 <a href="tel:${props.phone}">${props.phone}</a></div>`;
        }
        
        // 操作按鈕
        html += `<div class="popup-actions">`;
        if (props.phone) {
            html += `<a href="tel:${props.phone}" class="popup-btn">📞 撥打電話</a>`;
        }
        if (props.address) {
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(props.address)}`;
            html += `<a href="${mapUrl}" target="_blank" class="popup-btn primary">🗺️ 導航</a>`;
        }
        html += `</div>`;
        
        html += `</div>`;
        return html;
    }
    
    // 設置篩選器事件監聽
    function setupFilters() {
        console.log('設置篩選器...');
        
        // 服務類型篩選
        const categoryItems = document.querySelectorAll('.category-item');
        categoryItems.forEach(item => {
            item.addEventListener('click', function() {
                const type = this.dataset.type;
                
                console.log('點擊服務類型:', type); // 除錯用
                
                // 檢查是否為暫時沒有資料的服務類型
                const unavailableTypes = ['live', 'restaurant'];
                if (unavailableTypes.includes(type)) {
                    alert('此服務類型的資料即將上線，敬請期待！');
                    return;
                }
                
                // 切換選中狀態
                categoryItems.forEach(i => i.classList.remove('active'));
                
                if (currentFilters.type === type) {
                    // 如果點擊同一個，則取消選擇
                    currentFilters.type = null;
                    console.log('取消選擇服務類型');
                } else {
                    // 選擇新的類型
                    currentFilters.type = type;
                    this.classList.add('active');
                    console.log('選擇服務類型:', type);
                }
                
                updateFilters();
            });
        });
        
        // 寵物類型篩選
        const petTypeFilters = document.querySelectorAll('.pet-type-filter');
        petTypeFilters.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const petType = this.dataset.petType;
                
                if (this.checked) {
                    if (!currentFilters.petTypes.includes(petType)) {
                        currentFilters.petTypes.push(petType);
                    }
                } else {
                    currentFilters.petTypes = currentFilters.petTypes.filter(type => type !== petType);
                }
                
                updateFilters();
            });
        });
        
        // 搜尋功能
        const searchInput = document.getElementById('map-search-input');
        const searchBtn = document.getElementById('map-search-btn');
        
        function performSearch() {
            const searchText = searchInput.value.trim();
            currentFilters.search = searchText || null;
            updateFilters();
        }
        
        searchBtn.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        // 清除所有篩選
        document.getElementById('clear-filters').addEventListener('click', function() {
            // 重置篩選條件
            currentFilters = {
                type: null,
                city: null,
                search: null,
                petTypes: []
            };
            
            // 重置 UI
            categoryItems.forEach(item => item.classList.remove('active'));
            petTypeFilters.forEach(checkbox => checkbox.checked = false);
            searchInput.value = '';
            
            // 更新篩選
            updateFilters();
        });
    }
    
    // 更新篩選並重新載入資料
    function updateFilters() {
        console.log('更新篩選條件:', currentFilters);
        updateFilterDisplay();
        loadLocations();
    }
    
    // 更新篩選狀態顯示
    function updateFilterDisplay() {
        const activeFiltersDiv = document.getElementById('active-filters');
        const filterTagsDiv = document.getElementById('filter-tags');
        
        // 清空現有標籤
        filterTagsDiv.innerHTML = '';
        
        let hasActiveFilters = false;
        
        // 顯示服務類型篩選
        if (currentFilters.type) {
            const typeNames = {
                'hospital': '醫院',
                'cosmetic': '美容',
                'park': '公園',
                'product': '寵物用品',
                'shelter': '收容所',
                'funeral': '寵物殯葬',
                'boarding': '寄宿'
                // 移除不存在的 'live' 和 'restaurant'
            };
            
            const tag = document.createElement('span');
            tag.className = 'filter-tag';
            tag.innerHTML = `${typeNames[currentFilters.type] || currentFilters.type} <span class="remove-tag" data-type="service">×</span>`;
            filterTagsDiv.appendChild(tag);
            hasActiveFilters = true;
        }
        
        // 顯示寵物類型篩選
        currentFilters.petTypes.forEach(petType => {
            const petTypeNames = {
                'small_dog': '小型犬',
                'medium_dog': '中型犬',
                'large_dog': '大型犬',
                'cat': '貓',
                'bird': '鳥類',
                'rodent': '齧齒動物',
                'reptile': '爬蟲類',
                'other': '其他'
            };
            
            const tag = document.createElement('span');
            tag.className = 'filter-tag';
            tag.innerHTML = `${petTypeNames[petType] || petType} <span class="remove-tag" data-type="pet" data-value="${petType}">×</span>`;
            filterTagsDiv.appendChild(tag);
            hasActiveFilters = true;
        });
        
        // 顯示搜尋篩選
        if (currentFilters.search) {
            const tag = document.createElement('span');
            tag.className = 'filter-tag';
            tag.innerHTML = `搜尋: ${currentFilters.search} <span class="remove-tag" data-type="search">×</span>`;
            filterTagsDiv.appendChild(tag);
            hasActiveFilters = true;
        }
        
        // 顯示/隱藏篩選狀態區域
        activeFiltersDiv.style.display = hasActiveFilters ? 'flex' : 'none';
        
        // 設置移除標籤的事件監聽
        filterTagsDiv.querySelectorAll('.remove-tag').forEach(removeBtn => {
            removeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const type = this.dataset.type;
                const value = this.dataset.value;
                
                if (type === 'service') {
                    currentFilters.type = null;
                    document.querySelectorAll('.category-item').forEach(item => item.classList.remove('active'));
                } else if (type === 'pet') {
                    currentFilters.petTypes = currentFilters.petTypes.filter(pt => pt !== value);
                    const checkbox = document.querySelector(`[data-pet-type="${value}"]`);
                    if (checkbox) checkbox.checked = false;
                } else if (type === 'search') {
                    currentFilters.search = null;
                    document.getElementById('map-search-input').value = '';
                }
                
                updateFilters();
            });
        });
    }
    
    // 主初始化函數
    function init() {
        console.log('開始初始化地圖應用...');
        
        // 初始化地圖
        initMap();
        
        // 設置篩選器
        setupFilters();
        
        // 載入初始資料
        loadLocations();
        
        console.log('地圖應用初始化完成');
    }
    
    // 啟動應用
    init();
});

// 錯誤處理
window.addEventListener('error', function(e) {
    console.error('JavaScript 錯誤:', e.error);
});

// 未處理的 Promise 拒絕
window.addEventListener('unhandledrejection', function(e) {
    console.error('未處理的 Promise 拒絕:', e.reason);
});

console.log('地圖腳本載入完成');