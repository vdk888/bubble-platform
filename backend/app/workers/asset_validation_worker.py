"""
Background asset validation worker implementation.

Following Phase 2 Step 5 requirements:
- Background asset validation with progress tracking
- Periodic validation refresh jobs
- Worker monitoring and health checks
- Bulk operations support with concurrency control
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from celery import Task
from celery.exceptions import Retry

from ..core.celery_app import celery_app
from ..core.database import SessionLocal
from ..core.config import settings
from ..services.asset_validation_service import AssetValidationService
from ..models.asset import Asset
import redis

logger = logging.getLogger(__name__)

# Redis client for progress tracking
redis_client = redis.from_url(settings.redis_url)

class CallbackTask(Task):
    """Base task with callback support for progress tracking"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} completed successfully")
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed: {exc}")
        # Update progress with failure status
        progress_key = f"task_progress:{task_id}"
        redis_client.hset(progress_key, mapping={
            'status': 'failed',
            'error': str(exc),
            'completed_at': datetime.utcnow().isoformat()
        })
        redis_client.expire(progress_key, 3600)  # Keep for 1 hour

@celery_app.task(base=CallbackTask, bind=True)
def validate_asset_background(self, symbol: str, user_id: str, force_refresh: bool = False):
    """
    Background asset validation task with progress tracking
    
    Args:
        symbol: Asset symbol to validate
        user_id: User requesting the validation
        force_refresh: Whether to bypass cache
        
    Returns:
        Dict with validation result and metadata
    """
    task_id = self.request.id
    progress_key = f"task_progress:{task_id}"
    
    try:
        # Initialize progress tracking
        redis_client.hset(progress_key, mapping={
            'status': 'started',
            'symbol': symbol,
            'user_id': user_id,
            'started_at': datetime.utcnow().isoformat(),
            'progress': 0
        })
        redis_client.expire(progress_key, 3600)
        
        # Create async context for validation service
        validation_service = AssetValidationService()
        
        # Update progress
        redis_client.hset(progress_key, 'progress', 25)
        
        # Run validation in sync context (Celery requirement)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Perform validation
            if force_refresh:
                result = loop.run_until_complete(
                    validation_service.validate_real_time(symbol)
                )
            else:
                result = loop.run_until_complete(
                    validation_service.validate_symbol_mixed_strategy(symbol)
                )
            
            # Update progress
            redis_client.hset(progress_key, 'progress', 75)
            
            # Store result in database if validation succeeded
            if result.success and result.data:
                db = SessionLocal()
                try:
                    # Update or create asset record
                    existing_asset = db.query(Asset).filter(Asset.symbol == symbol.upper()).first()
                    
                    if existing_asset:
                        existing_asset.is_validated = True
                        existing_asset.last_validated_at = datetime.now(timezone.utc)
                        existing_asset.validation_source = 'background_worker'
                        if result.data.name:
                            existing_asset.name = result.data.name
                        if result.data.sector:
                            existing_asset.sector = result.data.sector
                        if result.data.industry:
                            existing_asset.industry = result.data.industry
                    else:
                        # Create new asset
                        new_asset = Asset(
                            symbol=symbol.upper(),
                            name=result.data.name or symbol.upper(),
                            sector=result.data.sector,
                            industry=result.data.industry,
                            is_validated=True,
                            last_validated_at=datetime.now(timezone.utc),
                            validation_source='background_worker'
                        )
                        db.add(new_asset)
                    
                    db.commit()
                    logger.info(f"Background validation completed for {symbol}")
                    
                finally:
                    db.close()
            
            # Complete progress tracking
            redis_client.hset(progress_key, mapping={
                'status': 'completed',
                'progress': 100,
                'result': json.dumps({
                    'success': result.success,
                    'symbol': symbol,
                    'validated': result.success and result.data is not None,
                    'message': result.message
                }),
                'completed_at': datetime.utcnow().isoformat()
            })
            
            return {
                'task_id': task_id,
                'symbol': symbol,
                'success': result.success,
                'validated': result.success and result.data is not None,
                'message': result.message
            }
            
        finally:
            loop.close()
            
    except Exception as exc:
        # Handle task failure
        logger.error(f"Background validation failed for {symbol}: {exc}")
        
        redis_client.hset(progress_key, mapping={
            'status': 'failed',
            'progress': 0,
            'error': str(exc),
            'completed_at': datetime.utcnow().isoformat()
        })
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            logger.info(f"Retrying validation for {symbol} in {countdown}s")
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # Max retries reached
            return {
                'task_id': task_id,
                'symbol': symbol,
                'success': False,
                'error': str(exc),
                'max_retries_reached': True
            }

