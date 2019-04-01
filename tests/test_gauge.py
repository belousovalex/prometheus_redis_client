import time
from unittest.mock import patch

import pytest
import base64

from .helpers import MetricEnvironment
import prometheus_redis_client as prom


class TestGauge(object):

    def test_interface_without_labels(self):
        with MetricEnvironment() as redis:
            gauge = prom.Gauge(
                "test_gauge",
                "Gauge Documentation",
                expire=4,
            )

            gauge.set(12.3)
            gauge_index = int(redis.get(prom.DEFAULT_GAUGE_INDEX_KEY))

            group_key = gauge.get_metric_group_key()
            metric_key = "test_gauge:{}".format(
                base64.b64encode(('{"gauge_index": %s}' % gauge_index).encode('utf-8')).decode('utf-8')
            ).encode('utf-8')

            assert sorted(redis.smembers(group_key)) == sorted([
                metric_key,
            ])
            assert float(redis.get(metric_key)) == 12.3

            gauge.set(12.9)
            assert sorted(redis.smembers(group_key)) == sorted([
                metric_key,
            ])
            assert float(redis.get(metric_key)) == 12.9

            gauge.dec(1.7)
            assert sorted(redis.smembers(group_key)) == sorted([
                metric_key
            ])
            assert float(redis.get(metric_key)) == 11.2

            assert prom.REGISTRY.output() == (
                "# HELP test_gauge Gauge Documentation\n"
                "# TYPE test_gauge gauge\n" 
                "test_gauge{gauge_index=\"%s\"} 11.2"
            ) % gauge_index

    def test_interface_with_labels(self):
        with MetricEnvironment() as redis:
            gauge = prom.Gauge(
                "test_gauge",
                "Gauge Documentation",
                ['name'],
                expire=4,
            )

            gauge.labels(name='test').set(12.3)

            gauge_index = int(redis.get(prom.DEFAULT_GAUGE_INDEX_KEY))
            group_key = gauge.get_metric_group_key()
            metric_key = "test_gauge:{}".format(
                base64.b64encode(('{"gauge_index": %s, "name": "test"}' % gauge_index).encode('utf-8')).decode('utf-8')
            ).encode('utf-8')
            assert sorted(redis.smembers(group_key)) == sorted([
                metric_key,
            ])
            assert float(redis.get(metric_key)) == 12.3

            gauge.labels(name='test').inc(1.7)
            assert sorted(redis.smembers(group_key)) == sorted([
                metric_key,
            ])
            assert float(redis.get(metric_key)) == 14.0

            assert prom.REGISTRY.output() == (
                "# HELP test_gauge Gauge Documentation\n"
                "# TYPE test_gauge gauge\n"
                "test_gauge{gauge_index=\"%s\",name=\"test\"} 14"
            ) % gauge_index

    def test_auto_clean(self):
        with MetricEnvironment() as redis:
            gauge = prom.Gauge(
                "test_gauge",
                "Gauge Documentation",
                expire=4,
            )
            gauge.set(12.3)

            group_key = gauge.get_metric_group_key()
            gauge_index = int(redis.get(prom.DEFAULT_GAUGE_INDEX_KEY))
            metric_key = "test_gauge:{}".format(
                base64.b64encode(('{"gauge_index": %s}' % gauge_index).encode('utf-8')).decode('utf-8')
            ).encode('utf-8')
            assert float(redis.get(metric_key)) == 12.3

            # force stop refresh metrics
            prom.REGISTRY.refresher.cleanup_and_stop()

            # after expire timeout metric should be remove
            time.sleep(5)
            assert redis.get(metric_key) is None

            assert prom.REGISTRY.output() == (
                "# HELP test_gauge Gauge Documentation\n"
                "# TYPE test_gauge gauge"
            )
            # ... and remove metric from group
            assert redis.smembers(group_key) == set()

    def test_refresh(self):
        with MetricEnvironment() as redis:
            gauge = prom.Gauge(
                "test_gauge",
                "Gauge Documentation",
                expire=4,
            )

            gauge.set(12.3)

            gauge_index = int(redis.get(prom.DEFAULT_GAUGE_INDEX_KEY))
            metric_key = "test_gauge:{}".format(
                base64.b64encode(('{"gauge_index": %s}' % gauge_index).encode('utf-8')).decode('utf-8')
            ).encode('utf-8')
            assert float(redis.get(metric_key)) == 12.3

            time.sleep(6)
            assert float(redis.get(metric_key)) == 12.3

            assert (prom.REGISTRY.output()) == (
                "# HELP test_gauge Gauge Documentation\n"
                "# TYPE test_gauge gauge\n"
                "test_gauge{gauge_index=\"%s\"} 12.3"
            ) % gauge_index
