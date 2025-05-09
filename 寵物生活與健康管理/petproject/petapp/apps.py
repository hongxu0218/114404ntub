# petapp/apps.py
from django.apps import AppConfig

class PetappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'petapp'

    def ready(self):
        import petapp.signals
