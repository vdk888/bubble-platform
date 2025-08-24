"""
Celery application configuration for background processing.

Following Phase 2 Step 5 requirements:
- Background asset validation workers
- Periodic validation refresh jobs
- Progress tracking for bulk operations
- Worker monitoring and health checks
"""

from celery import Celery
from celery.signals import setup_logging
from .config import settings
import logging

# Create Celery instance
celery_app = Celery(
    "bubble-platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.workers.asset_validation_worker']
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'app.workers.asset_validation_worker.validate_asset_background': {'queue': 'validation'},
        'app.workers.asset_validation_worker.refresh_stale_validations': {'queue': 'maintenance'},
        'app.workers.asset_validation_worker.bulk_validate_assets': {'queue': 'bulk_validation'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # One task at a time for better concurrency control
    task_acks_late=True,  # Acknowledge task after completion
    worker_disable_rate_limits=False,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
    },
    
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Retry settings
    task_default_retry_delay=60,  # 60 seconds
    task_max_retries=3,
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'refresh-stale-validations': {
            'task': 'app.workers.asset_validation_worker.refresh_stale_validations',
            'schedule': 3600.0,  # Every hour
            'options': {'queue': 'maintenance'}
        },
        'cleanup-expired-results': {
            'task': 'app.workers.asset_validation_worker.cleanup_expired_results',
            'schedule': 21600.0,  # Every 6 hours
            'options': {'queue': 'maintenance'}
        },
    },
    beat_schedule_filename='/tmp/celerybeat-schedule',
)

# Configure logging for Celery workers
@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers"""
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'loggers': {
            'celery': {
                'level': 'INFO',
                'handlers': ['console'],
            },
            'app.workers': {
                'level': 'INFO',
                'handlers': ['console'],
            },
        },
    })

# Health check for Celery workers
def get_worker_status():
    """Get Celery worker status for health monitoring"""
    try:
        # Get active workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active_tasks = inspect.active()
        
        if not stats:
            return {
                'status': 'unhealthy',
                'workers': 0,
                'active_tasks': 0,
                'message': 'No workers available'
            }
        
        total_active_tasks = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        
        return {
            'status': 'healthy',
            'workers': len(stats),
            'active_tasks': total_active_tasks,
            'worker_stats': stats
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'workers': 0,
            'active_tasks': 0,
            'message': str(e)
        }