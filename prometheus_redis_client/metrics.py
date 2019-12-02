import copy
import json
import collections
import threading
from functools import partial

from prometheus_redis_client.base_metric import BaseMetric, MetricRepresentation, silent_wrapper
from prometheus_redis_client.helpers import timeit
from prometheus_redis_client.registry import Registry, REGISTRY

DEFAULT_GAUGE_INDEX_KEY = 'GLOBAL_GAUGE_INDEX'


class Metric(BaseMetric):

    def collect(self) -> list:
        redis = self.registry.redis
        group_key = self.get_metric_group_key()
        members = redis.smembers(group_key)

        result = []
        for metric_key in members:
            name, packed_labels = self.parse_metric_key(metric_key)
            labels = self.unpack_labels(packed_labels)
            value = redis.get(metric_key)
            if value is None:
                redis.srem(group_key, metric_key)
                continue
            result.append(MetricRepresentation(
                name=name,
                labels=labels,
                value=value.decode('utf-8'),
            ))
        return result

    def cleanup(self):
        pass


class CommonGauge(Metric):
    """Just simple store some value in one key from all processes."""

    type = 'gauge'
    wrapped_functions_names = ['set', 'inc', 'dec']

    def __init__(self, name: str,
                 documentation: str, labelnames: list = None,
                 registry: Registry=REGISTRY, expire: float = None):
        """
        Construct CommonGauge metric.
        :param name: name of metric
        :param documentation: metric description
        :param labelnames: list of metric labels
        :param registry: the Registry object collect Metric for representation
        :param expire: equivalent Redis `expire`; after that timeout Redis delete key. It useful when
        you want know if metric does not set a long time.
        """
        super().__init__(name, documentation, labelnames, registry)
        self._expire = expire

    def set(self, value, labels=None, expire: float = None):
        labels = labels or {}
        self._check_labels(labels)
        if value is None:
            raise ValueError('value can not be None')
        self._set(value, labels, expire=expire or self._expire)

    @silent_wrapper
    def _set(self, value, labels, expire: float = None):
        group_key = self.get_metric_group_key()
        metric_key = self.get_metric_key(labels)

        pipeline = self.registry.redis.pipeline()
        pipeline.sadd(group_key, metric_key)
        pipeline.set(metric_key, value, ex=expire)
        return pipeline.execute()

    def inc(self, value: float = 1, labels=None, expire: float = None):
        labels = labels or {}
        self._check_labels(labels)
        return self._inc(value, labels, expire=expire or self._expire)

    def dec(self, value: float = 1, labels=None, expire: float = None):
        labels = labels or {}
        self._check_labels(labels)
        return self._inc(-value, labels, expire=expire or self._expire)

    @silent_wrapper
    def _inc(self, value: float, labels: dict, expire: float = None):
        group_key = self.get_metric_group_key()
        metric_key = self.get_metric_key(labels)
        pipeline = self.registry.redis.pipeline()
        pipeline.sadd(group_key, metric_key)
        pipeline.incrbyfloat(metric_key, float(value))
        if expire:
            pipeline.expire(metric_key, expire)
        return pipeline.execute()[1]


class Counter(Metric):
    type = 'counter'
    wrapped_functions_names = ['inc', 'set']

    def inc(self, value: int = 1, labels=None):
        """
        Calculate metric with labels redis key.
        Add this key to set of key for this metric.
        """
        labels = labels or {}
        self._check_labels(labels)

        if not isinstance(value, int):
            raise ValueError("Value should be int, got {}".format(
                type(value)
            ))
        return self._inc(value, labels)

    @silent_wrapper
    def _inc(self, value: int, labels: dict):
        group_key = self.get_metric_group_key()
        metric_key = self.get_metric_key(labels)

        pipeline = self.registry.redis.pipeline()
        pipeline.sadd(group_key, metric_key)
        pipeline.incrby(metric_key, int(value))
        return pipeline.execute()[1]

    def set(self, value: int = 1, labels=None):
        """
        Calculate metric with labels redis key.
        Set this key to set of key for this metric.
        """
        labels = labels or {}
        self._check_labels(labels)

        if not isinstance(value, int):
            raise ValueError("Value should be int, got {}".format(
                type(value)
            ))
        return self._set(value, labels)

    @silent_wrapper
    def _set(self, value: int, labels: dict):
        group_key = self.get_metric_group_key()
        metric_key = self.get_metric_key(labels)

        pipeline = self.registry.redis.pipeline()
        pipeline.sadd(group_key, metric_key)
        pipeline.set(metric_key, int(value))
        return pipeline.execute()[1]


