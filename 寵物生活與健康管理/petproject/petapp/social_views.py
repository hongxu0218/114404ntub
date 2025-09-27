# petapp/social_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Exists, OuterRef
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from collections import Counter
import json
import re

from .models import (
    UserProfile, Follow, Post, PostMedia, Like, Comment, CommentLike
)


def get_trending_topics():
    """獲取熱門話題"""
    # 獲取最近30天的貼文
    from datetime import datetime, timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)

    recent_posts = Post.objects.filter(created_at__gte=thirty_days_ago)

    # 定義話題及其對應的關鍵詞（與搜尋邏輯保持一致）
    topic_definitions = {
        '寵物健康': {'keywords': ['健康', '醫療', '疫苗', '體檢', '看醫生', '生病'], 'icon': 'bi-heart'},
        '新手飼養': {'keywords': ['飼養', '新手', '經驗'], 'icon': 'bi-book'},
        '萌寵瞬間': {'keywords': ['可愛', '萌', '瞬間', '日常', '生活'], 'icon': 'bi-camera'},
        '訓練技巧': {'keywords': ['訓練', '行為', '問題'], 'icon': 'bi-award'},
        '寵物美容': {'keywords': ['美容', '護理', '洗澡', '剪毛'], 'icon': 'bi-scissors'},
        '飲食分享': {'keywords': ['食物', '飼料', '零食'], 'icon': 'bi-bowl'},
        '好物推薦': {'keywords': ['用品', '玩具', '推薦'], 'icon': 'bi-star'},
        '寵物分享': {'keywords': ['貓咪', '狗狗', '寵物', '毛孩'], 'icon': 'bi-heart'},
        '生活陪伴': {'keywords': ['散步', '陪伴', '互動'], 'icon': 'bi-people'},
    }

    # 統計每個話題的貼文
    trending = []

    for topic_title, topic_info in topic_definitions.items():
        keywords = topic_info['keywords']
        icon = topic_info['icon']

        # 搜尋包含任一關鍵詞的貼文
        q_objects = Q()
        for keyword in keywords:
            q_objects |= Q(content__icontains=keyword)

        topic_posts = recent_posts.filter(q_objects).distinct()
        post_count = topic_posts.count()


        if post_count > 0:
            # 計算互動分數
            interaction_score = sum([
                post.likes_count + post.comments_count + post.shares_count + 1
                for post in topic_posts
            ])

            # 計算話題熱度

            trending.append({
                'title': topic_title,
                'count': post_count,
                'icon': icon,
                'interaction_score': interaction_score,
                'keyword': topic_title  # 使用話題標題作為搜尋關鍵詞
            })

    # 如果沒有足夠的真實數據，補充一些默認話題
    if len(trending) < 3:
        default_topics = [
            {'title': '寵物日常', 'count': 0, 'icon': 'bi-house', 'keyword': '日常'},
            {'title': '健康照護', 'count': 0, 'icon': 'bi-heart', 'keyword': '健康'},
            {'title': '新手指南', 'count': 0, 'icon': 'bi-book', 'keyword': '新手'},
        ]

        for topic in default_topics:
            if len(trending) >= 5:
                break
            if not any(t['title'] == topic['title'] for t in trending):
                trending.append(topic)

    # 按互動分數排序，然後按貼文數量排序
    trending.sort(key=lambda x: (x.get('interaction_score', 0), x['count']), reverse=True)

    return trending[:5]


def social_home(request):
    """社群媒體首頁"""
    # 獲取所有貼文，按時間排序
    posts = Post.objects.select_related('user').prefetch_related(
        'media_files', 'post_comments__user', 'post_likes'
    ).order_by('-created_at')

    # 添加用戶點讚狀態注釋
    if request.user.is_authenticated:
        posts = posts.annotate(
            user_liked=Exists(
                Like.objects.filter(post=OuterRef('pk'), user=request.user)
            )
        )

    # 如果用戶已登入，優先顯示追蹤用戶的貼文
    if request.user.is_authenticated:
        following_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
        if following_users:
            following_posts = posts.filter(user__in=following_users)
            other_posts = posts.exclude(user__in=following_users)
            posts = list(following_posts) + list(other_posts)

    # 分頁
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page', 1)
    page_posts = paginator.get_page(page_number)

    # 獲取追蹤列表
    following_list = []
    if request.user.is_authenticated:
        try:
            following_list = Follow.objects.filter(follower=request.user).select_related('following')[:10]
            # 確保每個被追蹤的用戶都有 UserProfile
            for follow in following_list:
                if not hasattr(follow.following, 'social_profile'):
                    UserProfile.objects.get_or_create(user=follow.following)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading following list: {str(e)}", exc_info=True)
            following_list = []

    # 獲取熱門話題
    trending_topics = get_trending_topics()

    context = {
        'posts': page_posts,
        'following_list': following_list,
        'trending_topics': trending_topics,
    }
    return render(request, 'social/home.html', context)


