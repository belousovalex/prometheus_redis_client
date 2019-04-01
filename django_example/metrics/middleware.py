import time
from metrics import general
from django.urls import resolve


class MetricsMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        viewname = resolve(request.path).view_name
        general.count_of_requests.labels(viewname=viewname).inc()
        start_time = time.time()
        try:
            return self.get_response(request)
        finally:
            general.request_latency.labels(viewname=viewname).observe(time.time() - start_time)