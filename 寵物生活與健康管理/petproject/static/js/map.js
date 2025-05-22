// 全域變數
let map;
let markersCluster;
let allLocations = [];
let filteredLocations = [];
let userLocation = null;
let selectedType = '';
let selectedPetTypes = []; 

// 地點類型對應的圖標
const TYPE_ICONS = {
    'hospital': '🏥',
    'cosmetic': '✂️',
    'park': '🌳',
    'product': '🛍️',
    'shelter': '🐾',
    'funeral': '⚱️',
    'live': '🏨',
    'restaurant': '🍽️',
    'boarding': '🏠'
};

// 地點類型顏色
const TYPE_COLORS = {
    'hospital': '#dc3545',
    'cosmetic': '#fd7e14',
    'park': '#28a745',
    'product': '#007bff',
    'shelter': '#e83e8c',
    'funeral': '#495057',
    'live': '#20c997',
    'restaurant': '#ffc107',
    'boarding': '#6f42c1'
};

// 寵物類型對應的圖標
const PET_TYPE_ICONS = {
    'support_small_dog': '🐕‍',
    'support_medium_dog': '🐕',
    'support_large_dog': '🦮',
    'support_cat': '🐈',
    'support_bird': '🦜',
    'support_rodent': '🐹',
    'support_reptile': '🦎',
    'support_other': '🦝'
};

// 初始化地圖
function initializeMap() {
    const taipeiCenter = [25.0330, 121.5654];
    
    map = L.map('pet-map', {
        center: taipeiCenter,
        zoom: 14,
        zoomControl: false,
        attributionControl: true
    });
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    
    markersCluster = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 50,
        iconCreateFunction: function(cluster) {
            const count = cluster.getChildCount();
            return L.divIcon({
                html: `<div class="marker-cluster">${count}</div>`,
                className: 'custom-cluster',
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            });
        }
    });
    
    map.addLayer(markersCluster);
    loadPetLocations();
    setupEventListeners();
}

