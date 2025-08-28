"""
Memory-Efficient Concurrent Processor Implementation - Sprint 2.5 Part D

Enterprise-grade concurrent processing with memory limits,
resource monitoring, and graceful degradation under load.

Following Interface-First Design methodology from planning/0_dev.md
"""
import asyncio
import psutil
from typing import List, Any, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gc
import threading

from ..interfaces.security import IConcurrentProcessor


class ResourceMonitor:
    """Monitor system resources during concurrent processing"""
    
    def __init__(self):
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        self.memory_warnings = []
    
    def check_memory(self) -> Dict[str, Any]:
        """Check current memory usage"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)
        
        return {
            "current_mb": round(current_memory, 2),
            "peak_mb": round(self.peak_memory, 2),
            "delta_mb": round(current_memory - self.initial_memory, 2),
            "system_available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2)
        }
    
    def is_memory_limit_exceeded(self, max_memory_mb: int) -> bool:
        """Check if memory limit is exceeded"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        return current_memory > max_memory_mb
    
    def add_warning(self, message: str):
        """Add memory warning"""
        self.memory_warnings.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
        })


class MemoryEfficientConcurrentProcessor(IConcurrentProcessor):
    """
    Memory-efficient concurrent processor implementation.
    
    Features:
    - Adaptive batch sizing based on memory usage
    - Resource monitoring and graceful degradation
    - Thread pool management with memory limits
    - Automatic garbage collection between batches
    - Circuit breaker pattern for overload protection
    """
    
    def __init__(
        self,
        max_workers: int = None,
        enable_monitoring: bool = True,
        gc_threshold: int = 100,
        circuit_breaker_threshold: int = 3
    ):
        """
        Initialize memory-efficient concurrent processor.
        
        Args:
            max_workers: Maximum number of worker threads
            enable_monitoring: Enable resource monitoring
            gc_threshold: Number of operations before garbage collection
            circuit_breaker_threshold: Number of failures before circuit breaker trips
        """
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 4) + 4)
        self.enable_monitoring = enable_monitoring
        self.gc_threshold = gc_threshold
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        # Performance tracking
        self._operation_count = 0
        self._failure_count = 0
        self._circuit_breaker_open = False
        self._last_gc_time = datetime.now(timezone.utc)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Resource monitoring
        self._resource_monitor = ResourceMonitor() if enable_monitoring else None
    
    async def _adaptive_batch_size(
        self, 
        total_items: int, 
        base_batch_size: int,
        max_memory_mb: int
    ) -> int:
        """
        Calculate adaptive batch size based on memory usage.
        
        Args:
            total_items: Total number of items to process
            base_batch_size: Base batch size
            max_memory_mb: Maximum memory limit
            
        Returns:
            Optimized batch size
        """
        if not self._resource_monitor:
            return base_batch_size
        
        memory_info = self._resource_monitor.check_memory()
        current_memory = memory_info["current_mb"]
        available_memory = max_memory_mb - current_memory
        
        # If we're close to memory limit, reduce batch size
        memory_usage_ratio = current_memory / max_memory_mb
        
        if memory_usage_ratio > 0.8:
            # High memory usage - reduce batch size significantly
            adaptive_size = max(1, base_batch_size // 4)
        elif memory_usage_ratio > 0.6:
            # Medium memory usage - reduce batch size moderately  
            adaptive_size = max(1, base_batch_size // 2)
        elif memory_usage_ratio > 0.4:
            # Low-medium memory usage - slight reduction
            adaptive_size = max(1, base_batch_size // 1.5)
        else:
            # Low memory usage - use full batch size
            adaptive_size = base_batch_size
        
        # Ensure we don't exceed available items
        return min(adaptive_size, total_items)
    
    async def _garbage_collection_if_needed(self):
        """Perform garbage collection if threshold reached"""
        if self._operation_count % self.gc_threshold == 0:
            if self._resource_monitor:
                memory_before = self._resource_monitor.check_memory()["current_mb"]
            
            # Force garbage collection
            collected = gc.collect()
            
            if self._resource_monitor:
                memory_after = self._resource_monitor.check_memory()["current_mb"]
                memory_freed = memory_before - memory_after
                
                if memory_freed > 1:  # More than 1MB freed
                    print(f"GC freed {memory_freed:.2f}MB, collected {collected} objects")
            
            self._last_gc_time = datetime.now(timezone.utc)
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should prevent processing"""
        with self._lock:
            if self._circuit_breaker_open:
                # Reset circuit breaker if enough time has passed
                time_since_last_gc = (datetime.utcnow() - self._last_gc_time).seconds
                if time_since_last_gc > 60:  # 1 minute cooldown
                    self._circuit_breaker_open = False
                    self._failure_count = 0
                    return False
                return True
            
            # Check if we should open circuit breaker
            if self._failure_count >= self.circuit_breaker_threshold:
                self._circuit_breaker_open = True
                if self._resource_monitor:
                    self._resource_monitor.add_warning("Circuit breaker opened due to failures")
                return True
            
            return False
    
    async def _process_batch(
        self, 
        batch: List[Any], 
        processor_func: Callable,
        **kwargs
    ) -> List[Any]:
        """
        Process a single batch with error handling.
        
        Args:
            batch: Batch of items to process
            processor_func: Function to process each item
            **kwargs: Additional arguments for processor function
            
        Returns:
            List of processed results
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Create thread pool executor for this batch
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
                # Submit all tasks
                futures = []
                for item in batch:
                    future = loop.run_in_executor(
                        executor, 
                        processor_func, 
                        item, 
                        **kwargs
                    )
                    futures.append(future)
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*futures, return_exceptions=True)
                
                # Separate successful results from exceptions
                processed_results = []
                for result in results:
                    if isinstance(result, Exception):
                        with self._lock:
                            self._failure_count += 1
                        print(f"Processing error: {result}")
                        processed_results.append(None)  # Or handle error appropriately
                    else:
                        processed_results.append(result)
                
                return processed_results
        
        except Exception as e:
            with self._lock:
                self._failure_count += 1
            raise e
    
    async def process_with_memory_limit(
        self,
        tasks: List[Any],
        max_memory_mb: int = 500,
        batch_size: int = 10,
        processor_func: Callable = None
    ) -> List[Any]:
        """
        Process tasks with memory limit and adaptive batching.
        
        Args:
            tasks: List of tasks to process
            max_memory_mb: Maximum memory limit in MB
            batch_size: Base batch size (will be adjusted adaptively)
            processor_func: Function to process each task
            
        Returns:
            List of processed results
        """
        if not tasks:
            return []
        
        # Check circuit breaker
        if await self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - processing temporarily disabled")
        
        if not processor_func:
            # Default processor function (identity function)
            processor_func = lambda x: x
        
        total_results = []
        processed_count = 0
        
        try:
            # Process tasks in adaptive batches
            while processed_count < len(tasks):
                # Check memory before each batch
                if self._resource_monitor and self._resource_monitor.is_memory_limit_exceeded(max_memory_mb):
                    # Force garbage collection
                    await self._garbage_collection_if_needed()
                    
                    # Check again after GC
                    if self._resource_monitor.is_memory_limit_exceeded(max_memory_mb):
                        self._resource_monitor.add_warning(
                            f"Memory limit exceeded: {self._resource_monitor.check_memory()['current_mb']}MB > {max_memory_mb}MB"
                        )
                        # Reduce batch size dramatically
                        batch_size = max(1, batch_size // 4)
                
                # Calculate adaptive batch size
                remaining_tasks = len(tasks) - processed_count
                current_batch_size = await self._adaptive_batch_size(
                    remaining_tasks, batch_size, max_memory_mb
                )
                
                # Extract current batch
                batch_end = min(processed_count + current_batch_size, len(tasks))
                current_batch = tasks[processed_count:batch_end]
                
                # Process batch
                batch_results = await self._process_batch(
                    current_batch, 
                    processor_func
                )
                
                total_results.extend(batch_results)
                processed_count = batch_end
                
                # Update operation count
                with self._lock:
                    self._operation_count += len(current_batch)
                
                # Garbage collection if needed
                await self._garbage_collection_if_needed()
                
                # Small delay to prevent CPU overload
                if len(current_batch) > 1:
                    await asyncio.sleep(0.01)  # 10ms delay
            
            return total_results
            
        except Exception as e:
            with self._lock:
                self._failure_count += 1
            
            if self._resource_monitor:
                self._resource_monitor.add_warning(f"Processing failed: {str(e)}")
            
            raise e
    
    async def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource usage statistics.
        
        Returns:
            Dictionary with resource usage statistics
        """
        stats = {
            "operation_count": self._operation_count,
            "failure_count": self._failure_count,
            "circuit_breaker_open": self._circuit_breaker_open,
            "max_workers": self.max_workers,
            "gc_threshold": self.gc_threshold
        }
        
        if self._resource_monitor:
            memory_info = self._resource_monitor.check_memory()
            stats.update({
                "memory": memory_info,
                "memory_warnings": self._resource_monitor.memory_warnings[-5:],  # Last 5 warnings
                "monitoring_enabled": True
            })
        else:
            stats["monitoring_enabled"] = False
        
        # Add system info
        stats["system"] = {
            "cpu_count": psutil.cpu_count(),
            "system_memory_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
            "system_memory_available_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2)
        }
        
        return stats
    
    async def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        with self._lock:
            self._circuit_breaker_open = False
            self._failure_count = 0
        
        if self._resource_monitor:
            self._resource_monitor.add_warning("Circuit breaker manually reset")
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """
        Get current system resource usage.
        
        Returns:
            System resource information
        """
        if self._resource_monitor:
            memory_info = self._resource_monitor.check_memory()
        else:
            memory_info = {
                "current_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
                "system_available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2)
            }
        
        return {
            "memory": memory_info,
            "cpu": {
                "count": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=0.1)
            },
            "system": {
                "total_memory_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                "available_memory_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2),
                "memory_usage_percent": psutil.virtual_memory().percent
            },
            "processor": {
                "max_workers": self.max_workers,
                "operation_count": self._operation_count,
                "failure_count": self._failure_count,
                "circuit_breaker_open": self._circuit_breaker_open
            }
        }
    
    async def should_throttle(self) -> bool:
        """
        Check if processing should be throttled due to resource constraints.
        
        Returns:
            True if throttling recommended
        """
        # Check circuit breaker
        if self._circuit_breaker_open:
            return True
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 85:  # High memory usage
            return True
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 90:  # High CPU usage
            return True
        
        # Check failure rate
        total_operations = self._operation_count
        if total_operations > 100:  # Only check after sufficient operations
            failure_rate = self._failure_count / total_operations
            if failure_rate > 0.1:  # More than 10% failure rate
                return True
        
        return False


# Specialized processors for universe calculations
class UniverseCalculationProcessor(MemoryEfficientConcurrentProcessor):
    """Specialized processor for universe screening and calculation tasks"""
    
    async def process_universe_screening(
        self,
        symbols: List[str],
        screening_func: Callable,
        max_memory_mb: int = 300,
        batch_size: int = 50
    ) -> List[Any]:
        """
        Process universe screening with optimized settings.
        
        Args:
            symbols: List of asset symbols to screen
            screening_func: Function to screen each symbol
            max_memory_mb: Memory limit for screening
            batch_size: Batch size for screening
            
        Returns:
            List of screening results
        """
        def screening_wrapper(symbol):
            """Wrapper to handle screening function calls"""
            try:
                return screening_func(symbol)
            except Exception as e:
                return {
                    "symbol": symbol,
                    "error": str(e),
                    "passed": False
                }
        
        return await self.process_with_memory_limit(
            tasks=symbols,
            max_memory_mb=max_memory_mb,
            batch_size=batch_size,
            processor_func=screening_wrapper
        )
    
    async def process_indicator_calculations(
        self,
        assets_data: List[Dict[str, Any]],
        indicator_func: Callable,
        max_memory_mb: int = 400,
        batch_size: int = 25
    ) -> List[Any]:
        """
        Process technical indicator calculations.
        
        Args:
            assets_data: List of asset data for indicator calculation
            indicator_func: Function to calculate indicators
            max_memory_mb: Memory limit for calculations
            batch_size: Batch size for calculations
            
        Returns:
            List of indicator calculation results
        """
        def indicator_wrapper(asset_data):
            """Wrapper to handle indicator calculations"""
            try:
                return indicator_func(asset_data)
            except Exception as e:
                return {
                    "symbol": asset_data.get("symbol", "unknown"),
                    "error": str(e),
                    "indicators": {}
                }
        
        return await self.process_with_memory_limit(
            tasks=assets_data,
            max_memory_mb=max_memory_mb,
            batch_size=batch_size,
            processor_func=indicator_wrapper
        )


def create_universe_processor(
    max_memory_mb: int = 500,
    max_workers: int = None,
    enable_monitoring: bool = True
) -> UniverseCalculationProcessor:
    """
    Factory function to create universe calculation processor.
    
    Args:
        max_memory_mb: Maximum memory limit
        max_workers: Maximum worker threads
        enable_monitoring: Enable resource monitoring
        
    Returns:
        Configured universe calculation processor
    """
    return UniverseCalculationProcessor(
        max_workers=max_workers,
        enable_monitoring=enable_monitoring
    )