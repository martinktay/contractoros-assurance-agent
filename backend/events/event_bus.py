import logging
import asyncio
from typing import Callable, Any, Optional
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

class EventBus:
    """In-memory Event Bus to decouple event producers and consumers."""
    
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to event: {event_type}")

    def emit(self, event_type: str, background_tasks: Optional[BackgroundTasks] = None, *args: Any, **kwargs: Any) -> None:
        """Publishes an event to all registered listeners.
        
        If a BackgroundTasks object is provided, listeners will be executed asynchronously
        as background tasks. Otherwise, they are executed immediately.
        """
        handlers = self._listeners.get(event_type, [])
        if not handlers:
            logger.debug(f"No handlers registered for event: {event_type}")
            return
            
        for handler in handlers:
            if background_tasks:
                background_tasks.add_task(handler, *args, **kwargs)
                logger.info(f"Queued handler {handler.__name__} as background task for event {event_type}")
            else:
                # Sync execution
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(*args, **kwargs))
                else:
                    handler(*args, **kwargs)
                logger.info(f"Executed handler {handler.__name__} synchronously for event {event_type}")

# Global Event Bus instance
event_bus = EventBus()