class Summary(Metric):
    type = 'summary'
    wrapped_functions_names = ['observe', ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeit = partial(timeit, metric_callback=self.observe)

    def observe(self, value, labels=None):
        labels = labels or {}
        self._check_labels(labels)
        print('DEBUG:', value, labels)
        return self._observer(value, labels)

    @silent_wrapper
    def _observer(self, value, labels: dict):
        group_key = self.get_metric_group_key()
        sum_metric_key = self.get_metric_key(labels, "_sum")
        count_metric_key = self.get_metric_key(labels, "_count")

        pipeline = self.registry.redis.pipeline()
        pipeline.sadd(group_key, count_metric_key, sum_metric_key)
        pipeline.incrbyfloat(sum_metric_key, float(value))
        pipeline.incr(count_metric_key)
        return pipeline.execute()[1]


class Gauge(Metric):
    type = 'gauge'
    wrapped_functions_names = ['inc', 'set', ]

    default_expire = 60

    def __init__(self, *args,
                 expire=default_expire,
                 refresh_enable=True,
                 gauge_index_key: str = DEFAULT_GAUGE_INDEX_KEY,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.gauge_index_key = gauge_index_key
        self.refresh_enable = refresh_enable
        self._refresher_added = False
        self.lock = threading.Lock()
        self.gauge_values = collections.defaultdict(lambda: 0.0)
        self.expire = expire
        self.index = None

    def add_refresher(self):
        if self.refresh_enable and not self._refresher_added:
            self.registry.refresher.add_refresh_function(
                self.refresh_values,
            )
            self._refresher_added = True

    def _set_internal(self, key: str, value: float):
        self.gauge_values[key] = value

    def _inc_internal(self, key: str, value: float):
        self.gauge_values[key] += value

    def inc(self, value: float, labels: dict = None):
        labels = labels or {}
        self._check_labels(labels)
        return self._inc(value, labels)

    def dec(self, value: float, labels: dict = None):
        labels = labels or {}
        self._check_labels(labels)
        return self._inc(-value, labels)

    @silent_wrapper
    def _inc(self, value: float, labels: dict):
        with self.lock:
            group_key = self.get_metric_group_key()
            labels['gauge_index'] = self.get_gauge_index()
            metric_key = self.get_metric_key(labels)

            pipeline = self.registry.redis.pipeline()
            pipeline.sadd(group_key, metric_key)
            pipeline.incrbyfloat(metric_key, float(value))
            pipeline.expire(metric_key, self.expire)
            self._inc_internal(metric_key, float(value))
            result = pipeline.execute()

        self.add_refresher()
        return result

    def set(self, value: float, labels:dict = None):
        labels = labels or {}
        self._check_labels(labels)
        return self._set(value, labels)

    @silent_wrapper
    def _set(self, value: float, labels: dict):
        with self.lock:
            group_key = self.get_metric_group_key()
            labels['gauge_index'] = self.get_gauge_index()
            metric_key = self.get_metric_key(labels)

            pipeline = self.registry.redis.pipeline()
            pipeline.sadd(group_key, metric_key)
            pipeline.set(
                metric_key,
                float(value),
                ex=self.expire,
            )
            self._set_internal(metric_key, float(value))
            result = pipeline.execute()
        self.add_refresher()
        return result

    def get_gauge_index(self):
        if self.index is None:
            self.index = self.make_gauge_index()
        return self.index

    def make_gauge_index(self):
        index = self.registry.redis.incr(
            self.gauge_index_key,
        )
        self.registry.refresher.add_refresh_function(
            self.refresh_values,
        )
        return index

    def refresh_values(self):
        with self.lock:
            for key, value in self.gauge_values.items():
                self.registry.redis.set(
                    key, value, ex=self.expire,
                )

    def cleanup(self):
        with self.lock:
            group_key = self.get_metric_group_key()
            keys = list(self.gauge_values.keys())
            if len(keys) == 0:
                return
            pipeline = self.registry.redis.pipeline()
            pipeline.srem(group_key, *keys)
            pipeline.delete(*keys)
            pipeline.execute()


class Histogram(Metric):
    type = 'histogram'
    wrapped_functions_names = ['observe', ]

    def __init__(self, *args, buckets: list, **kwargs):
        super().__init__(*args, **kwargs)
        self.buckets = sorted(buckets, reverse=True)
        self.timeit = partial(timeit, metric_callback=self.observe)

    def observe(self, value, labels=None):
        labels = labels or {}
        self._check_labels(labels)
        return self._a_observe(value, labels)

    @silent_wrapper
    def _a_observe(self, value: float, labels):
        group_key = self.get_metric_group_key()
        sum_key = self.get_metric_key(labels, '_sum')
        counter_key = self.get_metric_key(labels, '_count')
        pipeleine = self.registry.redis.pipeline()
        for bucket in self.buckets:
            if value > bucket:
                break
            labels['le'] = bucket
            bucket_key = self.get_metric_key(labels, '_bucket')
            pipeleine.sadd(group_key, bucket_key)
            pipeleine.incr(bucket_key)
        pipeleine.sadd(group_key, sum_key, counter_key)
        pipeleine.incr(counter_key)
        pipeleine.incrbyfloat(sum_key, float(value))
        return pipeleine.execute()

    def _get_missing_metric_values(self, redis_metric_values):
        missing_metrics_values = set(
            json.dumps({"le": b}) for b in self.buckets
        )
        groups = set("{}")

        # If flag is raised then we should add
        # *_sum and *_count values for empty labels.
        sc_flag = True
        for mv in redis_metric_values:
            key = json.dumps(mv.labels, sort_keys=True)
            labels = copy.copy(mv.labels)
            if 'le' in labels:
                del labels['le']
            group = json.dumps(labels, sort_keys=True)
            if group == "{}":
                sc_flag = False
            if group not in groups:
                for b in self.buckets:
                    labels['le'] = b
                    missing_metrics_values.add(
                        json.dumps(labels, sort_keys=True)
                    )
                groups.add(group)
            if key in missing_metrics_values:
                missing_metrics_values.remove(key)
        return missing_metrics_values, sc_flag

    def collect(self) -> list:
        redis_metrics = super().collect()
        missing_metrics_values, sc_flag = self._get_missing_metric_values(
            redis_metrics,
        )

        missing_values = [
            MetricRepresentation(
                self.name + "_bucket",
                labels=json.loads(ls),
                value=0,
            ) for ls in missing_metrics_values
        ]

        if sc_flag:
            missing_values.append(
                MetricRepresentation(
                    self.name + "_sum",
                    labels={},
                    value=0,
                ),
            )
            missing_values.append(
                MetricRepresentation(
                    self.name + "_count",
                    labels={},
                    value=0,
                ),
            )

        return redis_metrics + missing_values
