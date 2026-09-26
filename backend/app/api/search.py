from fastapi import APIRouter, Query
from ..database import SessionLocal
from ..models import Actor, Identifier
from ..services.neo4j_service import Neo4jService
from ..services.actor_generator import generate_deterministic_actor

router = APIRouter(
    prefix="/api",
    tags=["search"],
)

neo4j_service = Neo4jService()


@router.get("/suggestions")
def suggestions():
    items = []
    db = SessionLocal()
    try:
        # Get distinctive handles, keys, wallets from database
        types_to_fetch = ["handle", "wallet", "pgp", "username_alias", "email_alias", "profile_id"]
        seen_vals = set()
        for target_type in types_to_fetch:
            sub_idents = (
                db.query(Identifier.identifier_type, Identifier.identifier_value)
                .filter(Identifier.identifier_type == target_type)
                .distinct()
                .limit(10)
                .all()
            )
            for itype, ivalue in sub_idents:
                v = (ivalue or "").strip()
                if v and v not in seen_vals:
                    seen_vals.add(v)
                    frontend_type = "wallet" if "wallet" in itype else ("key" if "key" in itype or "pgp" in itype else "handle")
                    items.append({
                        "label": f"{v} ({itype})",
                        "value": v,
                        "type": frontend_type,
                    })

        if not items:
            # Fallback to actors table
            actors = db.query(Actor).limit(20).all()
            for a in actors:
                h = a.primary_handle or a.actor_id
                if h not in seen_vals:
                    seen_vals.add(h)
                    items.append({
                        "label": f"{h} (handle)",
                        "value": h,
                        "type": "handle",
                    })
    except Exception:
        pass
    finally:
        db.close()

    if not items:
        default_items = [
            ("AshForge54", "handle"), ("AshFox60", "handle"), ("AshMoth", "handle"),
            ("AshShade20", "handle"), ("BlackCipher", "handle"), ("BlackDrift", "handle"),
            ("ChromeGrid", "handle"), ("ChromeMarrow", "handle"), ("CrimsonCrow", "handle"),
            ("WALLET_SYN_0001", "wallet"), ("WALLET_SYN_0002", "wallet"),
            ("PGP_SYN_0001", "key"), ("PGP_SYN_0002", "key"),
            ("user_21066", "handle"), ("alias1420@example.invalid", "handle")
        ]
        items = [{"label": f"{name} ({t})", "value": name, "type": t} for name, t in default_items]

    return {"items": items}