@celery_app.task(base=CallbackTask, bind=True)
def bulk_validate_assets(self, symbols: List[str], user_id: str, batch_size: int = 10):
    """
    Bulk asset validation with progress tracking and concurrency control
    
    Args:
        symbols: List of asset symbols to validate
        user_id: User requesting the validation
        batch_size: Number of symbols to process per batch
        
    Returns:
        Dict with bulk validation results
    """
    task_id = self.request.id
    progress_key = f"bulk_progress:{task_id}"
    
    try:
        # Initialize progress tracking
        total_symbols = len(symbols)
        redis_client.hset(progress_key, mapping={
            'status': 'started',
            'total_symbols': total_symbols,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'user_id': user_id,
            'started_at': datetime.utcnow().isoformat(),
            'progress': 0
        })
        redis_client.expire(progress_key, 7200)  # Keep for 2 hours
        
        results = []
        processed = 0
        successful = 0
        failed = 0
        
        # Process in batches to avoid overwhelming providers
        for i in range(0, total_symbols, batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            # Process batch with Celery group for parallel execution
            from celery import group
            
            batch_tasks = group(
                validate_asset_background.s(symbol, user_id, False) 
                for symbol in batch_symbols
            )
            
            # Execute batch and wait for results
            batch_result = batch_tasks.apply()
            
            # Collect results
            for result in batch_result.get(timeout=300):  # 5 minute timeout per batch
                results.append(result)
                processed += 1
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
            
            # Update progress
            progress_percent = (processed / total_symbols) * 100
            redis_client.hset(progress_key, mapping={
                'processed': processed,
                'successful': successful,
                'failed': failed,
                'progress': progress_percent
            })
            
            logger.info(f"Bulk validation progress: {processed}/{total_symbols} ({progress_percent:.1f}%)")
        
        # Complete progress tracking
        redis_client.hset(progress_key, mapping={
            'status': 'completed',
            'progress': 100,
            'completed_at': datetime.utcnow().isoformat()
        })
        
        return {
            'task_id': task_id,
            'total_symbols': total_symbols,
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'results': results,
            'completion_rate': (successful / total_symbols * 100) if total_symbols > 0 else 0
        }
        
    except Exception as exc:
        logger.error(f"Bulk validation failed: {exc}")
        
        redis_client.hset(progress_key, mapping={
            'status': 'failed',
            'error': str(exc),
            'completed_at': datetime.utcnow().isoformat()
        })
        
        raise

@celery_app.task
def refresh_stale_validations():
    """
    Periodic task to refresh stale asset validations
    
    Runs every hour to refresh validations older than 24 hours
    """
    try:
        db = SessionLocal()
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Find assets with stale validations
        stale_assets = db.query(Asset).filter(
            Asset.is_validated == True,
            Asset.last_validated_at < cutoff_time
        ).limit(50).all()  # Limit to 50 per run to avoid overload
        
        if not stale_assets:
            logger.info("No stale validations found")
            return {'refreshed': 0, 'message': 'No stale validations found'}
        
        # Queue background validation for stale assets
        symbols_to_refresh = [asset.symbol for asset in stale_assets]
        
        # Use Celery group for parallel processing
        from celery import group
        
        refresh_tasks = group(
            validate_asset_background.s(symbol, 'system', True)  # Force refresh
            for symbol in symbols_to_refresh
        )
        
        # Execute refresh tasks
        refresh_tasks.apply_async()
        
        logger.info(f"Queued {len(symbols_to_refresh)} assets for validation refresh")
        
        return {
            'refreshed': len(symbols_to_refresh),
            'symbols': symbols_to_refresh,
            'message': f'Queued {len(symbols_to_refresh)} assets for refresh'
        }
        
    except Exception as e:
        logger.error(f"Stale validation refresh failed: {e}")
        return {'error': str(e)}
    finally:
        if 'db' in locals():
            db.close()

@celery_app.task  
def cleanup_expired_results():
    """
    Cleanup expired task results and progress tracking data
    
    Runs every 6 hours to clean up Redis keys
    """
    try:
        # Clean up expired progress keys
        pattern_keys = ['task_progress:*', 'bulk_progress:*', 'background_validation_queue:*']
        cleaned_count = 0
        
        for pattern in pattern_keys:
            keys = redis_client.keys(pattern)
            
            for key in keys:
                # Check if key has TTL, if not, set one
                ttl = redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    redis_client.expire(key, 3600)  # Set 1 hour expiration
                    cleaned_count += 1
        
        # Clean up old validation cache entries
        validation_keys = redis_client.keys('asset_validation:*')
        for key in validation_keys:
            if redis_client.ttl(key) == -1:
                redis_client.expire(key, 3600)  # Set 1 hour expiration
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} expired Redis keys")
        
        return {
            'cleaned_keys': cleaned_count,
            'message': f'Cleaned up {cleaned_count} expired keys'
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {'error': str(e)}

def get_task_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get progress information for a background task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dictionary with progress information or None if not found
    """
    try:
        # Check different progress key patterns
        for pattern in ['task_progress:', 'bulk_progress:']:
            progress_key = f"{pattern}{task_id}"
            
            if redis_client.exists(progress_key):
                progress_data = redis_client.hgetall(progress_key)
                
                # Convert bytes to strings
                return {
                    k.decode('utf-8') if isinstance(k, bytes) else k: 
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in progress_data.items()
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting task progress for {task_id}: {e}")
        return None