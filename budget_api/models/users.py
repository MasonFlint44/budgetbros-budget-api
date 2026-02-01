from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    id: uuid.UUID
    email: str
    created_at: datetime
    last_seen_at: datetime
