
from fastapi import APIRouter, Query, Depends

from typing import Optional
from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db

from ..models import Actor, Identifier

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/suggestions")
def suggestions(db: Session = Depends(get_db)):
    actors = db.query(Actor).limit(10).all()
    return {"items": [
        {"label": a.primary_handle, "value": str(a.id), "type": "handle"}
        for a in actors
    ]}


@router.get("/search")
def search(q: str = Query(""), type: str = Query("all"), db: Session = Depends(get_db)):
    query = db.query(Actor)

    if q:
        matching_actor_ids = (
            db.query(Identifier.actor_id)
            .filter(Identifier.value.ilike(f"%{q}%"))
            .subquery()
        )
        query = query.filter(
            or_(
                Actor.primary_handle.ilike(f"%{q}%"),
                Actor.id.in_(matching_actor_ids),
            )
        )

    actors = query.limit(20).all()

    items = []
    for actor in actors:
        aliases, keys, wallets = [], [], []
        for ident in actor.identifiers:
            if ident.type == "handle":
                aliases.append({"id": str(ident.id), "handle": ident.value, "detail": None, "confidence": None, "nodeId": None})
            elif ident.type == "pgp_key":
                keys.append({"id": str(ident.id), "title": ident.value, "detail": None, "source": None, "date": None, "confidence": None, "nodeId": None, "url": None, "value": ident.value, "algorithm": None})
            elif ident.type == "wallet":
                wallets.append({"id": str(ident.id), "title": ident.value, "detail": None, "source": None, "date": None, "confidence": None, "nodeId": None, "url": None, "value": ident.value, "network": None})

        items.append({
            "id": str(actor.id),
            "handle": actor.primary_handle,
            "description": "",
            "priority": "unknown",
            "confidence": round((actor.confidence or 0.0) * 100, 1),
            "firstSeen": None,
            "lastSeen": actor.last_seen.isoformat() if actor.last_seen else None,
            "aliases": aliases,
            "keys": keys,
            "wallets": wallets,
            "evidence": [],
            "sources": [],
            "events": [],
        })

    return {"items": items}

    # Add actors from matching posts
    post_actor_ids = {p.actor_id for p in posts if p.actor_id}
    if post_actor_ids:
        post_actors = db.query(Actor).filter(Actor.actor_id.in_(post_actor_ids)).all()
        for a in post_actors:
            all_actors[a.actor_id] = a

    # Build full dossiers for each matching actor so all 6 chapters are populated in search cards
    items = [build_actor_dossier(a, db, include_graph=False) for a in all_actors.values()]

    return {
        "items": items,
        "actors": items,
        "posts": [
            {
                "id": p.id,
                "actor_id": p.actor_id,
                "handle": p.handle,
                "source": p.source,
                "content": p.content,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p in posts
        ],
    }

