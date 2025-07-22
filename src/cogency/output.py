"""Centralized output management for Cogency agents with tracing and formatting"""

from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from cogency.utils import summarize_tool_result, tool_emoji


class Output:
    """Single source of truth for all agent output with tracing and formatting"""

    def __init__(
        self,
        trace: bool = False,
        verbose: bool = True,
        callback: Optional[Union[Callable[[str], None], Callable[[str], Awaitable[None]]]] = None,
    ):
        """Initialize output manager with tracing and verbosity settings"""
        self.tracing = trace
        self.verbose = verbose
        self.callback = callback
        self.entries: List[Dict[str, Any]] = []  # Collected traces

    async def trace(self, message: str, node: Optional[str] = None, **kwargs):
        """Record trace entries for debugging and stream to callback if available"""
        if not self.tracing:
            return

        # Store trace entry
        entry = {"type": "trace", "message": message, "node": node, **kwargs}
        self.entries.append(entry)

        # Stream if callback available
        if self.callback:
            # Split on | for separate trace lines
            parts = message.split(" | ")
            for part in parts:
                if node:
                    formatted = f"\n    🔧 [{node}] {part.strip()}"
                else:
                    formatted = f"\n    🔧 {part.strip()}"
                await self.callback(formatted)

    async def update(self, message: str, type: str = "info", **kwargs):
        """Display user progress updates - always shown, left-aligned, no emoji"""
        if not self.callback:
            return

        # Updates are left-aligned, always shown, no emoji
        formatted = f"\n{message}"
        await self.callback(formatted)

    async def log_tool(self, tool_name: str, result: Any, success: bool = True):
        """Log tool execution with status emoji and formatted result"""
        if not self.verbose or not self.callback:
            return

        icon = tool_emoji(tool_name)
        status = "✅" if success else "❌"
        formatted_result = summarize_tool_result(result) if result else ""
        formatted = f"{icon} {tool_name} → {status} {formatted_result}"
        await self.callback(formatted)


    def tool_emoji(self, tool_name: str) -> str:
        """Get tool-specific emoji for display"""
        return tool_emoji(tool_name)

    def traces(self) -> List[Dict[str, Any]]:
        """Get copy of all collected trace entries"""
        return self.entries.copy()

    def reset_traces(self) -> None:
        """Clear all trace entries"""
        self.entries.clear()

    async def send(self, message_type: str, content: str, node: Optional[str] = None, **kwargs):
        """Route messages to appropriate output methods by type"""
        if message_type == "trace":
            await self.trace(content, node=node, **kwargs)
        elif message_type == "update":
            await self.update(content, type="info", **kwargs)
        elif message_type == "tool_execution":
            # Handle tool execution results
            tool_name = kwargs.get("tool_name", "unknown")
            success = kwargs.get("success", True)
            await self.log_tool(tool_name, content, success=success)
        else:
            # Default to update for unknown types
            await self.update(content, type=message_type, **kwargs)
