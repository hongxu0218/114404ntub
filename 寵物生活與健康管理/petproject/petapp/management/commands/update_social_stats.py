"""
管理命令：更新所有用戶的社群統計數據
使用方法: python manage.py update_social_stats
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from petapp.models import UserProfile, Follow, Post


class Command(BaseCommand):
    help = '更新所有用戶的社群統計數據（粉絲數、追蹤數、貼文數）'

    def handle(self, *args, **options):
        self.stdout.write('開始更新社群統計數據...')

        updated_count = 0
        error_count = 0

        # 獲取所有用戶
        users = User.objects.all()
        total_users = users.count()

        self.stdout.write(f'找到 {total_users} 個用戶')

        for user in users:
            try:
                # 獲取或創建用戶檔案
                profile, created = UserProfile.objects.get_or_create(user=user)

                # 計算追蹤數
                following_count = Follow.objects.filter(follower=user).count()

                # 計算粉絲數
                followers_count = Follow.objects.filter(following=user).count()

                # 計算貼文數
                posts_count = Post.objects.filter(user=user).count()

                # 更新統計數據
                profile.following_count = following_count
                profile.followers_count = followers_count
                profile.posts_count = posts_count
                profile.save()

                updated_count += 1

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] {user.username}: 創建檔案 | '
                            f'追蹤: {following_count}, 粉絲: {followers_count}, 貼文: {posts_count}'
                        )
                    )
                else:
                    self.stdout.write(
                        f'[OK] {user.username}: '
                        f'追蹤: {following_count}, 粉絲: {followers_count}, 貼文: {posts_count}'
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] {user.username}: 更新失敗 - {str(e)}')
                )

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f'更新完成！\n'
                f'成功: {updated_count} 個用戶\n'
                f'失敗: {error_count} 個用戶'
            )
        )
