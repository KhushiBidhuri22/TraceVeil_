from ml.src.inference import predict_relationship

from ..models import Actor, Post
from .ml_features import build_features


def compare_actors(
    actor_a: Actor,
    actor_b: Actor,
    posts_a: list[Post],
    posts_b: list[Post],
    db,
) -> dict:
    features, evidence = build_features(
        actor_a=actor_a,
        actor_b=actor_b,
        posts_a=posts_a,
        posts_b=posts_b,
        db=db,
    )

    prediction = predict_relationship(
        actor_a=actor_a.primary_handle,
        actor_b=actor_b.primary_handle,
        features=features,
    )

    prediction["evidence"] = evidence

    return prediction