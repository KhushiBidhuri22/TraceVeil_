from .config import NEO4J_DATABASE
from .db import get_neo4j_driver


# Evidence weights used by the prototype.
#
# These are heuristic weights, NOT probabilities.
EVIDENCE_WEIGHTS = {
    "ALIAS_OF": 1.00,
    "POSSIBLE_ALIAS_OF": 0.90,
    "USES_PGP": 0.90,
    "SHARES_INFRASTRUCTURE": 0.70,
    "USES_WALLET": 0.70,
    "ASSOCIATED_WITH": 0.60,
    "POSSIBLE_LINK": 0.50,
    "CONNECTED_TO": 0.40,
    "RELATED_TO": 0.30,
}


def calculate_association_score(actor_1: str, actor_2: str):
    """
    Calculate a heuristic association score between two actors.

    Evidence is collected from:
    1. Direct actor-to-actor relationships.
    2. Shared PGP identifiers.

    The same shared PGP node is counted once, so evidence is not
    double-counted.

    The final association_score is normalized to a 0-1 scale.
    It should NOT be interpreted as a calibrated probability.
    """

    driver = get_neo4j_driver()

    direct_query = """
    MATCH (a1:Actor {entity_id: $actor_1})
          -[r]-
          (a2:Actor {entity_id: $actor_2})

    RETURN
        type(r) AS relationship,
        r.confidence AS confidence,
        r.event_timestamp AS timestamp,
        r.relationship_id AS relationship_id
    ORDER BY confidence DESC
    """

    shared_pgp_query = """
    MATCH (a1:Actor {entity_id: $actor_1})
          -[r1:USES_PGP]->
          (p:PGP)
          <-[r2:USES_PGP]-
          (a2:Actor {entity_id: $actor_2})

    RETURN
        p.entity_id AS pgp_id,
        r1.confidence AS actor_1_confidence,
        r2.confidence AS actor_2_confidence
    ORDER BY pgp_id
    """

    try:
        with driver.session(database=NEO4J_DATABASE) as session:

            # ---------------------------------------------------------
            # 1. Direct actor-to-actor evidence
            # ---------------------------------------------------------
            direct_result = session.run(
                direct_query,
                actor_1=actor_1,
                actor_2=actor_2,
            )

            direct_evidence = [
                record.data()
                for record in direct_result
            ]

            # ---------------------------------------------------------
            # 2. Shared PGP evidence
            # ---------------------------------------------------------
            pgp_result = session.run(
                shared_pgp_query,
                actor_1=actor_1,
                actor_2=actor_2,
            )

            shared_pgp = [
                record.data()
                for record in pgp_result
            ]

    finally:
        driver.close()

    # -------------------------------------------------------------
    # Calculate raw weighted evidence score
    # -------------------------------------------------------------
    raw_score = 0.0

    for evidence in direct_evidence:
        relationship = evidence["relationship"]
        confidence = evidence["confidence"]

        if confidence is None:
            confidence = 0.0

        weight = EVIDENCE_WEIGHTS.get(
            relationship,
            0.20,
        )

        raw_score += float(confidence) * weight

    # -------------------------------------------------------------
    # Add shared PGP evidence.
    #
    # Each shared PGP is counted once using the average confidence
    # from the two actor-to-PGP relationships.
    # -------------------------------------------------------------
    for pgp in shared_pgp:
        confidence_1 = pgp["actor_1_confidence"] or 0.0
        confidence_2 = pgp["actor_2_confidence"] or 0.0

        average_confidence = (
            float(confidence_1) + float(confidence_2)
        ) / 2.0

        raw_score += (
            average_confidence
            * EVIDENCE_WEIGHTS["USES_PGP"]
        )

    # -------------------------------------------------------------
    # Normalize raw score to 0-1.
    #
    # This is a heuristic normalization, NOT a probability.
    # -------------------------------------------------------------
    association_score = (
        raw_score / (1.0 + raw_score)
    )

    # -------------------------------------------------------------
    # Determine evidence level
    # -------------------------------------------------------------
    if raw_score >= 1.50:
        evidence_level = "HIGH"
    elif raw_score >= 0.75:
        evidence_level = "MEDIUM"
    else:
        evidence_level = "LOW"

    # -------------------------------------------------------------
    # Collect evidence types
    # -------------------------------------------------------------
    direct_evidence_types = sorted(
        set(
            evidence["relationship"]
            for evidence in direct_evidence
        )
    )

    return {
        "actor_1": actor_1,
        "actor_2": actor_2,
        "association_score": round(
            association_score,
            2,
        ),
        "raw_score": round(
            raw_score,
            2,
        ),
        "evidence_count": (
            len(direct_evidence)
            + len(shared_pgp)
        ),
        "evidence_level": evidence_level,
        "direct_evidence_types": direct_evidence_types,
        "shared_pgp": [
            pgp["pgp_id"]
            for pgp in shared_pgp
        ],
        "direct_evidence": direct_evidence,
    }