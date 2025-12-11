# src/api/webhooks.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("webhooks-api")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@dataclass
class _Subscription:
    id: int
    event_type: str
    url: str

_SUBSCRIPTIONS: Dict[int, _Subscription] = {}
_NEXT_ID: int = 1

class SubscriptionCreate(BaseModel):
    event_type: str
    url: HttpUrl

class SubscriptionOut(BaseModel):
    id: int
    event_type: str
    url: HttpUrl

@router.post("", response_model=SubscriptionOut)
async def create_subscription(body: SubscriptionCreate) -> SubscriptionOut:
    global _NEXT_ID
    sub = _Subscription(id=_NEXT_ID, event_type=body.event_type, url=str(body.url))
    _SUBSCRIPTIONS[_NEXT_ID] = sub
    _NEXT_ID += 1
    safe_log(
        log,
        "info",
        "Webhook subscription created",
        extra=sanitize_for_log({"event_type": sub.event_type, "url": sub.url}),
    )
    return SubscriptionOut(id=sub.id, event_type=sub.event_type, url=sub.url)

@router.get("", response_model=List[SubscriptionOut])
async def list_subscriptions() -> List[SubscriptionOut]:
    return [SubscriptionOut(id=s.id, event_type=s.event_type, url=s.url) for s in _SUBSCRIPTIONS.values()]

@router.delete("/{sub_id}")
async def delete_subscription(sub_id: int) -> dict:
    if sub_id not in _SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub = _SUBSCRIPTIONS.pop(sub_id)
    safe_log(
        log,
        "info",
        "Webhook subscription deleted",
        extra=sanitize_for_log({"event_type": sub.event_type, "url": sub.url}),
    )
    return {"ok": True}

def get_subscribers_for_event(event_type: str) -> List[_Subscription]:
    return [s for s in _SUBSCRIPTIONS.values() if s.event_type == event_type]
