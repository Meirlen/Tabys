"""
Publication scheduling configuration for news articles.

This module defines the publication time slots and their minimum requirements.
Configuration is designed to be easily modifiable without code changes.
"""

from typing import List, Dict
from datetime import time

# Publication time slots with minimum required news count
# Format: {"time": "HH:MM", "min": <minimum_news_count>}
PUBLICATION_SLOTS: List[Dict] = [
    {"time": "11:00", "min": 3},
    {"time": "13:00", "min": 4},
    {"time": "18:00", "min": 3},
    {"time": "21:00", "min": 4},
]

# Time window in minutes for grouping news into slots
# News scheduled within this window of a slot time is considered part of that slot
SLOT_WINDOW_MINUTES: int = 30

# Scheduler configuration
SCHEDULER_INTERVAL_MINUTES: int = 1  # How often the scheduler runs

# Get slot time objects for easier comparison
def get_slot_times() -> List[time]:
    """Return list of slot times as time objects"""
    result = []
    for slot in PUBLICATION_SLOTS:
        hour, minute = map(int, slot["time"].split(":"))
        result.append(time(hour=hour, minute=minute))
    return result

def get_slot_config(slot_time: str) -> Dict:
    """Get configuration for a specific slot time"""
    for slot in PUBLICATION_SLOTS:
        if slot["time"] == slot_time:
            return slot
    return None

def get_total_minimum_news() -> int:
    """Get total minimum required news across all slots"""
    return sum(slot["min"] for slot in PUBLICATION_SLOTS)
