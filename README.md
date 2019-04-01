# prometheus_redis_client
Python prometheus client that store metrics in Redis.

### Installation

    $ pip install prometheus_redis_client
    
Support Semver. Use >=0.x.0,<0.x+1.0 in you requirements file if you dont want to break code.

### Base usage


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
    
    def some_function():
        ...
        simple_cointer.inc()
        counter_with_labels.labels(name="piter").inc(2)
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


### Contribution

Write code, write tests, make pull request. 

Run tests if you have docker:

    $ docker-compose -f test-docker-compose.yml up --build
    
Start django app example:

    $ docker run -p 6379:6379 -d redis
    $ PROMETHEUS_REDIS_URI=redis://127.0.0.1:6379 python manage.py runserver

