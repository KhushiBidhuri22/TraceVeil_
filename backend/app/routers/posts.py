from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Post
from ..schemas import PostCreate, Post as PostSchema

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostSchema)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    new_post = Post(
        source=post.source,
        handle=post.handle,
        pgp_key=post.pgp_key,
        wallet=post.wallet,
        text=post.text,
        timestamp=post.timestamp or datetime.utcnow(),
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


@router.get("", response_model=list[PostSchema])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.event_timestamp.desc()).all()


@router.get("/{post_id}", response_model=PostSchema)
def get_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.post_id == str(post_id)).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post