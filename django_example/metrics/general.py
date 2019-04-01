from prometheus_redis_client import Counter, Histogram

count_of_requests = Counter(
    "count_of_requests",
    "Count of requests",
    labelnames=["viewname", ],
)

request_latency = Histogram(
    "request_latency",
    "Request latency",
    labelnames=["viewname", ],
    buckets=[0.10, 0.50, 0.100, 0.500],
)