@login_required
def user_profile(request, username):
    """用戶個人頁面"""
    user = get_object_or_404(User, username=username)

    # 獲取或創建用戶檔案
    profile, created = UserProfile.objects.get_or_create(user=user)

    # 獲取用戶的貼文
    posts = Post.objects.filter(user=user).select_related('user').prefetch_related(
        'media_files', 'post_comments__user', 'post_likes'
    ).annotate(
        user_liked=Exists(
            Like.objects.filter(post=OuterRef('pk'), user=request.user)
        )
    ).order_by('-created_at')

    # 分頁
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page', 1)
    page_posts = paginator.get_page(page_number)

    # 檢查是否已追蹤
    is_following = False
    if request.user.is_authenticated and request.user != user:
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()

    context = {
        'profile_user': user,
        'profile': profile,
        'posts': page_posts,
        'is_following': is_following,
        'is_own_profile': request.user == user,
    }
    return render(request, 'social/profile.html', context)


@login_required
@require_http_methods(["POST"])
def create_post(request):
    """創建貼文"""
    print(f"收到創建貼文請求 - 用戶: {request.user.username}")
    try:
        # 檢查是否為 FormData (有文件上傳) 或 JSON
        if request.content_type.startswith('multipart/form-data'):
            # FormData 處理
            content = request.POST.get('content', '').strip()
            post_type = request.POST.get('post_type', 'text')
            location = request.POST.get('location', '').strip()
            # 優先使用新的多媒體系統
            image_files = request.FILES.getlist('images')
            video_files = request.FILES.getlist('videos')

            # 舊版兼容性 - 只有在沒有新格式時才使用
            if not image_files and not video_files:
                single_image = request.FILES.get('image')
                single_video = request.FILES.get('video')
                if single_image:
                    image_files = [single_image]
                if single_video:
                    video_files = [single_video]
        else:
            # JSON 處理
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            post_type = data.get('post_type', 'text')
            location = data.get('location', '').strip()
            image_files = []
            video_files = []

        if not content:
            return JsonResponse({'success': False, 'error': '內容不能為空'})

        # 確定貼文類型
        if image_files and video_files:
            post_type = 'mixed'
        elif image_files:
            post_type = 'image'
        elif video_files:
            post_type = 'video'

        # 創建貼文
        print(f"創建貼文 - 內容: '{content}', 類型: {post_type}, 位置: '{location}'")
        post = Post.objects.create(
            user=request.user,
            content=content,
            post_type=post_type,
            location=location if location else None
        )
        print(f"成功創建貼文 ID: {post.id}")

        # 處理多個圖片上傳
        print(f"處理圖片文件數量: {len(image_files)}")
        for i, image_file in enumerate(image_files):
            PostMedia.objects.create(
                post=post,
                media_type='image',
                file=image_file,
                order=i
            )
            print(f"已創建圖片媒體 {i+1}")

        # 處理多個影片上傳
        video_start_order = len(image_files)
        print(f"處理影片文件數量: {len(video_files)}")
        for i, video_file in enumerate(video_files):
            PostMedia.objects.create(
                post=post,
                media_type='video',
                file=video_file,
                order=video_start_order + i
            )
            print(f"已創建影片媒體 {i+1}")

        # 更新用戶檔案的貼文數
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.posts_count = Post.objects.filter(user=request.user).count()
        profile.save()

        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'redirect_url': reverse('social:home')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def toggle_like(request, post_id):
    """切換貼文點讚狀態"""
    try:
        post = get_object_or_404(Post, id=post_id)

        like, created = Like.objects.get_or_create(user=request.user, post=post)

        if not created:
            # 已經點讚，取消點讚
            like.delete()
            post.likes_count = max(0, post.likes_count - 1)
            liked = False
        else:
            # 新增點讚
            post.likes_count += 1
            liked = True

        post.save()

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': post.likes_count
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"toggle_like error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def add_comment(request, post_id):
    """新增留言"""
    try:
        post = get_object_or_404(Post, id=post_id)

        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            parent_id = data.get('parent_id')

            if not content:
                return JsonResponse({'success': False, 'error': '留言內容不能為空'})

            parent_comment = None
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)

            comment = Comment.objects.create(
                user=request.user,
                post=post,
                content=content,
                parent_comment=parent_comment
            )

            # 更新貼文的留言數
            post.comments_count = Comment.objects.filter(post=post).count()
            post.save()

            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'content': comment.content,
                'username': comment.user.username,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
            })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '無效的JSON格式'})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"add_comment inner error: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"add_comment outer error: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def delete_post(request, post_id):
    """刪除貼文"""
    try:
        post = get_object_or_404(Post, id=post_id, user=request.user)

        # 刪除相關媒體文件
        for media in post.media_files.all():
            if media.file:
                # 刪除實際文件
                import os
                if os.path.exists(media.file.path):
                    os.remove(media.file.path)
                media.delete()

        # 刪除貼文
        post.delete()

        # 更新用戶檔案的貼文數
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.posts_count = Post.objects.filter(user=request.user).count()
        profile.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def toggle_comment_like(request, comment_id):
    """切換留言點讚狀態"""
    try:
        comment = get_object_or_404(Comment, id=comment_id)

        like, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)

        if not created:
            # 已經點讚，取消點讚
            like.delete()
            comment.likes_count = max(0, comment.likes_count - 1)
            liked = False
        else:
            # 新增點讚
            comment.likes_count += 1
            liked = True

        comment.save()

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': comment.likes_count
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"toggle_comment_like error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def toggle_follow(request, username):
    """切換追蹤狀態"""
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({'success': False, 'error': '不能追蹤自己'})

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    if not created:
        # 已經追蹤，取消追蹤
        follow.delete()
        following = False
    else:
        # 新增追蹤
        following = True

    # 更新用戶檔案的統計數據
    follower_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    following_profile, _ = UserProfile.objects.get_or_create(user=target_user)

    follower_profile.following_count = Follow.objects.filter(follower=request.user).count()
    following_profile.followers_count = Follow.objects.filter(following=target_user).count()

    follower_profile.save()
    following_profile.save()

    return JsonResponse({
        'success': True,
        'following': following,
        'followers_count': following_profile.followers_count,
        'following_count': follower_profile.following_count
    })


