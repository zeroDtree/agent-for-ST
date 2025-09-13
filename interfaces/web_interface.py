"""
Web Interface - Provides web confirmation functionality without circular dependencies
"""

import threading
from typing import Callable, Dict, Optional

from utils.logger import get_logger

logger = get_logger(name=__name__)


class WebConfirmationInterface:
    """Interface for web confirmation functionality"""

    def __init__(self):
        self._pending_confirmations: Optional[Dict] = None
        self._send_sse_event: Optional[Callable] = None

    def set_dependencies(self, pending_confirmations: Dict, send_sse_event: Callable):
        """Inject web server dependencies"""
        self._pending_confirmations = pending_confirmations
        self._send_sse_event = send_sse_event
        logger.info("Web confirmation interface dependencies injected successfully")

    def is_available(self) -> bool:
        """Check if web interface is available"""
        return self._pending_confirmations is not None and self._send_sse_event is not None

    def request_confirmation(self, session_id: str, command_info: str, tool_name: str, timeout: int = 300) -> bool:
        """
        Request confirmation from web frontend

        Args:
            session_id: Session identifier
            command_info: Command to be confirmed
            tool_name: Name of the tool calling for confirmation
            timeout: Timeout in seconds (default: 5 minutes)

        Returns:
            bool: True if confirmed, False if rejected or timeout
        """
        if not self.is_available():
            logger.error("Web interface not available - dependencies not injected")
            return False

        # Create confirmation event
        confirmation_event = threading.Event()
        confirmation_result = {"confirmed": False}

        def confirmation_callback(confirmed: bool):
            confirmation_result["confirmed"] = confirmed
            confirmation_event.set()

        # Add to pending confirmation list
        self._pending_confirmations[session_id] = {
            "command": command_info,
            "tool_name": tool_name,
            "callback": confirmation_callback,
        }

        # Push confirmation request through SSE
        try:
            self._send_sse_event(
                session_id,
                {
                    "type": "confirmation_request",
                    "command": command_info,
                    "tool_name": tool_name,
                    "session_id": session_id,
                },
            )
            logger.info(f"Confirmation request pushed via SSE: {command_info}")
        except Exception as e:
            logger.warning(f"SSE push failed, will rely on polling mechanism: {e}")

        logger.info(f"Waiting for web frontend to confirm command: {command_info}")

        # Wait for frontend confirmation (with timeout)
        if confirmation_event.wait(timeout):
            # User has made a choice
            return confirmation_result["confirmed"]
        else:
            # Timeout handling
            logger.warning(f"Command confirmation timeout: {command_info}")
            # Clean up pending confirmation status
            if session_id in self._pending_confirmations:
                del self._pending_confirmations[session_id]
            return False


# Global instance
web_confirmation_interface = WebConfirmationInterface()
