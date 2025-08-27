"""
Universe Scheduler - Evolution Module Component

Handles scheduling and automation of universe updates with support for
multiple frequencies, timezone management, and execution tracking.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import uuid


class ScheduleFrequency(str, Enum):
    """Supported scheduling frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"  
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class ScheduleStatus(str, Enum):
    """Schedule execution status"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScheduleExecution:
    """Record of a scheduled execution"""
    id: str
    schedule_id: str
    planned_date: datetime
    actual_date: Optional[datetime]
    status: ScheduleStatus
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "planned_date": self.planned_date.isoformat(),
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "status": self.status.value,
            "result": self.result,
            "error": self.error
        }


@dataclass
class Schedule:
    """Universe update schedule configuration"""
    id: str
    universe_id: str
    frequency: ScheduleFrequency
    start_date: date
    end_date: Optional[date]
    execution_time: str  # HH:MM format
    timezone_name: str
    status: ScheduleStatus
    created_at: datetime
    updated_at: datetime
    executions: List[ScheduleExecution]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "universe_id": self.universe_id,
            "frequency": self.frequency.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "execution_time": self.execution_time,
            "timezone_name": self.timezone_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "executions": [ex.to_dict() for ex in self.executions],
            "metadata": self.metadata,
            "next_execution": self.get_next_execution_date().isoformat() if self.get_next_execution_date() else None
        }
    
    def get_next_execution_date(self) -> Optional[datetime]:
        """Calculate the next scheduled execution date"""
        if self.status != ScheduleStatus.ACTIVE:
            return None
        
        now = datetime.now(timezone.utc)
        current_date = max(self.start_date, now.date())
        
        # If we have a specific end date and we've passed it, no next execution
        if self.end_date and current_date > self.end_date:
            return None
        
        # Parse execution time
        try:
            hour, minute = map(int, self.execution_time.split(':'))
        except ValueError:
            hour, minute = 9, 0  # Default to 9:00 AM
        
        # Calculate next execution based on frequency
        next_date = current_date
        
        if self.frequency == ScheduleFrequency.DAILY:
            # If today's execution time has passed, schedule for tomorrow
            today_execution = datetime.combine(current_date, datetime.min.time()).replace(
                hour=hour, minute=minute, tzinfo=timezone.utc
            )
            if now >= today_execution:
                next_date = current_date + timedelta(days=1)
                
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Find next weekly execution
            days_ahead = 7 - ((current_date.weekday() + 1) % 7)  # Next week same day
            if days_ahead == 0:  # Today is the day
                today_execution = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=hour, minute=minute, tzinfo=timezone.utc
                )
                if now >= today_execution:
                    days_ahead = 7
            next_date = current_date + timedelta(days=days_ahead)
            
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Next month same day
            if current_date.month == 12:
                next_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_date = current_date.replace(month=current_date.month + 1)
                
        elif self.frequency == ScheduleFrequency.QUARTERLY:
            # Next quarter
            new_month = current_date.month + 3
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            next_date = current_date.replace(year=new_year, month=new_month)
        
        return datetime.combine(next_date, datetime.min.time()).replace(
            hour=hour, minute=minute, tzinfo=timezone.utc
        )


class UniverseScheduler:
    """
    Universe update scheduler with support for multiple frequencies
    and automated execution tracking.
    """
    
    def __init__(self):
        self.schedules: Dict[str, Schedule] = {}
        
    def schedule_monthly_updates(
        self,
        universe_id: str,
        start_date: date,
        execution_time: str = "09:00",
        end_date: Optional[date] = None,
        timezone_name: str = "UTC"
    ) -> Schedule:
        """
        Schedule monthly universe updates.
        
        Args:
            universe_id: UUID of universe to schedule updates for
            start_date: Date to start scheduling from
            execution_time: Time of day to execute (HH:MM format)
            end_date: Optional end date for schedule
            timezone_name: Timezone for execution time
            
        Returns:
            Schedule object with configuration
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        schedule = Schedule(
            id=schedule_id,
            universe_id=universe_id,
            frequency=ScheduleFrequency.MONTHLY,
            start_date=start_date,
            end_date=end_date,
            execution_time=execution_time,
            timezone_name=timezone_name,
            status=ScheduleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            executions=[],
            metadata={
                "auto_created": True,
                "scheduling_method": "monthly_updates"
            }
        )
        
        self.schedules[schedule_id] = schedule
        return schedule
    
    def schedule_quarterly_updates(
        self,
        universe_id: str,
        start_date: date,
        execution_time: str = "09:00",
        end_date: Optional[date] = None,
        timezone_name: str = "UTC"
    ) -> Schedule:
        """
        Schedule quarterly universe updates.
        
        Args:
            universe_id: UUID of universe to schedule updates for
            start_date: Date to start scheduling from
            execution_time: Time of day to execute (HH:MM format)
            end_date: Optional end date for schedule
            timezone_name: Timezone for execution time
            
        Returns:
            Schedule object with configuration
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        schedule = Schedule(
            id=schedule_id,
            universe_id=universe_id,
            frequency=ScheduleFrequency.QUARTERLY,
            start_date=start_date,
            end_date=end_date,
            execution_time=execution_time,
            timezone_name=timezone_name,
            status=ScheduleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            executions=[],
            metadata={
                "auto_created": True,
                "scheduling_method": "quarterly_updates"
            }
        )
        
        self.schedules[schedule_id] = schedule
        return schedule
    
    def create_custom_schedule(
        self,
        universe_id: str,
        frequency: ScheduleFrequency,
        start_date: date,
        execution_time: str = "09:00",
        end_date: Optional[date] = None,
        timezone_name: str = "UTC",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schedule:
        """
        Create custom schedule with specified parameters.
        
        Args:
            universe_id: UUID of universe to schedule updates for
            frequency: Scheduling frequency
            start_date: Date to start scheduling from
            execution_time: Time of day to execute (HH:MM format)
            end_date: Optional end date for schedule
            timezone_name: Timezone for execution time
            metadata: Additional metadata for the schedule
            
        Returns:
            Schedule object with configuration
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        schedule = Schedule(
            id=schedule_id,
            universe_id=universe_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            execution_time=execution_time,
            timezone_name=timezone_name,
            status=ScheduleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            executions=[],
            metadata=metadata or {}
        )
        
        self.schedules[schedule_id] = schedule
        return schedule
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get schedule by ID"""
        return self.schedules.get(schedule_id)
    
    def get_schedules_for_universe(self, universe_id: str) -> List[Schedule]:
        """Get all schedules for a specific universe"""
        return [
            schedule for schedule in self.schedules.values()
            if schedule.universe_id == universe_id
        ]
    
    def get_due_schedules(self, check_time: Optional[datetime] = None) -> List[Schedule]:
        """
        Get schedules that are due for execution.
        
        Args:
            check_time: Time to check against (defaults to now)
            
        Returns:
            List of schedules due for execution
        """
        if check_time is None:
            check_time = datetime.now(timezone.utc)
        
        due_schedules = []
        
        for schedule in self.schedules.values():
            if schedule.status != ScheduleStatus.ACTIVE:
                continue
                
            next_execution = schedule.get_next_execution_date()
            if next_execution and next_execution <= check_time:
                due_schedules.append(schedule)
        
        return due_schedules
    
    def record_execution(
        self,
        schedule_id: str,
        planned_date: datetime,
        actual_date: datetime,
        status: ScheduleStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> ScheduleExecution:
        """
        Record a schedule execution.
        
        Args:
            schedule_id: ID of executed schedule
            planned_date: Originally planned execution time
            actual_date: Actual execution time
            status: Execution status
            result: Optional execution result data
            error: Optional error message if execution failed
            
        Returns:
            ScheduleExecution object
        """
        execution = ScheduleExecution(
            id=str(uuid.uuid4()),
            schedule_id=schedule_id,
            planned_date=planned_date,
            actual_date=actual_date,
            status=status,
            result=result,
            error=error
        )
        
        if schedule_id in self.schedules:
            self.schedules[schedule_id].executions.append(execution)
            self.schedules[schedule_id].updated_at = datetime.now(timezone.utc)
        
        return execution
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].status = ScheduleStatus.PAUSED
            self.schedules[schedule_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].status = ScheduleStatus.ACTIVE
            self.schedules[schedule_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return True
        return False
    
    def get_execution_history(
        self,
        schedule_id: str,
        limit: Optional[int] = None
    ) -> List[ScheduleExecution]:
        """
        Get execution history for a schedule.
        
        Args:
            schedule_id: Schedule to get history for
            limit: Optional limit on number of executions to return
            
        Returns:
            List of ScheduleExecution objects, newest first
        """
        if schedule_id not in self.schedules:
            return []
        
        executions = sorted(
            self.schedules[schedule_id].executions,
            key=lambda x: x.actual_date or x.planned_date,
            reverse=True
        )
        
        if limit:
            executions = executions[:limit]
            
        return executions
    
    def get_schedule_statistics(self, schedule_id: str) -> Dict[str, Any]:
        """
        Get statistics for a schedule.
        
        Args:
            schedule_id: Schedule to get statistics for
            
        Returns:
            Dictionary with schedule statistics
        """
        if schedule_id not in self.schedules:
            return {}
        
        schedule = self.schedules[schedule_id]
        executions = schedule.executions
        
        if not executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_delay": 0.0,
                "last_execution": None,
                "next_execution": schedule.get_next_execution_date().isoformat() if schedule.get_next_execution_date() else None
            }
        
        # Calculate statistics
        successful_executions = [ex for ex in executions if ex.status == ScheduleStatus.COMPLETED]
        success_rate = len(successful_executions) / len(executions) if executions else 0.0
        
        # Calculate average delay (positive = late, negative = early)
        delays = []
        for execution in executions:
            if execution.actual_date and execution.planned_date:
                delay_seconds = (execution.actual_date - execution.planned_date).total_seconds()
                delays.append(delay_seconds)
        
        average_delay = sum(delays) / len(delays) if delays else 0.0
        
        # Get last execution
        last_execution = max(executions, key=lambda x: x.actual_date or x.planned_date)
        
        return {
            "total_executions": len(executions),
            "successful_executions": len(successful_executions),
            "failed_executions": len([ex for ex in executions if ex.status == ScheduleStatus.FAILED]),
            "success_rate": success_rate,
            "average_delay_seconds": average_delay,
            "last_execution": last_execution.to_dict(),
            "next_execution": schedule.get_next_execution_date().isoformat() if schedule.get_next_execution_date() else None,
            "schedule_age_days": (datetime.now(timezone.utc) - schedule.created_at).days
        }