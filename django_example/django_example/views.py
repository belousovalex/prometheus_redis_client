import time
import random
from django.http.response import HttpResponse


def increment_view(request):
    sleep_time = random.randint(1, 700) / 1000.0
    time.sleep(sleep_time)
    return HttpResponse("%f" % sleep_time)
