from unittest.mock import patch
import pytest

from .helpers import MetricEnvironment
import prometheus_redis_client as prom


class TestCounter(object):

    def test_interface_without_labels(self):
        with MetricEnvironment() as redis:

            counter = prom.Counter(
                name="test_counter1",
                documentation="Counter documentation"
            )

            counter.inc()
            group_key = counter.get_metric_group_key()
            metric_key = counter.get_metric_key({})

            assert redis.smembers(group_key) == {b'test_counter1:e30='}
            assert int(redis.get(metric_key)) == 1

            counter.inc(3)
            assert float(redis.get(metric_key)) == 4

            assert (prom.REGISTRY.output()) == (
                "# HELP test_counter1 Counter documentation\n"
                "# TYPE test_counter1 counter\n"
                "test_counter1 4"
            )

    def test_interface_with_labels(self):
        with MetricEnvironment() as redis:

            counter = prom.Counter(
                name="test_counter2",
                documentation="Counter documentation",
                labelnames=["host", "url"]
            )

            # need 'url' label
            with pytest.raises(ValueError):
                counter.labels(host="123.123.123.123").inc()

            # need use labels method
            with pytest.raises(Exception):
                counter.inc()

            labels = dict(host="123.123.123.123", url="/home/")
            counter.labels(**labels).inc(2)
            group_key = counter.get_metric_group_key()
            metric_key = counter.get_metric_key(labels)

            assert redis.smembers(group_key) == {b'test_counter2:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0='}
            assert int(redis.get(metric_key)) == 2

            assert counter.labels(**labels).inc(3) == 5
            assert int(redis.get(metric_key)) == 5

    @patch('prometheus_redis_client.base_metric.logger.exception')
    def test_silent_mode(self, mock_logger):
        """
        If we have some errors while send metric
        to redis we should not stop usefull work.
        """
        with MetricEnvironment():

            counter = prom.Counter(
                name="test_counter2",
                documentation="Counter documentation"
            )

            def raised_exception_func(*args, **kwargs):
                raise Exception()

            with patch("prometheus_redis_client.REGISTRY.redis.pipeline") as mock:
                mock.side_effect = raised_exception_func

                counter.inc()
            assert mock_logger.called


    def test_add_interface_without_labels(self):
        with MetricEnvironment() as redis:

            counter = prom.Counter(
                name="test_counter1",
                documentation="Counter documentation"
            )

            counter.set(1)
            group_key = counter.get_metric_group_key()
            metric_key = counter.get_metric_key({})

            assert redis.smembers(group_key) == {b'test_counter1:e30='}
            assert int(redis.get(metric_key)) == 1

            counter.set(30)
            assert float(redis.get(metric_key)) == 30

            counter.set(10)
            assert float(redis.get(metric_key)) == 10

            assert (prom.REGISTRY.output()) == (
                "# HELP test_counter1 Counter documentation\n"
                "# TYPE test_counter1 counter\n"
                "test_counter1 10"
            )