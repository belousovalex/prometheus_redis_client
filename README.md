# Prometheus Redis client
Python prometheus client that store metrics in Redis.

Use it in multiprocessing applications (started via gunicorn\uwsgi) and in deferred tasks like a celery tasks.

### Installation

    $ pip install prometheus_redis_client
    
Support Semver. Use >=0.x.0,<0.x+1.0 in you requirements file if you dont want to break code.

### Base usage

You can make global variable and use it when you want change metrics value. Support four type of values: Counter, Histogram, Summary, Gauge.

Each metric variable bind to some `prometheus_redis_client.Registry` object. By default its `prometheus_redis_client.REGISTRY`.
Registry contains redis client. So you can store metric values in different Redis instance if you make you own Registry object and bind it with your metrics. 

##### Setup REGISTRY

    import redis
    from prometheus_redis_client import REGISTRY
    
    REGISTRY.set_redis(redis.from_url("redis://localhost:6379"))

##### Counter

    from prometheus_redis_client import Counter
    simple_counter = Counter('simple_counter', 'Simple counter')
    counter_with_labels  = Counter(
        'counter_with_labels', 
        'Counter with labels',
        labelnames=["name"],
    )

* increase counter

    def some_function():
        ...
        simple_cointer.inc()
        counter_with_labels.labels(name="piter").inc(2)
        ...


* support for set current value
 
    def some_function():
        ...
        simple_cointer.set(100)
        counter_with_labels.labels(name="piter").set(2)
        ...

##### Summary

    from prometheus_redis_client import Summary
    simple_summary = Summary('simple_summary', 'Simple summary')
    summary_with_labels  = Summary(
        'summary_with_labels', 
        'Summary with labels',
        labelnames=["name"],
    )
    
    def some_function():
        ...
        simple_summary.inc()
        summary_with_labels.labels(name="piter").inc(2)
        ...
        
You can use decorator for time some function processing.

    @simple_summary.timeit()
    def another_func():
        ...
        
    # and with labels
    @summary_with_labels.timeit(name='greg')
    def another_func2():
        ...
        
##### Histogram

    from prometheus_redis_client import Histogram
    simple_histogram = Histogram('simple_histogram', 'Simple histogram')
    histogram_with_labels  = Histogram(
        'histogram_with_labels', 
        'Histogram with labels',
        labelnames=["name"],
    )
    
    def some_function():
        ...
        simple_histogram.observe(2.34)
        histogram_with_labels.labels(name="piter").observe(0.43)
        ...
    
You can use decorator for time function.

    @simple_histogram.timeit()
    def another_func():
        ...
        
    # and with labels
    @histogram_with_labels.timeit(name='greg')
    def another_func2():
        ...
        
        
##### CommonGauge

CommonGauge its simple metric that set, increment or decrement value to same Redis key from any process.

Represent as Gauge metric in output for Prometheus.

    from prometheus_redis_client import CommonGauge
    common_gauge = CommonGauge('common_gauge', 'Common gauge')
    gauge_with_labels  = CommonGauge(
        'common_gauge_with_labels', 
        'Common gauge with labels',
        labelnames=["name"],
    )
    gauge_with_labels_and_expire  = CommonGauge(
        'common_gauge_with_labels', 
        'Common gauge with labels',
        labelnames=["name"],
        expire=2,  # if you make set() then after 2 seconds Redis delete key/value for metric with given labels 
    )
    
    def some_function():
        ...
        simple_gauge.set(2.34)
        gauge_with_labels.labels(name="piter").set(0.43)
        ...
        
##### Gauge

Gauge metric per process. Add `gauge_index` label to metric as process identifier. 

    from prometheus_redis_client import Gauge
    simple_gauge = Gauge('simple_gauge', 'Simple gauge')
    gauge_with_labels  = Gauge(
        'gauge_with_labels', 
        'gauge with labels',
        labelnames=["name"],
    )
    
    def some_function():
        ...
        simple_gauge.set(2.34)
        gauge_with_labels.labels(name="piter").set(0.43)
        ...

Only Gauge metric set per process. 
If your application start via gunicorn\uwsgi with concurrency = N then you get N metrics value for each process. 
Metrics value contains `gauge_index` - its simple counter based on Redis.

Gauge metrics set value in Redis with expire period because you application can restart after N requests (harakiry mode for example) or server shout down.

Then after expire period gauge of dead process will be remove from metrics.

But you can change gauge metrics less often then expire period set. 
For not to lose metrics value special thread will refresh gauge values with period less then expire timeout. 


##### Export metrics

You cat export metrics to text. Example:

    from prometheus_redis_client import REGISTRY
    REGISTRY.output()


### Contribution

Welcome for contribution.

Run tests if you have docker:

    $ docker-compose -f test-docker-compose.yml up --build
    
Start django app example:

    $ docker-compose -f example-docker-compose.yml up --build

