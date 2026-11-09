"""Prometheus metrics. Defined here, not in main.py: with uvicorn's reload mode on Windows,
main.py is imported twice in the child process, and a metric can only be registered once."""

from prometheus_client import Counter, Histogram

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_SECONDS = Histogram("http_request_seconds", "HTTP request time in seconds", ["method", "path"])
