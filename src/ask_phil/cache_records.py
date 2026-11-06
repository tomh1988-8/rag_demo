"""Public measurements for this delivery, without another delivery's private identity."""

from typing import Literal

from ask_phil.evidence import Record


class CacheDelivery(Record):
    version: Literal["exact-text-cache-v1"] = "exact-text-cache-v1"
    status: Literal["hit", "miss", "bypass"]
    reason: str
    eligible: bool = False
