from contextlib import contextmanager

import redis
import prometheus_redis_client as prom


@contextmanager
def MetricEnvironment():
    redis_client = redis.from_url("redis://redis:6379")
    redis_client.flushdb()
    refresher = prom.Refresher(refresh_period=2)
    prom.REGISTRY.set_redis(redis_client)
    prom.REGISTRY.set_refresher(refresher)
    yield redis_client
    prom.REGISTRY.cleanup_and_stop()
