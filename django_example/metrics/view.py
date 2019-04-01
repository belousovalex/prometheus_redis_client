from django.http.response import HttpResponse
from prometheus_redis_client import REGISTRY


def metrics_view(request):
    return HttpResponse(REGISTRY.output(), content_type="text/plain")
