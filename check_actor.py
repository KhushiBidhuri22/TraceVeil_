from backend.app.database import SessionLocal
from backend.app.models import Actor, Identifier, Post

db = SessionLocal()
actor = db.query(Actor).filter(Actor.id == 4).first()

if not actor:
    print("No actor with id=4 exists in SQLite.")
else:
    print("Handle:", actor.primary_handle)
    print("Confidence:", actor.confidence)
    print("Last seen:", actor.last_seen)
    idents = db.query(Identifier).filter(Identifier.actor_id == 4).all()
    print("Identifier count:", len(idents))
    for i in idents:
        print(" -", i.type, ":", i.value)
    posts = db.query(Post).filter(Post.handle == actor.primary_handle).all()
    print("Post count:", len(posts))
    for p in posts:
        print(" post:", p.source, p.handle, p.pgp_key, p.wallet, p.text)