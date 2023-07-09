import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rpg_agg.settings')

app = Celery('rpg_agg')

app.conf.beat_schedule = {
    'add-every-8-hour': {
        'task': 'news.tasks.all_game_news_update',
        'schedule': crontab(minute='0', hour='*/4'),  # Каждые 4 часа
    },
    'every_midnight': {
        'task': 'users.tasks.check_finish_email_verify',
        'schedule': crontab(minute='0', hour='0'),  # Каждый день в полночь
    },
    'every_mounth': {
        'task': 'users.tasks.check_useless_avatar',
        'schedule': crontab('0', '0', day_of_month='1')  # Первого числа, каждый месяц
    },
}

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
