"""
Gunicorn configuration for Railway deployment
Optimized for production with reduced workers and proper logging
"""

import multiprocessing
import os
import sys
import logging.config

# Validate critical environment variables
def validate_environment():
    """Validate that required environment variables are present"""
    critical_vars = []

    # Check PORT (Railway should always provide this)
    port = os.getenv('PORT', '8080')
    if not port.isdigit():
        raise ValueError(f"Invalid PORT value: {port}. Must be a number.")

    # Log environment info for debugging
    print(f"[Gunicorn Config] Starting with PORT={port}")
    print(f"[Gunicorn Config] Workers: {os.getenv('WORKERS', 'auto')}")
    print(f"[Gunicorn Config] Log Level: {os.getenv('LOG_LEVEL', 'info')}")
    print(f"[Gunicorn Config] Python Path: {sys.executable}")
    print(f"[Gunicorn Config] Working Directory: {os.getcwd()}")

    return port

# Validate environment on import
try:
    validated_port = validate_environment()
except Exception as e:
    print(f"[Gunicorn Config ERROR] Configuration validation failed: {e}", file=sys.stderr)
    sys.exit(1)

# Server socket
bind = f"0.0.0.0:{validated_port}"

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
# Custom logging to properly route INFO to stdout and ERROR to stderr
# This fixes the issue where all Gunicorn logs were going to stderr

# Configure Python logging to properly separate stdout and stderr
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %z'
        },
        'access': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'stdout_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
            'level': 'DEBUG'
        },
        'stderr_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stderr',
            'level': 'WARNING'
        },
        'access_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'access',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'gunicorn': {
            'level': 'DEBUG',
            'handlers': ['stdout_handler', 'stderr_handler'],
            'propagate': False
        },
        'gunicorn.error': {
            'level': 'DEBUG',
            'handlers': ['stdout_handler', 'stderr_handler'],
            'propagate': False
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['access_handler'],
            'propagate': False
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['stdout_handler', 'stderr_handler'],
            'propagate': False
        },
        'uvicorn.error': {
            'level': 'INFO',
            'handlers': ['stdout_handler', 'stderr_handler'],
            'propagate': False
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': ['access_handler'],
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['stdout_handler', 'stderr_handler']
    }
}

# Apply the custom logging configuration
logging.config.dictConfig(logconfig_dict)

# Still set these for Gunicorn's internal use
accesslog = '-'  # stdout
errorlog = '-'   # stderr (for actual errors only now)
loglevel = os.getenv('LOG_LEVEL', 'info').lower()

# Access log format with timing information
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("=" * 60)
    server.log.info("Gunicorn master process starting")
    server.log.info(f"Configuration: {workers} workers, {worker_class} worker class")
    server.log.info(f"Binding to {bind}")
    server.log.info(f"Timeout: {timeout}s, Graceful timeout: {graceful_timeout}s")
    server.log.info(f"Current working directory: {os.getcwd()}")
    server.log.info(f"Python executable: {sys.executable}")
    server.log.info(f"Python version: {sys.version}")

    # Verify critical paths exist
    app_path = os.path.join(os.getcwd(), 'app', 'main.py')
    if os.path.exists(app_path):
        server.log.info(f"✓ App module found at: {app_path}")
    else:
        server.log.warning(f"⚠ App module not found at expected path: {app_path}")

    # Check for ANTHROPIC_API_KEY (don't log the value)
    if os.getenv('ANTHROPIC_API_KEY'):
        server.log.info("✓ ANTHROPIC_API_KEY is set")
    else:
        server.log.warning("⚠ ANTHROPIC_API_KEY is not set - AI features may not work")

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
# Removed chdir = None to fix Railway deployment error
# When chdir is None, gunicorn's internal validation fails
# Since Procfile already does 'cd backend', we don't need this

# Detach the main Gunicorn process from the controlling terminal
daemon = False

# Environment variables to set in the execution environment
raw_env = [
    f"PYTHONUNBUFFERED=1",
    f"LOG_LEVEL={os.getenv('LOG_LEVEL', 'INFO')}"
]

# SSL/TLS Configuration
# Railway handles SSL/TLS termination at the edge (load balancer level)
# so these settings are not needed for Railway deployments.
# We only keep the minimal required SSL settings that accept None values.
keyfile = None
certfile = None
# Removed ssl_version - deprecated parameter that causes warnings
# Removed cert_reqs - must be an integer (ssl.CERT_NONE/OPTIONAL/REQUIRED), not None
ca_certs = None
suppress_ragged_eofs = True
do_handshake_on_connect = False
ciphers = None
