# petapp/social_urls.py
from django.urls import path
from . import social_views

app_name = 'social'

urlpatterns = [
    # 社群首頁
    path('', social_views.social_home, name='home'),

    # 用戶相關
    path('profile/edit/', social_views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', social_views.user_profile, name='profile'),

    # 貼文相關
    path('post/create/', social_views.create_post, name='create_post'),
    path('post/<uuid:post_id>/', social_views.post_detail, name='post_detail'),
    path('post/<uuid:post_id>/like/', social_views.toggle_like, name='toggle_like'),
    path('post/<uuid:post_id>/repost/', social_views.repost, name='repost'),
    path('post/<uuid:post_id>/delete/', social_views.delete_post, name='delete_post'),

    # 留言相關
    path('post/<uuid:post_id>/comments/', social_views.get_comments, name='get_comments'),
    path('post/<uuid:post_id>/comment/', social_views.add_comment, name='add_comment'),
    path('comment/<uuid:comment_id>/like/', social_views.toggle_comment_like, name='toggle_comment_like'),

    # 追蹤相關
    path('follow/<str:username>/', social_views.toggle_follow, name='toggle_follow'),

    # 搜尋
    path('search/', social_views.search_posts, name='search_posts'),
]