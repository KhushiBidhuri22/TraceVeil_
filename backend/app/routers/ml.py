from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier, Post
from ..services.ml_adapter import compare_actors

router = APIRouter(prefix="/ml", tags=["ml"])


def _resolve_actor(val: str, db: Session):
    clean = str(val).strip()
    # 1. By actor_id
    a = db.query(Actor).filter(Actor.actor_id == clean).first()
    if a:
        return a
    # 2. By identifier
    ident = db.query(Identifier).filter(Identifier.identifier_value.ilike(clean)).first()
    if ident and ident.actor:
        return ident.actor
    # 3. By handle
    for item in db.query(Actor).all():
        if item.primary_handle and item.primary_handle.lower() == clean.lower():
            return item
    return None


@router.get("/compare/{actor_id}/{candidate_id}")
def compare_actor_profiles(
    actor_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
):
    if actor_id == candidate_id:
        raise HTTPException(
            status_code=400,
            detail="Choose two different actors.",
        )

    actor_a = _resolve_actor(actor_id, db)
    actor_b = _resolve_actor(candidate_id, db)

    if not actor_a or not actor_b:
        raise HTTPException(
            status_code=404,
            detail="One or both actors were not found.",
        )

    posts_a = (
        db.query(Post)
        .filter(Post.handle == actor_a.primary_handle)
        .all()
    )

    posts_b = (
        db.query(Post)
        .filter(Post.handle == actor_b.primary_handle)
        .all()
    )

    return compare_actors(
        actor_a=actor_a,
        actor_b=actor_b,
        posts_a=posts_a,
        posts_b=posts_b,
        db=db,
    )