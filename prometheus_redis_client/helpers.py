import time
from typing import Callable
from functools import wraps


def timeit(metric_callback: Callable, **labels):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            metric_callback(time.time() - start, labels=labels)
            return result
        return func_wrapper
    return wrapper
