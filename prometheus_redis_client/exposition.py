import threading
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from prometheus_redis_client import REGISTRY

class _SilentHandler(WSGIRequestHandler):
    """WSGI handler that does not log requests."""

    def log_message(self, format, *args):
        """Log nothing."""

class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Thread per request HTTP server."""
    # Make worker threads "fire and forget". Beginning with Python 3.7 this
    # prevents a memory leak because ``ThreadingMixIn`` starts to gather all
    # non-daemon threads in a list in order to join on them at server close.
    daemon_threads = True

def make_wsgi_app(registry=REGISTRY):
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')])
        return [bytes(registry.output(), encoding='utf-8')]

    return prometheus_app

def start_wsgi_server(port, addr='', registry=REGISTRY):
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, ThreadingWSGIServer, handler_class=_SilentHandler)
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()

start_http_server = start_wsgi_server
