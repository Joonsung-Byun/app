import time
import logging
from langchain.callbacks.base import BaseCallbackHandler
from backend.utils.tool_timings import record_tool_timing

logger = logging.getLogger(__name__)


class ToolTimingCallbackHandler(BaseCallbackHandler):
    """Record start/end timestamps for each tool call."""

    def __init__(self):
        super().__init__()
        self._starts = {}

    def on_tool_start(self, serialized, input_str, **kwargs):
        run_id = kwargs.get("run_id")
        tool_name = serialized.get("name") if isinstance(serialized, dict) else None
        conversation_id = None
        try:
            if isinstance(input_str, dict):
                conversation_id = input_str.get("conversation_id")
        except Exception:
            pass
        self._starts[run_id] = (time.time(), tool_name, conversation_id)
        logger.debug(f"[ToolTiming] start tool={tool_name} run_id={run_id} conv={conversation_id}")

    def on_tool_end(self, output, **kwargs):
        run_id = kwargs.get("run_id")
        start, tool_name, conversation_id = self._starts.pop(run_id, (None, None, None))
        if start is None:
            return
        duration = time.time() - start
        record_tool_timing(tool=tool_name or "unknown_tool", duration=duration, conversation_id=conversation_id)
        logger.debug(f"[ToolTiming] end tool={tool_name} run_id={run_id} conv={conversation_id} duration={duration:.3f}s")
