# gunicorn.conf.py
timeout = 300  # 5 minutes (increased from 30 seconds)
workers = 1
threads = 2
worker_class = 'sync'
keepalive = 5
max_requests = 100
max_requests_jitter = 20
