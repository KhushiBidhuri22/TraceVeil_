from itertools import combinations
from math import sqrt

from sqlalchemy.orm import Session

from ..models import Actor, Identifier, Post


MODEL_FEATURES = [
    "stylometric_distance",
    "behavior_similarity",
    "embedding_similarity",
    "shared_pgp",
    "shared_infra",
    "shared_handle_with_overlap",
    "evidence_count",
    "same_kmeans_cluster",
]


def _identifier_values(
    db: Session,
    actor_id: str,
    identifier_type: str,
) -> set[str]:
    rows = (
        db.query(Identifier)
        .filter(
            Identifier.actor_id == str(actor_id),
            (Identifier.identifier_type == identifier_type) | (Identifier.identifier_type.ilike(f"%{identifier_type}%")),
        )
        .all()
    )

    return {
        row.identifier_value
        for row in rows
        if row.identifier_value
    }


def _get_actor_posts(
    db: Session,
    actor: Actor,
) -> list[Post]:
    return (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )


def _text_statistics(posts: list[Post]) -> tuple[float, float]:
    """
    Small baseline stylometry approximation.

    This is not equivalent to Jahnvi's trained stylometry pipeline.
    It only provides a simple fallback for the current MVP.
    """
    texts = [
        post.text or ""
        for post in posts
        if post.text
    ]

    if not texts:
        return 0.0, 0.0

    all_text = " ".join(texts)
    words = all_text.split()

    if not words:
        return 0.0, 0.0

    average_word_length = sum(
        len(word.strip(".,!?;:"))
        for word in words
    ) / len(words)

    punctuation_count = sum(
        1
        for character in all_text
        if character in ".,!?;:"
    )

    punctuation_ratio = punctuation_count / max(len(all_text), 1)

    return average_word_length, punctuation_ratio


def _stylometric_distance(
    posts_a: list[Post],
    posts_b: list[Post],
) -> float:
    stats_a = _text_statistics(posts_a)
    stats_b = _text_statistics(posts_b)

    return sqrt(
        (stats_a[0] - stats_b[0]) ** 2
        + (stats_a[1] - stats_b[1]) ** 2
    )


def _behavior_similarity(
    posts_a: list[Post],
    posts_b: list[Post],
) -> float:
    hours_a = {
        post.timestamp.hour
        for post in posts_a
        if post.timestamp
    }

    hours_b = {
        post.timestamp.hour
        for post in posts_b
        if post.timestamp
    }

    if not hours_a or not hours_b:
        return 0.0

    overlap = len(hours_a.intersection(hours_b))
    total = len(hours_a.union(hours_b))

    return overlap / total if total else 0.0


def build_features(
    actor_a: Actor,
    actor_b: Actor,
    posts_a: list[Post],
    posts_b: list[Post],
    db: Session,
) -> tuple[dict, list[dict]]:
    pgp_a = _identifier_values(db, actor_a.id, "pgp_key")
    pgp_b = _identifier_values(db, actor_b.id, "pgp_key")

    handles_a = _identifier_values(db, actor_a.id, "handle")
    handles_b = _identifier_values(db, actor_b.id, "handle")

    shared_pgp = int(bool(pgp_a.intersection(pgp_b)))
    shared_handle = int(bool(handles_a.intersection(handles_b)))

    source_a = {
        post.source
        for post in posts_a
        if post.source
    }

    source_b = {
        post.source
        for post in posts_b
        if post.source
    }

    evidence = []

    if shared_pgp:
        evidence.append({
            "type": "shared_pgp",
            "description": "The actors share a PGP identifier.",
            "available": True,
        })

    if shared_handle:
        evidence.append({
            "type": "shared_handle",
            "description": "The actors share a handle identifier.",
            "available": True,
        })

    if source_a.intersection(source_b):
        evidence.append({
            "type": "source_overlap",
            "description": (
                "The actors appear in at least one common source."
            ),
            "available": True,
        })

    stylometric_distance = _stylometric_distance(
        posts_a,
        posts_b,
    )

    behavior_similarity = _behavior_similarity(
        posts_a,
        posts_b,
    )

    # Not computable from your current tables alone.
    embedding_similarity = 0.0
    shared_infra = 0
    same_kmeans_cluster = 0

    evidence_count = (
        shared_pgp
        + shared_handle
        + int(bool(source_a.intersection(source_b)))
    )

    features = {
        "stylometric_distance": stylometric_distance,
        "behavior_similarity": behavior_similarity,
        "embedding_similarity": embedding_similarity,
        "shared_pgp": shared_pgp,
        "shared_infra": shared_infra,
        "shared_handle_with_overlap": shared_handle,
        "evidence_count": evidence_count,
        "same_kmeans_cluster": same_kmeans_cluster,
    }

    return features, evidence