// 毛日好社群 - 現代化 JavaScript 功能
// =============================================

class SocialApp {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.initializeComponents();
    }

    init() {
        console.log('🚀 毛日好社群正在啟動...');
        this.addLoadingStyles();
    }

    // 添加載入動畫樣式
    addLoadingStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255,255,255,.3);
                border-radius: 50%;
                border-top-color: #fff;
                animation: spin 1s ease-in-out infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .fade-in {
                animation: fadeIn 0.5s ease-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .bounce {
                animation: bounce 0.3s ease;
            }

            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                60% { transform: translateY(-5px); }
            }

            .shake {
                animation: shake 0.5s;
            }

            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
        `;
        document.head.appendChild(style);
    }

    // 設置事件監聽器
    setupEventListeners() {
        // 貼文互動
        document.addEventListener('click', this.handleClick.bind(this));

        // 表單提交
        document.addEventListener('submit', this.handleSubmit.bind(this));

        // 滾動載入更多
        window.addEventListener('scroll', this.handleScroll.bind(this));

        // 鍵盤快捷鍵
        document.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    // 點擊事件處理
    handleClick(e) {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const postId = target.closest('[data-post-id]')?.dataset.postId;

        switch (action) {
            case 'like':
                this.toggleLike(postId, target);
                break;
            case 'share':
                this.sharePost(postId);
                break;
            case 'comment':
                this.toggleComments(postId);
                break;
            case 'follow':
                this.toggleFollow(target.dataset.username, target);
                break;
            case 'load-more':
                this.loadMorePosts();
                break;
        }
    }

    // 表單提交處理
    handleSubmit(e) {
        const form = e.target;
        if (form.id === 'postForm') {
            e.preventDefault();
            this.createPost(form);
        }
    }

    // 滾動處理
    handleScroll() {
        // 無限滾動
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 1000) {
            this.loadMorePosts();
        }
    }

    // 鍵盤快捷鍵
    handleKeydown(e) {
        // Ctrl/Cmd + Enter 發送貼文
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const postForm = document.getElementById('postForm');
            if (postForm) {
                this.createPost(postForm);
            }
        }
    }

    // 初始化組件
    initializeComponents() {
        this.initTooltips();
        this.initImageLazyLoading();
        this.initNotifications();
        this.initSearchAutocomplete();
    }

    // 工具提示
    initTooltips() {
        document.querySelectorAll('[title]').forEach(el => {
            el.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.title);
            });
            el.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        const existing = document.querySelector('.custom-tooltip');
        if (existing) existing.remove();

        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        `;

        document.body.appendChild(tooltip);

        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';

        setTimeout(() => tooltip.style.opacity = '1', 10);
    }

    hideTooltip() {
        const tooltip = document.querySelector('.custom-tooltip');
        if (tooltip) tooltip.remove();
    }

    // 圖片懶載入
    initImageLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // 通知系統
    initNotifications() {
        this.notifications = [];
    }

    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#667eea'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        document.body.appendChild(notification);

        // 動畫進入
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);

        // 自動移除
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    // 搜尋自動完成
    initSearchAutocomplete() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length > 1) {
                searchTimeout = setTimeout(() => {
                    this.fetchSearchSuggestions(query);
                }, 300);
            } else {
                this.hideSearchSuggestions();
            }
        });
    }

    fetchSearchSuggestions(query) {
        // 模擬搜尋建議
        const suggestions = [
            '寵物健康',
            '新手飼養',
            '寵物訓練',
            '萌寵日常',
            '寵物美容'
        ].filter(s => s.includes(query));

        this.showSearchSuggestions(suggestions);
    }

    showSearchSuggestions(suggestions) {
        const existing = document.querySelector('.search-suggestions-dropdown');
        if (existing) existing.remove();

        if (suggestions.length === 0) return;

        const dropdown = document.createElement('div');
        dropdown.className = 'search-suggestions-dropdown';
        dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 100;
        `;

        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.textContent = suggestion;
            item.style.cssText = `
                padding: 10px 15px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background 0.2s;
            `;
            item.addEventListener('click', () => {
                document.getElementById('searchInput').value = suggestion;
                document.getElementById('searchForm').submit();
            });
            item.addEventListener('mouseenter', () => {
                item.style.background = '#f8f9fa';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = 'white';
            });
            dropdown.appendChild(item);
        });

        const searchBox = document.getElementById('searchInput').parentElement;
        searchBox.style.position = 'relative';
        searchBox.appendChild(dropdown);
    }

    hideSearchSuggestions() {
        const dropdown = document.querySelector('.search-suggestions-dropdown');
        if (dropdown) dropdown.remove();
    }

    // 按讚功能
    async toggleLike(postId, button) {
        if (!postId) return;

        const originalContent = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<div class="loading-spinner"></div>';

        try {
            const response = await fetch(`/social/post/${postId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                const icon = button.querySelector('i');
                const count = button.querySelector('.like-count');

                if (data.liked) {
                    button.classList.add('active');
                    icon.classList.remove('bi-heart');
                    icon.classList.add('bi-heart-fill');
                    button.classList.add('bounce');
                } else {
                    button.classList.remove('active');
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                }

                if (count) {
                    count.textContent = data.likes_count;
                }

                setTimeout(() => button.classList.remove('bounce'), 300);
                this.showNotification(data.liked ? '已按讚 ❤️' : '已取消按讚', 'success', 1000);
            } else {
                this.showNotification(data.error || '操作失敗', 'error');
            }
        } catch (error) {
            console.error('按讚失敗:', error);
            this.showNotification('網路錯誤，請稍後再試', 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = originalContent;
        }
    }

    // 創建貼文
    async createPost(form) {
        const formData = new FormData(form);
        const content = formData.get('content').trim();

        if (!content) {
            this.showNotification('請輸入貼文內容', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalContent = submitBtn.innerHTML;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="loading-spinner"></div> 發布中...';

        try {
            const response = await fetch('/social/post/create/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    post_type: 'text'
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('貼文發布成功！🎉', 'success');
                form.reset();

                // 刷新頁面或動態添加新貼文
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.showNotification(data.error || '發布失敗', 'error');
            }
        } catch (error) {
            console.error('發布貼文失敗:', error);
            this.showNotification('網路錯誤，請稍後再試', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalContent;
        }
    }

    // 分享貼文
    sharePost(postId) {
        if (navigator.share) {
            navigator.share({
                title: '毛日好社群分享',
                text: '來看看這篇有趣的貼文！',
                url: `${window.location.origin}/social/post/${postId}/`
            }).then(() => {
                this.showNotification('分享成功！', 'success');
            }).catch(err => {
                console.log('分享取消', err);
            });
        } else {
            // 複製連結到剪貼板 (postId now is UUID, much safer!)
            const url = `${window.location.origin}/social/post/${postId}/`;
            navigator.clipboard.writeText(url).then(() => {
                this.showNotification('連結已複製到剪貼板！', 'success');
            }).catch(() => {
                this.showNotification('分享失敗', 'error');
            });
        }
    }

    // 追蹤/取消追蹤
    async toggleFollow(username, button) {
        if (!username) return;

        const originalContent = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<div class="loading-spinner"></div> 處理中...';

        try {
            const response = await fetch(`/social/follow/${username}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                if (data.following) {
                    button.className = 'profile-btn btn-following';
                    button.innerHTML = `
                        <span class="follow-text">
                            <i class="bi bi-check-circle"></i>
                            已追蹤
                        </span>
                    `;
                    this.showNotification(`已追蹤 ${username}`, 'success');
                } else {
                    button.className = 'profile-btn btn-follow';
                    button.innerHTML = `
                        <i class="bi bi-person-plus"></i>
                        追蹤
                    `;
                    this.showNotification(`已取消追蹤 ${username}`, 'success');
                }

                // 更新粉絲數
                const followersCount = document.querySelector('.stat-card:nth-child(2) .stat-number');
                if (followersCount) {
                    followersCount.textContent = data.followers_count;
                }
            } else {
                this.showNotification(data.error || '操作失敗', 'error');
                button.innerHTML = originalContent;
            }
        } catch (error) {
            console.error('追蹤操作失敗:', error);
            this.showNotification('網路錯誤，請稍後再試', 'error');
            button.innerHTML = originalContent;
        } finally {
            button.disabled = false;
        }
    }

    // 切換留言區域
    toggleComments(postId) {
        const commentsSection = document.querySelector(`[data-post-id="${postId}"] .comments-section`);
        if (commentsSection) {
            commentsSection.style.display = commentsSection.style.display === 'none' ? 'block' : 'none';
        }
    }

    // 載入更多貼文
    loadMorePosts() {
        if (this.loadingMore) return;
        this.loadingMore = true;

        // 這裡實作載入更多貼文的邏輯
        console.log('載入更多貼文...');

        setTimeout(() => {
            this.loadingMore = false;
        }, 1000);
    }

    // 獲取 CSRF Token
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    // 工具函數：格式化時間
    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        const minute = 60 * 1000;
        const hour = minute * 60;
        const day = hour * 24;

        if (diff < minute) {
            return '剛剛';
        } else if (diff < hour) {
            return `${Math.floor(diff / minute)} 分鐘前`;
        } else if (diff < day) {
            return `${Math.floor(diff / hour)} 小時前`;
        } else {
            return `${Math.floor(diff / day)} 天前`;
        }
    }

    // 工具函數：文字截斷
    truncateText(text, maxLength = 100) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}

// 當頁面載入完成時初始化應用
document.addEventListener('DOMContentLoaded', () => {
    window.socialApp = new SocialApp();
});

// 全域函數（向後兼容）
function toggleLike(postId) {
    const button = document.querySelector(`[data-post-id="${postId}"] [data-action="like"]`);
    if (button && window.socialApp) {
        window.socialApp.toggleLike(postId, button);
    }
}

function sharePost(postId) {
    if (window.socialApp) {
        window.socialApp.sharePost(postId);
    }
}

function toggleFollow(username) {
    const button = document.querySelector(`[data-action="follow"][data-username="${username}"]`);
    if (button && window.socialApp) {
        window.socialApp.toggleFollow(username, button);
    }
}

function toggleComments(postId) {
    if (window.socialApp) {
        window.socialApp.toggleComments(postId);
    }
}

function repostPost(postId, username, content) {
    // Repost functionality - you can implement this based on your backend API
    if (confirm(`確定要轉發 ${username} 的貼文嗎？`)) {
        // Implementation would go here - likely an API call to create repost
        console.log('Reposting:', postId, username, content);
        if (window.socialApp) {
            window.socialApp.showNotification('貼文已轉發！', 'success');
        }
    }
}