@router.get("/search")
def search(
    q: str = Query(""),
    type: str = Query("all"),
):
    clean_q = q.strip().lower()
    items = []
    db = SessionLocal()

    try:
        matched_actor_ids = set()

        if clean_q:
            # Find matching actors directly
            actors_direct = (
                db.query(Actor)
                .filter(Actor.actor_id.ilike(f"%{clean_q}%"))
                .limit(20)
                .all()
            )
            for a in actors_direct:
                matched_actor_ids.add(a.actor_id)

            # Find matching identifiers
            idents = (
                db.query(Identifier)
                .filter(Identifier.identifier_value.ilike(f"%{clean_q}%"))
                .limit(40)
                .all()
            )
            for i in idents:
                if i.actor_id:
                    matched_actor_ids.add(i.actor_id)
        else:
            # If search is empty, return top actors
            actors_all = db.query(Actor).limit(20).all()
            for a in actors_all:
                matched_actor_ids.add(a.actor_id)

        # Load actor objects and build response summaries
        for actor_id in list(matched_actor_ids)[:20]:
            actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
            if not actor:
                continue

            actor_idents = actor.identifiers or []
            aliases = [
                {
                    "id": str(i.identifier_id),
                    "handle": i.identifier_value,
                    "detail": f"Type: {i.identifier_type}",
                    "confidence": round((i.confidence or 0.8) * 100, 1),
                    "nodeId": str(i.identifier_id),
                }
                for i in actor_idents
                if i.identifier_type in ["handle", "alias", "username", "email"]
            ]

            keys = [
                {
                    "id": str(i.identifier_id),
                    "title": f"Key: {i.identifier_value[:12]}...",
                    "value": i.identifier_value,
                    "algorithm": "RSA-4096 / PGP",
                    "confidence": round((i.confidence or 0.9) * 100, 1),
                    "source": i.source_id,
                    "date": i.last_seen.isoformat() if i.last_seen else None,
                }
                for i in actor_idents
                if "key" in i.identifier_type or "pgp" in i.identifier_type
            ]

            wallets = [
                {
                    "id": str(i.identifier_id),
                    "title": f"Wallet: {i.identifier_value[:10]}...",
                    "value": i.identifier_value,
                    "network": "Cryptocurrency",
                    "confidence": round((i.confidence or 0.85) * 100, 1),
                    "source": i.source_id,
                    "date": i.last_seen.isoformat() if i.last_seen else None,
                }
                for i in actor_idents
                if "wallet" in i.identifier_type
            ]

            confidence_pct = round((actor.confidence or 0.85) * 100, 1)
            last_seen_iso = actor.last_seen.isoformat() if actor.last_seen else None
            first_seen_iso = actor.created_at.isoformat() if actor.created_at else None

            # Build graph for search card
            main_node_id = str(actor.actor_id)
            handle_str = actor.primary_handle or main_node_id
            g_nodes = [
                {
                    "id": main_node_id,
                    "name": handle_str,
                    "type": "actor",
                    "identifier": handle_str,
                    "confidence": confidence_pct,
                    "recordId": main_node_id,
                }
            ]
            g_edges = []
            node_ids_set = {main_node_id}

            for a in aliases[:4]:
                nid = a.get("nodeId") or f"node_{a['id']}"
                if nid not in node_ids_set:
                    node_ids_set.add(nid)
                    g_nodes.append({
                        "id": nid,
                        "name": a["handle"],
                        "type": "alias",
                        "identifier": a["handle"],
                        "confidence": a.get("confidence", 85.0),
                        "recordId": a["id"],
                    })
                    g_edges.append({
                        "id": f"edge_{main_node_id}_{nid}",
                        "from": main_node_id,
                        "to": nid,
                        "kind": "ALIAS_OF",
                        "confidence": a.get("confidence", 85.0),
                    })

            for k in keys[:3]:
                nid = f"node_{k['id']}"
                if nid not in node_ids_set:
                    node_ids_set.add(nid)
                    g_nodes.append({
                        "id": nid,
                        "name": k["title"],
                        "type": "key",
                        "identifier": k["value"],
                        "confidence": k.get("confidence", 95.0),
                        "recordId": k["id"],
                    })
                    g_edges.append({
                        "id": f"edge_{main_node_id}_{nid}",
                        "from": main_node_id,
                        "to": nid,
                        "kind": "USES_PGP",
                        "confidence": k.get("confidence", 95.0),
                    })

            for w in wallets[:3]:
                nid = f"node_{w['id']}"
                if nid not in node_ids_set:
                    node_ids_set.add(nid)
                    g_nodes.append({
                        "id": nid,
                        "name": w["title"],
                        "type": "wallet",
                        "identifier": w["value"],
                        "confidence": w.get("confidence", 90.0),
                        "recordId": w["id"],
                    })
                    g_edges.append({
                        "id": f"edge_{main_node_id}_{nid}",
                        "from": main_node_id,
                        "to": nid,
                        "kind": "USES_WALLET",
                        "confidence": w.get("confidence", 90.0),
                    })

            items.append({
                "id": str(actor.actor_id),
                "handle": handle_str,
                "description": f"Threat actor record ({len(actor_idents)} mapped identifiers).",
                "priority": "HIGH" if confidence_pct >= 80 else "MEDIUM",
                "confidence": confidence_pct,
                "firstSeen": first_seen_iso,
                "lastSeen": last_seen_iso,
                "aliases": aliases,
                "keys": keys,
                "wallets": wallets,
                "evidence": [],
                "sources": [],
                "events": [],
                "graph": {
                    "nodes": g_nodes,
                    "edges": g_edges,
                },
            })

    except Exception:
        pass
    finally:
        db.close()

    # Fallback search results if database returned nothing
    if not items:
        default_names = ["GreyRoot", "SilentTrace", "ShadowDrift", "OnyxNode"]
        matches = [h for h in default_names if clean_q in h.lower()] if clean_q else default_names
        if not matches and clean_q:
            matches = [q.strip()]

        for handle in matches:
            items.append(generate_deterministic_actor(handle))

    return {"items": items}
