import os

bind = f"0.0.0.0:{int(os.environ.get('PORT', '8000'))}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = 2
timeout = 30
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
