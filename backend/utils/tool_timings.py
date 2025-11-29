"""Simple in-process tool timing recorder."""

import time
import threading
from typing import Dict, Any, List

_lock = threading.Lock()
_records: List[Dict[str, Any]] = []
_enabled = True


def enable_tool_timing():
    global _enabled
    _enabled = True


def disable_tool_timing():
    global _enabled
    _enabled = False


def clear_tool_timings():
    with _lock:
        _records.clear()


def record_tool_timing(tool: str, duration: float, conversation_id: str = None):
    """Store a single timing record."""
    if not _enabled:
        return
    with _lock:
        _records.append({
            "tool": tool,
            "duration": duration,
            "conversation_id": conversation_id,
            "timestamp": time.time(),
        })


def get_and_reset() -> List[Dict[str, Any]]:
    """Return all timing records and clear the buffer."""
    with _lock:
        data = list(_records)
        _records.clear()
        return data


def timed_call(tool: str, conversation_id: str, func, *args, **kwargs):
    """Wrapper to measure duration of a tool function."""
    start = time.time()
    try:
        return func(*args, **kwargs)
    finally:
        duration = time.time() - start
        record_tool_timing(tool=tool, duration=duration, conversation_id=conversation_id)
