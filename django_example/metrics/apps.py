import redis
from django.apps import AppConfig
from django.conf import settings

from prometheus_redis_client import REGISTRY


class MetricAppConfig(AppConfig):
    name = 'metrics'
    verbose_name = "metrics"

    def ready(self):
        super().ready()
        REGISTRY.set_redis(redis.from_url(settings.PROMETHEUS_REDIS_URI))

