from unittest.mock import patch
import pytest

from .helpers import MetricEnvironment
import prometheus_redis_client as prom


class TestCommonGauge(object):

    def test_none_value_exception(self):
        with MetricEnvironment():

            const = prom.CommonGauge(
                name="test_const1",
                documentation="Const metric documentation",
            )
            with pytest.raises(ValueError, match=r"value can not be None"):
                const.set(None)

    def test_interface_without_labels(self):
        with MetricEnvironment() as redis:

            const = prom.CommonGauge(
                name="test_const1",
                documentation="Const metric documentation",
            )

            const.set(12)
            group_key = const.get_metric_group_key()
            metric_key = const.get_metric_key({})

            assert redis.smembers(group_key) == {b'test_const1:e30='}
            assert int(redis.get(metric_key)) == 12

            const.set(3)
            assert float(redis.get(metric_key)) == 3

            assert (prom.REGISTRY.output()) == (
                "# HELP test_const1 Const metric documentation\n"
                "# TYPE test_const1 gauge\n" 
                "test_const1 3"
            )

    def test_interface_with_labels(self):
        with MetricEnvironment() as redis:

            const = prom.CommonGauge(
                name="test_const2",
                documentation="Const documentation",
                labelnames=["host", "url"]
            )

            # need 'url' label
            with pytest.raises(ValueError):
                const.labels(host="123.123.123.123").inc()

            # need use labels method
            with pytest.raises(Exception):
                const.set(12)

            labels = dict(host="123.123.123.123", url="/home/")
            const.labels(**labels).set(2)
            group_key = const.get_metric_group_key()
            metric_key = const.get_metric_key(labels)

            assert redis.smembers(group_key) == {b'test_const2:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0='}
            assert int(redis.get(metric_key)) == 2

            const.labels(**labels).set(3)
            assert int(redis.get(metric_key)) == 3

            assert (prom.REGISTRY.output()) == (
                "# HELP test_const2 Const documentation\n"
                "# TYPE test_const2 gauge\n" 
                "test_const2{host=\"123.123.123.123\",url=\"/home/\"} 3"
            )

    @patch('prometheus_redis_client.base_metric.logger.exception')
    def test_silent_mode(self, mock_logger):
        """
        If we have some errors while send metric
        to redis we should not stop usefull work.
        """
        with MetricEnvironment():

            const = prom.CommonGauge(
                name="test_counter2",
                documentation="Counter documentation"
            )

            def raised_exception_func(*args, **kwargs):
                raise Exception()

            with patch("prometheus_redis_client.REGISTRY.redis.pipeline") as mock:
                mock.side_effect = raised_exception_func

                const.set(12)
            assert mock_logger.called
