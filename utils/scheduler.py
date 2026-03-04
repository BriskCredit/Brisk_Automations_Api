from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional
from utils.logger import get_logger

logger = get_logger("app.scheduler")


class SchedulerService:
    """
    Singleton scheduler service for managing cron jobs.
    """
    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._scheduler = AsyncIOScheduler()
        return cls._instance

    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def start(self):
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler shut down")

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: str = "*",
        minute: str = "0",
        second: str = "0",
        day: str = "*",
        day_of_week: str = "*",
        month: str = "*",
        timezone: str = None,
        **kwargs
    ):
        """
        Add a cron job to the scheduler.
        
        Args:
            func: The function to execute
            job_id: Unique identifier for the job
            hour: Hour field (0-23 or *)
            minute: Minute field (0-59 or *)
            second: Second field (0-59 or *)
            day: Day of month field (1-31 or *)
            day_of_week: Day of week field (0-6 or mon-sun or *)
            month: Month field (1-12 or *)
            timezone: Timezone string (e.g., "Africa/Nairobi")
            **kwargs: Additional arguments to pass to add_job
        """
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            second=second,
            day=day,
            day_of_week=day_of_week,
            month=month,
            timezone=timezone
        )
        
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        tz_info = f" tz={timezone}" if timezone else ""
        logger.info(f"Cron job '{job_id}' added: {hour}:{minute}:{second} day={day} dow={day_of_week}{tz_info}")

    def remove_job(self, job_id: str):
        """Remove a job by ID."""
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Job '{job_id}' removed")
        except Exception as e:
            logger.warning(f"Failed to remove job '{job_id}': {e}")

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self._scheduler.get_jobs()


# Global scheduler instance
scheduler_service = SchedulerService()
