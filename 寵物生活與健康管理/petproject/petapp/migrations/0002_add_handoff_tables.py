from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('petapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HandoffTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(max_length=64, db_index=True)),
                ('name', models.CharField(max_length=64, blank=True)),
                ('contact', models.CharField(max_length=128, blank=True)),
                ('channel', models.CharField(max_length=32, default='web')),
                ('is_open', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-is_open', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='HandoffMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.CharField(max_length=16, choices=[('user','user'),('agent','agent'),('system','system')])),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=models.CASCADE, related_name='messages', to='petapp.handoffticket')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