// 創建自定義標記
function createCustomIcon(type) {
    const icon = TYPE_ICONS[type] || '📍';
    const color = TYPE_COLORS[type] || '#ff385c';
    
    return L.divIcon({
        className: 'custom-marker',
        html: `<div class="marker-pin" style="background-color: ${color}; border: 2px solid white;">${icon}</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
    });
}

// 載入地點資料
async function loadPetLocations() {
    let queryParams = new URLSearchParams();
    
    if (selectedType) {
        queryParams.append('type', selectedType);
    }
    
    selectedPetTypes.forEach(petType => {
        queryParams.append(petType, 'true');
    });

    try {
        console.log('載入地點資料:', queryParams.toString());
        const response = await fetch(`/api/locations/?${queryParams.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        markersCluster.clearLayers();
        
        if (data.type === 'FeatureCollection' && data.features) {
            allLocations = data.features.map(feature => ({
                id: feature.properties.id,
                name: feature.properties.name,
                type: getLocationType(feature.properties),
                address: feature.properties.address,
                lat: feature.geometry && feature.geometry.coordinates ? feature.geometry.coordinates[1] : null,
                lng: feature.geometry && feature.geometry.coordinates ? feature.geometry.coordinates[0] : null,
                rating: feature.properties.rating,
                phone: feature.properties.phone,
                support_small_dog: feature.properties.support_small_dog,
                support_medium_dog: feature.properties.support_medium_dog,
                support_large_dog: feature.properties.support_large_dog,
                support_cat: feature.properties.support_cat,
                support_bird: feature.properties.support_bird,
                support_rodent: feature.properties.support_rodent,
                support_reptile: feature.properties.support_reptile,
                support_other: feature.properties.support_other,
                supported_pet_types: feature.properties.supported_pet_types,
                business_hours: feature.properties.business_hours,
                type_display: feature.properties.type_display,
                website: feature.properties.website,
                is_hospital: feature.properties.is_hospital,
                is_cosmetic: feature.properties.is_cosmetic,
                is_park: feature.properties.is_park,
                is_product: feature.properties.is_product,
                is_shelter: feature.properties.is_shelter,
                is_funeral: feature.properties.is_funeral,
                is_live: feature.properties.is_live,
                is_boarding: feature.properties.is_boarding
            }));
            
            console.log(`載入了 ${allLocations.length} 個地點`);
        }
        
        // 篩選並顯示地點
        filterLocations();
        updateFilterDisplay();
        
    } catch (error) {
        console.error('載入地點資料錯誤:', error);
        showAlert('無法載入地點資料: ' + error.message, 'error');
    }
}

// 根據屬性確定地點類型 - 處理 0/1 格式
function getLocationType(properties) {
    if (properties.is_hospital === 1) return 'hospital';
    if (properties.is_cosmetic === 1) return 'cosmetic';
    if (properties.is_park === 1) return 'park';
    if (properties.is_product === 1) return 'product';
    if (properties.is_shelter === 1) return 'shelter';
    if (properties.is_funeral === 1) return 'funeral';
    if (properties.is_live === 1) return 'live';
    if (properties.is_boarding === 1) return 'boarding';
    return 'other';
}

// 篩選地點
function filterLocations() {
    const searchText = document.getElementById('map-search-input').value.trim().toLowerCase();
    
    filteredLocations = allLocations.filter(location => {
        // 類型篩選
        if (selectedType && selectedType !== '') {
            if (selectedType === 'restaurant') {
                const isRestaurant = 
                    (location.name && location.name.includes('餐廳')) || 
                    (location.address && location.address.includes('餐廳'));
                if (!isRestaurant) return false;
            } 
            else if (selectedType === 'adoption') {
                if (!location.is_shelter) return false;
            }
            else {
                const propertyName = `is_${selectedType}`;
                if (!location[propertyName]) return false;
            }
        }
        
        // 寵物類型篩選
        if (selectedPetTypes.length > 0) {
            let matchesAnyPetType = false;
            
            for (const petType of selectedPetTypes) {
                if (location[petType] && location[petType] !== 0) {
                    matchesAnyPetType = true;
                    break;
                }
            }
            
            if (!matchesAnyPetType) {
                const assumedSupport = [];
                if (location.is_hospital || location.is_cosmetic || location.is_live || location.is_boarding) {
                    assumedSupport.push('support_small_dog', 'support_medium_dog', 'support_large_dog', 'support_cat');
                }
                if (location.is_park) {
                    assumedSupport.push('support_small_dog', 'support_medium_dog', 'support_large_dog');
                }
                if (location.is_product) {
                    assumedSupport.push('support_small_dog', 'support_medium_dog', 'support_large_dog', 'support_cat', 'support_bird', 'support_rodent', 'support_reptile', 'support_other');
                }
                
                for (const petType of selectedPetTypes) {
                    if (assumedSupport.includes(petType)) {
                        matchesAnyPetType = true;
                        break;
                    }
                }
            }
            
            if (!matchesAnyPetType) return false;
        }
        
        // 搜尋文字篩選
        if (searchText) {
            const nameMatch = location.name && location.name.toLowerCase().includes(searchText);
            const addressMatch = location.address && location.address.toLowerCase().includes(searchText);
            const petTypeMatch = location.supported_pet_types && 
                      location.supported_pet_types.some(type => 
                          type.toLowerCase().includes(searchText));
            
            if (!(nameMatch || addressMatch || petTypeMatch)) {
                return false;
            }
        }
        
        return true;
    });
    
    console.log(`篩選後剩餘 ${filteredLocations.length} 個地點`);
    displayMarkers();
}

// 顯示標記 - 簡化版本，只顯示有座標的地點
function displayMarkers() {
    markersCluster.clearLayers();
    
    // 只處理有座標的地點
    const locationsWithCoords = filteredLocations.filter(loc => 
        loc.lat && loc.lng && loc.lat !== null && loc.lng !== null
    );
    
    const locationsWithoutCoords = filteredLocations.length - locationsWithCoords.length;
    
    console.log(`顯示標記: ${locationsWithCoords.length} 個有座標的地點`);
    if (locationsWithoutCoords > 0) {
        console.log(`跳過 ${locationsWithoutCoords} 個沒有座標的地點`);
    }
    
    // 添加有座標的標記到地圖
    locationsWithCoords.forEach(location => {
        const marker = L.marker([location.lat, location.lng], {
            icon: createCustomIcon(location.type)
        });
        
        marker.bindPopup(createPopupContent(location));
        markersCluster.addLayer(marker);
    });
    
    // 調整視圖
    if (markersCluster.getLayers().length > 0) {
        try {
            map.fitBounds(markersCluster.getBounds(), {
                padding: [50, 50],
                maxZoom: 16
            });
        } catch (error) {
            console.warn('無法調整地圖視圖:', error);
        }
    } else if (filteredLocations.length === 0) {
        showAlert('沒有找到符合條件的地點', 'info');
    } else if (locationsWithoutCoords > 0) {
        showAlert(`找到 ${filteredLocations.length} 個地點，但其中 ${locationsWithoutCoords} 個沒有座標資訊`, 'warning');
    }
}

// 創建彈出視窗內容
function createPopupContent(location) {
    const stars = location.rating ? 
        '★'.repeat(Math.floor(location.rating)) + '☆'.repeat(5 - Math.floor(location.rating)) : '';
    
    // 顯示支援的寵物類型
    let petTypesHtml = '';
    if (location.supported_pet_types && location.supported_pet_types.length > 0) {
        let petTypeTags = location.supported_pet_types.map(type => {
            let iconKey = Object.keys(PET_TYPE_ICONS).find(key => 
                key.includes(type.toLowerCase().replace(/[^a-z0-9]/g, '_')) || 
                type.toLowerCase().includes(key.replace('support_', ''))
            );
            let icon = iconKey ? PET_TYPE_ICONS[iconKey] : '';
            
            return `<span class="pet-type-tag">${icon} ${type}</span>`;
        });
        
        petTypesHtml = `
            <div class="popup-pet-types">
                <strong>適合寵物：</strong>
                <div class="popup-pet-tags">${petTypeTags.join('')}</div>
            </div>
        `;
    }
    
    // 營業時間
    let businessHoursHtml = '';
    if (location.business_hours) {
        try {
            let hours;
            if (typeof location.business_hours === 'string') {
                hours = JSON.parse(location.business_hours);
            } else {
                hours = location.business_hours;
            }
            
            const today = new Date().getDay();
            const weekdays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
            const todayKey = weekdays[today];
            const todayHours = hours[todayKey] || '未提供';
            
            businessHoursHtml = `
                <div class="popup-hours">
                    <div><strong>今日營業：</strong> ${todayHours}</div>
                </div>
            `;
        } catch (error) {
            console.warn('無法解析營業時間:', error);
        }
    }
    
    // 服務標籤
    let servicesHtml = '';
    if (location.type_display && location.type_display.length > 0) {
        servicesHtml = `
            <div class="popup-services">
                ${Array.isArray(location.type_display) ? 
                  location.type_display.map(service => 
                    `<span class="popup-service-tag">${service}</span>`
                  ).join('') : 
                  `<span class="popup-service-tag">${location.type_display}</span>`
                }
            </div>
        `;
    }
    
    // 只顯示 address，不包含 city 和 district
    const displayAddress = location.address || '';
    
    return `
        <div class="popup-content">
            <h3>${location.name}</h3>
            ${displayAddress ? `<div class="popup-address">${displayAddress}</div>` : ''}
            ${location.rating ? `
            <div class="popup-rating">
                <span class="stars">${stars}</span>
                <span>${location.rating}</span>
            </div>
            ` : ''}
            ${servicesHtml}
            ${petTypesHtml}
            ${businessHoursHtml}
            <div class="popup-actions">
                ${location.phone ? `<a href="tel:${location.phone}" class="popup-btn">📞 撥打電話</a>` : ''}
                ${location.lat && location.lng ? 
                  `<a href="https://www.google.com/maps/dir/?api=1&destination=${location.lat},${location.lng}" 
                    class="popup-btn primary" target="_blank">🧭 導航前往</a>` : ''}
                ${location.website ? 
                  `<a href="${location.website}" class="popup-btn" target="_blank">🌐 官方網站</a>` : ''}
            </div>
        </div>
    `;
}

// 更新篩選顯示
function updateFilterDisplay() {
    const filterTagsContainer = document.getElementById('filter-tags');
    const activeFiltersContainer = document.getElementById('active-filters');
    
    if (!filterTagsContainer || !activeFiltersContainer) return;
    
    filterTagsContainer.innerHTML = '';
    let hasActiveFilters = false;
    
    selectedPetTypes.forEach(petType => {
        hasActiveFilters = true;
        const petTypeSelector = document.querySelector(`.pet-type-filter[data-pet-type="${petType}"]`);
        if (petTypeSelector) {
            const petTypeName = petTypeSelector.parentNode.querySelector('span').textContent;
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `${petTypeName} <span class="remove-tag" data-type="pet" data-value="${petType}">×</span>`;
            filterTagsContainer.appendChild(tag);
        }
    });
    
    if (selectedType) {
        hasActiveFilters = true;
        const typeSelector = document.querySelector(`.category-item[data-type="${selectedType}"]`);
        if (typeSelector) {
            const typeName = typeSelector.querySelector('.category-name').textContent;
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `${typeName} <span class="remove-tag" data-type="location" data-value="${selectedType}">×</span>`;
            filterTagsContainer.appendChild(tag);
        }
    }
    
    if (hasActiveFilters) {
        activeFiltersContainer.style.display = 'flex';
    } else {
        activeFiltersContainer.style.display = 'none';
    }
    
    document.querySelectorAll('.remove-tag').forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            const value = this.getAttribute('data-value');
            
            if (type === 'pet') {
                const checkbox = document.querySelector(`.pet-type-filter[data-pet-type="${value}"]`);
                if (checkbox) {
                    checkbox.checked = false;
                }
                selectedPetTypes = selectedPetTypes.filter(t => t !== value);
            } else if (type === 'location') {
                document.querySelectorAll('.category-item').forEach(i => {
                    i.classList.remove('active');
                });
                selectedType = '';
            }
            
            loadPetLocations();
        });
    });
}

