"""
Schedule configuration helpers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, time


class ScheduleType(Enum):
    """Schedule type enumeration"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    MANUAL = "manual"


@dataclass
class ScheduleConfig:
    """Helper for creating schedule configurations"""

    @staticmethod
    def once(run_at: datetime) -> Dict[str, Any]:
        """Run once at specific time"""
        return {
            'type': ScheduleType.ONCE.value,
            'config': {'run_at': run_at.isoformat()}
        }

    @staticmethod
    def interval(
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run at regular intervals"""
        config = {}
        if minutes:
            config['interval_minutes'] = minutes
        if hours:
            config['interval_hours'] = hours
        if days:
            config['interval_days'] = days

        return {
            'type': ScheduleType.INTERVAL.value,
            'config': config
        }

    @staticmethod
    def daily(hour: int = 0, minute: int = 0) -> Dict[str, Any]:
        """Run daily at specific time"""
        return {
            'type': ScheduleType.CRON.value,
            'config': {
                'hour': hour,
                'minute': minute
            }
        }

    @staticmethod
    def weekly(day_of_week: int, hour: int = 0, minute: int = 0) -> Dict[str, Any]:
        """
        Run weekly on specific day.

        Args:
            day_of_week: 0=Monday, 6=Sunday
            hour: Hour (0-23)
            minute: Minute (0-59)
        """
        return {
            'type': ScheduleType.CRON.value,
            'config': {
                'day_of_week': day_of_week,
                'hour': hour,
                'minute': minute
            }
        }

    @staticmethod
    def manual() -> Dict[str, Any]:
        """Manual execution only (no automatic scheduling)"""
        return {
            'type': ScheduleType.MANUAL.value,
            'config': {}
        }
