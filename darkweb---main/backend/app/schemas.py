from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# --- Identifiers ---

class IdentifierBase(BaseModel):
    type: str
    value: str

class IdentifierCreate(IdentifierBase):
    pass

class Identifier(IdentifierBase):
    id: int
    actor_id: int

    class Config:
        from_attributes = True  # allows ORM objects → Pydantic

# --- Actors ---

class ActorBase(BaseModel):
    primary_handle: str

class ActorCreate(ActorBase):
    # Optionally allow creating with identifiers
    identifiers: Optional[List[IdentifierCreate]] = []

class Actor(ActorBase):
    id: int
    confidence: float
    last_seen: datetime
    identifiers: List[Identifier] = []

    class Config:
        from_attributes = True

# --- Posts ---

class PostBase(BaseModel):
    source: str
    handle: str
    pgp_key: Optional[str] = None
    wallet: Optional[str] = None
    text: str
    timestamp: Optional[datetime] = None


class PostCreate(PostBase):
    pass


class Post(PostBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True