// 獲取用戶位置
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                L.marker([userLocation.lat, userLocation.lng], {
                    icon: L.divIcon({
                        className: 'custom-marker',
                        html: '<div class="marker-pin" style="background-color: #1976D2;">📍</div>',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    })
                })
                .addTo(map)
                .bindPopup('您的位置')
                .openPopup();
                
                map.setView([userLocation.lat, userLocation.lng], 15);
            },
            error => {
                console.error('無法獲取位置:', error);
                showAlert('無法獲取您的位置', 'warning');
            }
        );
    } else {
        showAlert('您的瀏覽器不支援地理位置功能', 'warning');
    }
}

// 全螢幕切換
function toggleFullscreen() {
    const mapContainer = document.querySelector('.map-container');
    
    if (!document.fullscreenElement) {
        if (mapContainer.requestFullscreen) {
            mapContainer.requestFullscreen();
        } else if (mapContainer.mozRequestFullScreen) {
            mapContainer.mozRequestFullScreen();
        } else if (mapContainer.webkitRequestFullscreen) {
            mapContainer.webkitRequestFullscreen();
        } else if (mapContainer.msRequestFullscreen) {
            mapContainer.msRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

// 顯示提示訊息
function showAlert(message, type = 'info') {
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type}`;
    alertElement.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 10px 20px;
        border-radius: 8px;
        z-index: 2000;
        background-color: ${type === 'error' ? '#f8d7da' : type === 'warning' ? '#fff3cd' : type === 'success' ? '#d4edda' : '#d1ecf1'};
        color: ${type === 'error' ? '#721c24' : type === 'warning' ? '#856404' : type === 'success' ? '#155724' : '#0c5460'};
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        max-width: 400px;
        word-wrap: break-word;
        font-size: 14px;
        line-height: 1.4;
    `;
    
    alertElement.textContent = message;
    document.body.appendChild(alertElement);
    
    setTimeout(() => {
        alertElement.style.opacity = '0';
        alertElement.style.transition = 'opacity 0.5s';
        setTimeout(() => {
            if (document.body.contains(alertElement)) {
                document.body.removeChild(alertElement);
            }
        }, 500);
    }, 3000);
}

// 設置事件監聽器
function setupEventListeners() {
    document.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            
            document.querySelectorAll('.category-item').forEach(i => {
                i.classList.remove('active');
            });
            
            if (selectedType === type) {
                selectedType = '';
            } else {
                this.classList.add('active');
                selectedType = type;
            }
            
            console.log('選擇類型:', selectedType);
            loadPetLocations();
        });
    });
    
    const searchBtn = document.getElementById('map-search-btn');
    const searchInput = document.getElementById('map-search-input');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            filterLocations();
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                filterLocations();
            }
        });
    }
    
    document.querySelectorAll('.pet-type-filter').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const petType = this.getAttribute('data-pet-type');
            
            if (this.checked) {
                if (!selectedPetTypes.includes(petType)) {
                    selectedPetTypes.push(petType);
                }
            } else {
                selectedPetTypes = selectedPetTypes.filter(type => type !== petType);
            }
            
            console.log('選擇寵物類型:', selectedPetTypes);
            loadPetLocations();
        });
    });
    
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            selectedPetTypes = [];
            document.querySelectorAll('.pet-type-filter').forEach(checkbox => {
                checkbox.checked = false;
            });
            
            selectedType = '';
            document.querySelectorAll('.category-item').forEach(i => {
                i.classList.remove('active');
            });
            
            if (searchInput) {
                searchInput.value = '';
            }
            loadPetLocations();
        });
    }
    
    const locateBtn = document.getElementById('locate-btn');
    if (locateBtn) {
        locateBtn.addEventListener('click', function() {
            getUserLocation();
        });
    }
    
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', function() {
            toggleFullscreen();
        });
    }
    
    document.addEventListener('fullscreenchange', function() {
        if (map) {
            setTimeout(() => {
                map.invalidateSize();
            }, 100);
        }
    });
    
    window.addEventListener('resize', function() {
        if (map) {
            setTimeout(() => {
                map.invalidateSize();
            }, 100);
        }
    });
}

// 頁面載入完成後初始化地圖
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing map...');
    initializeMap();
});