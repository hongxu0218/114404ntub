from django.core.management.base import BaseCommand
from petapp.adoption_sync import AdoptionDataSyncService

class Command(BaseCommand):
    help = '同步動物認領養資料'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制同步所有資料',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('開始同步動物認領養資料...')
        
        sync_service = AdoptionDataSyncService()
        success, message = sync_service.sync_all_data()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'同步成功: {message}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'同步失敗: {message}')
            )