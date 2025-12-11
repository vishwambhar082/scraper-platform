# src/audit/audit_decorators.py
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from src.audit.audit_log import log_event


def audited(
    action: str,
    entity_type: str,
    entity_id_fn: Callable[..., str],
    actor_fn: Optional[Callable[..., str]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            entity_id = entity_id_fn(*args, **kwargs)
            actor = actor_fn(*args, **kwargs) if actor_fn else "system"
            log_event(actor=actor, action=action, entity_type=entity_type, entity_id=entity_id)
            return func(*args, **kwargs)

        return wrapper

    return decorator
