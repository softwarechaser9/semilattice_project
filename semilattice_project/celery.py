"""
Celery configuration for asynchronous task processing
Supports both local development (Redis) and Render deployment
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'semilattice_project.settings')

# Create Celery app
app = Celery('semilattice_project')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Optional: Configure for better error handling
app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # Soft limit at 25 minutes
    worker_prefetch_multiplier=1,  # Only fetch one task at a time (better for long tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)
)

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')
