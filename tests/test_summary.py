from unittest.mock import patch

import pytest

from .helpers import MetricEnvironment
import prometheus_redis_client as prom


class TestSummary(object):

    def test_interface_without_labels(self):
        with MetricEnvironment() as redis:

            summary = prom.Summary(
                name="test_summary",
                documentation="Summary documentation",
            )

            summary.observe(1)
            group_key = summary.get_metric_group_key()

            assert sorted(redis.smembers(group_key)) == [
                b'test_summary_count:e30=',
                b'test_summary_sum:e30='
            ]
            assert int(redis.get('test_summary_count:e30=')) == 1
            assert float(redis.get('test_summary_sum:e30=')) == 1

            summary.observe(3.5)
            assert int(redis.get('test_summary_count:e30=')) == 2
            assert float(redis.get('test_summary_sum:e30=')) == 4.5

            assert prom.REGISTRY.output() == (
                "# HELP test_summary Summary documentation\n"
                "# TYPE test_summary summary\n"
                "test_summary_count 2\n"
                "test_summary_sum 4.5"
            )

    def test_interface_with_labels(self):
        with MetricEnvironment() as redis:

            summary = prom.Summary(
                name="test_summary",
                documentation="Summary documentation",
                labelnames=["host", "url", ],
            )

            # need 'url' label
            with pytest.raises(ValueError, match=r"Expect define all labels: .*?\. Got only: host"):
                summary.labels(host="123.123.123.123").observe(3)

            # need use labels method
            with pytest.raises(Exception, match=r"Expect define all labels: .*?\. Got only: "):
                summary.observe(1)

            labels = dict(host="123.123.123.123", url="/home/")
            summary.labels(**labels).observe(2)
            group_key = summary.get_metric_group_key()

            assert sorted(redis.smembers(group_key)) == [
                b'test_summary_count:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0=',
                b'test_summary_sum:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0=',
            ]
            metric_sum_key = 'test_summary_sum:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0='
            metric_count_key = 'test_summary_count:eyJob3N0IjogIjEyMy4xMjMuMTIzLjEyMyIsICJ1cmwiOiAiL2hvbWUvIn0='
            assert int(redis.get(metric_count_key)) == 1
            assert float(redis.get(metric_sum_key)) == 2

            assert summary.labels(**labels).observe(3.1) == 5.1
            assert int(redis.get(metric_count_key)) == 2
            assert float(redis.get(metric_sum_key)) == 5.1

            assert prom.REGISTRY.output() == (
                '# HELP test_summary Summary documentation\n'
                '# TYPE test_summary summary\n'
                'test_summary_count{host="123.123.123.123",url="/home/"} 2\n'
                'test_summary_sum{host="123.123.123.123",url="/home/"} 5.1'
            )

    @patch('prometheus_redis_client.base_metric.logger.exception')
    def test_silent_mode(self, mock_logger):
        """
        If we have some errors while send metric
        to redis we should not stop usefull work.
        """
        with MetricEnvironment():

            summary = prom.Summary(
                name="test_summary",
                documentation="Summary documentation",
            )

            def raised_exception_func(*args, **kwargs):
                raise Exception()

            with patch("prometheus_redis_client.REGISTRY.redis.pipeline") as mock:
                mock.side_effect = raised_exception_func

                summary.observe(1)
            assert mock_logger.called