@login_required
@require_http_methods(["POST"])
def repost(request, post_id):
    """轉發貼文"""
    original_post = get_object_or_404(Post, id=post_id)

    # 檢查是否已經轉發過
    existing_repost = Post.objects.filter(
        user=request.user,
        original_post=original_post,
        is_repost=True
    ).exists()

    if existing_repost:
        return JsonResponse({'success': False, 'error': '已經轉發過此貼文'})

    # 獲取轉發評論（如果有的話）
    try:
        data = json.loads(request.body) if request.body else {}
        repost_comment = data.get('comment', '').strip()
    except:
        repost_comment = ''

    # 創建轉發貼文
    # 轉發者的評論作為內容，原始內容通過 original_post 保存
    repost = Post.objects.create(
        user=request.user,
        content=repost_comment,  # 只保存轉發者的評論
        post_type='text',  # 轉發本身是文字類型
        original_post=original_post,
        is_repost=True
    )

    # 轉發不需要複製媒體檔案，媒體會通過原始貼文顯示

    # 更新原貼文的分享數
    original_post.shares_count += 1
    original_post.save()

    # 更新用戶檔案的貼文數
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.posts_count = Post.objects.filter(user=request.user).count()
    profile.save()

    return JsonResponse({
        'success': True,
        'repost_id': repost.id,
        'shares_count': original_post.shares_count
    })


