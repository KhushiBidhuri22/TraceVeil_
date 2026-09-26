from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier, Post

router = APIRouter(prefix="/actors", tags=["timeline"])


@router.get("/{actor_id}/timeline")
def get_actor_timeline(
    actor_id: str,
    db: Session = Depends(get_db),
):
    """
    Return chronological observations for an actor.
    """
    clean = str(actor_id).strip()
    actor = db.query(Actor).filter(Actor.actor_id == clean).first()
    if not actor:
        ident = db.query(Identifier).filter(Identifier.identifier_value.ilike(clean)).first()
        if ident and ident.actor:
            actor = ident.actor
    if not actor:
        for item in db.query(Actor).all():
            if item.primary_handle and item.primary_handle.lower() == clean.lower():
                actor = item
                break

    if not actor:
        raise HTTPException(
            status_code=404,
            detail=f"Actor '{actor_id}' not found",
        )

    posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .order_by(Post.event_timestamp.asc())
        .all()
    )

    events = []

    for post in posts:
        text = post.text or ""

        events.append({
            "post_id": post.id,
            "timestamp": (
                post.timestamp.isoformat()
                if post.timestamp
                else None
            ),
            "type": "observation",
            "source": post.source,
            "handle": post.handle,
            "summary": (
                text[:160] + "..."
                if len(text) > 160
                else text
            ),
            "has_pgp_key": bool(post.pgp_key),
            "has_wallet": bool(post.wallet),
        })

    return {
        "actor_id": actor.actor_id,
        "primary_handle": actor.primary_handle,
        "event_count": len(events),
        "events": events,
    }