import os

import dotenv
from celery import Celery
from django.apps import apps
from django.conf import settings

dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spt.settings')

app = Celery('spt', broker=settings.BROKER_URL)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.broker_url = settings.BROKER_URL
app.conf.redbeat_redis_url = settings.BROKER_URL + "/1"
app.conf.result_backend = settings.BROKER_URL + '/0'
app.conf.redbeat_lock_key = None

app.conf.beat_schedule = {
}

app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()])


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