@login_required
def get_comments(request, post_id):
    """獲取貼文留言"""
    try:
        post = get_object_or_404(Post, id=post_id)

        comments = Comment.objects.filter(post=post, parent_comment=None).select_related('user').prefetch_related(
            'comment_likes'
        ).annotate(
            user_liked=Exists(
                CommentLike.objects.filter(comment=OuterRef('pk'), user=request.user)
            ) if request.user.is_authenticated else False
        ).order_by('created_at')

        comments_data = []
        for comment in comments:
            # 確保留言作者有 UserProfile
            if not hasattr(comment.user, 'social_profile'):
                UserProfile.objects.get_or_create(user=comment.user)

            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'username': comment.user.username,
                'avatar_url': comment.user.social_profile.avatar.url if hasattr(comment.user, 'social_profile') and comment.user.social_profile.avatar else None,
                'created_at': timezone.localtime(comment.created_at).strftime('%Y-%m-%d %H:%M'),
                'likes_count': comment.likes_count,
                'user_liked': comment.user_liked,
                'is_own_comment': comment.user == request.user
            })

        return JsonResponse({
            'success': True,
            'comments': comments_data
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"get_comments error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_topic_keywords(topic_title):
    """根據話題標題獲取相關關鍵詞"""
    keyword_map = {
        '寵物健康': ['健康', '醫療', '疫苗', '體檢', '看醫生', '生病'],
        '新手飼養': ['飼養', '新手', '經驗'],
        '萌寵瞬間': ['可愛', '萌', '瞬間', '日常', '生活'],
        '訓練技巧': ['訓練', '行為', '問題'],
        '寵物美容': ['美容', '護理', '洗澡', '剪毛'],
        '飲食分享': ['食物', '飼料', '零食'],
        '好物推薦': ['用品', '玩具', '推薦'],
        '寵物分享': ['貓咪', '狗狗', '寵物', '毛孩'],
        '生活陪伴': ['散步', '陪伴', '互動'],
    }
    return keyword_map.get(topic_title, [topic_title])


@login_required
def search_posts(request):
    """搜尋貼文"""
    query = request.GET.get('q', '').strip()
    posts = []

    if query:
        # 檢查是否為熱門話題搜尋
        topic_keywords = get_topic_keywords(query)

        if len(topic_keywords) > 1:
            # 如果是話題搜尋，搜尋所有相關關鍵詞
            # 話題搜尋：使用相關關鍵詞
            q_objects = Q()
            for keyword in topic_keywords:
                q_objects |= Q(content__icontains=keyword)

            # 為了與熱門話題保持一致，只搜尋最近30天的貼文
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)

            # 先計算總數（包含30天限制）
            total_count = Post.objects.filter(q_objects, created_at__gte=thirty_days_ago).count()

            # 再取前20筆顯示
            posts = Post.objects.filter(q_objects, created_at__gte=thirty_days_ago).select_related('user').prefetch_related(
                'media_files', 'post_comments__user', 'post_likes'
            ).annotate(
                user_liked=Exists(
                    Like.objects.filter(post=OuterRef('pk'), user=request.user)
                )
            ).order_by('-created_at')[:20]
        else:
            # 普通搜尋：搜尋貼文內容和用戶名
            posts = Post.objects.filter(
                Q(content__icontains=query) | Q(user__username__icontains=query)
            ).select_related('user').prefetch_related(
                'media_files', 'post_comments__user', 'post_likes'
            ).annotate(
                user_liked=Exists(
                    Like.objects.filter(post=OuterRef('pk'), user=request.user)
                )
            ).order_by('-created_at')[:20]

    # 獲取熱門話題
    trending_topics = get_trending_topics()

    context = {
        'posts': posts,
        'query': query,
        'trending_topics': trending_topics,
    }
    return render(request, 'social/search.html', context)


@login_required
def edit_profile(request):
    """編輯個人檔案"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        bio = request.POST.get('bio', '').strip()

        profile.bio = bio

        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        if 'banner' in request.FILES:
            profile.banner = request.FILES['banner']

        profile.save()
        messages.success(request, '個人檔案已更新')
        return redirect('social:profile', username=request.user.username)

    context = {
        'profile': profile,
    }
    return render(request, 'social/edit_profile.html', context)