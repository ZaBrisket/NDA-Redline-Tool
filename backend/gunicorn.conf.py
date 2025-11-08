"""
Gunicorn configuration for Railway deployment
Optimized for production with reduced workers and proper logging
"""

import multiprocessing
import os
import sys

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"

# Worker configuration
# Reduce from 4 to 2 workers to minimize redundant initialization
# Each worker will initialize its own orchestrator instance
workers_env = os.getenv('WORKERS')
if workers_env:
    workers = int(workers_env)
else:
    # Default: min of 2 or CPU count (whichever is lower)
    workers = min(multiprocessing.cpu_count(), 2)

worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeouts
timeout = 120  # 2 minutes for long-running AI operations
graceful_timeout = 30  # 30 seconds for graceful shutdown
keepalive = 5  # Keep connections alive for 5 seconds

# Process naming
proc_name = 'nda-redlining-api'

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Logging configuration
# Railway reads from stdout/stderr directly
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = os.getenv('LOG_LEVEL', 'info').lower()

# Access log format with timing information
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# Disable access log buffering for real-time Railway logs
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'class': 'logging.Formatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stdout
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stderr
        }
    },
    'root': {
        'level': loglevel.upper(),
        'handlers': ['console']
    },
    'loggers': {
        'gunicorn.error': {
            'level': loglevel.upper(),
            'handlers': ['error_console'],
            'propagate': False,
            'qualname': 'gunicorn.error'
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
            'qualname': 'gunicorn.access'
        }
    }
}

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("=" * 60)
    server.log.info("Gunicorn master process starting")
    server.log.info(f"Configuration: {workers} workers, {worker_class} worker class")
    server.log.info(f"Binding to {bind}")
    server.log.info(f"Timeout: {timeout}s, Graceful timeout: {graceful_timeout}s")
    server.log.info("=" * 60)


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading workers...")


def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Gunicorn master process ready. Workers are being spawned...")


def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info(f"Pre-fork: Preparing to spawn worker")


def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info(f"Worker spawned (PID: {worker.pid})")


def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forking new master process...")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal"""
    worker.log.info(f"Worker {worker.pid} received SIGINT/SIGQUIT - initiating graceful shutdown")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.warning(f"Worker {worker.pid} received SIGABRT - forcing shutdown")


def post_worker_init(worker):
    """Called just after a worker has initialized the application"""
    worker.log.info(f"Worker {worker.pid} initialized successfully and is ready to handle requests")


def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} exited")


def child_exit(server, worker):
    """Called just after a worker has been reaped"""
    server.log.info(f"Worker {worker.pid} reaped")


def on_exit(server):
    """Called just before exiting Gunicorn"""
    server.log.info("=" * 60)
    server.log.info("Gunicorn master process shutting down")
    server.log.info("=" * 60)


# Error handling
def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes"""
    server.log.info(f"Workers changed from {old_value} to {new_value}")


# Preload app for faster worker startup (optional)
# Set to False to avoid issues with workers sharing state
preload_app = False

# Enable reuse of port for zero-downtime restarts (Linux only)
reuse_port = True if sys.platform == 'linux' else False

# Maximum number of pending connections
backlog = 2048

# Chdir to specified directory before apps loading
chdir = None

# Detach the main Gunicorn process from the controlling terminal
daemon = False

# Environment variables to set in the execution environment
raw_env = [
    f"PYTHONUNBUFFERED=1",
    f"LOG_LEVEL={os.getenv('LOG_LEVEL', 'INFO')}"
]

# SSL/TLS (not needed for Railway - they handle this at the edge)
keyfile = None
certfile = None
ssl_version = None
cert_reqs = None
ca_certs = None
suppress_ragged_eofs = True
do_handshake_on_connect = False
ciphers = None
