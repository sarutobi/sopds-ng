import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '8008')}"
accesslog = "-"
access_log_format = (
    "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s '%(f)s' '%(a)s' in %(D)sµs"  # noqa: E501
)

workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2)) + 1
worker_type = "gthread"
threads = int(os.getenv("PYTHON_MAX_THREADS", 2))

reload = False

timeout = int(os.getenv("WEB_TIMEOUT", 120))
