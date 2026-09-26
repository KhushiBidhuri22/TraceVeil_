-- ============================================================
-- SIH DARK WEB THREAT INTELLIGENCE DATABASE
-- PostgreSQL schema
-- ============================================================

-- ------------------------------------------------------------
-- 1. ACTORS
-- The dataset has no actors.csv.
-- Actor IDs are referenced throughout the dataset.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS actors (
    actor_id VARCHAR(20) PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 2. SOURCES
-- Provenance for observations, posts, identifiers, etc.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sources (
    source_id VARCHAR(20) PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type VARCHAR(50),
    source_category VARCHAR(100),
    source_url TEXT,
    collection_method VARCHAR(100),
    first_seen TIMESTAMPTZ,
    last_checked TIMESTAMPTZ,
    reliability_score DOUBLE PRECISION
        CHECK (reliability_score >= 0 AND reliability_score <= 1),
    status VARCHAR(30),
    description TEXT
);


-- ------------------------------------------------------------
-- 3. OBSERVATIONS
-- Master ingestion table.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS observations (
    observation_id VARCHAR(20) PRIMARY KEY,
    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),
    actor_id VARCHAR(20) REFERENCES actors(actor_id),
    handle TEXT,
    content TEXT,
    event_timestamp TIMESTAMPTZ NOT NULL,
    pgp_key TEXT,
    wallet_address TEXT,
    domain TEXT,
    url TEXT,
    category VARCHAR(100),
    language VARCHAR(20),
    observation_type VARCHAR(50),
    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1),
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ
);


-- ------------------------------------------------------------
-- 4. POSTS
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS posts (
    post_id VARCHAR(20) PRIMARY KEY,
    actor_id VARCHAR(20) NOT NULL REFERENCES actors(actor_id),
    handle TEXT,
    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),
    content TEXT,
    event_timestamp TIMESTAMPTZ NOT NULL,
    language VARCHAR(20),
    category VARCHAR(50),
    reply_count INTEGER DEFAULT 0,
    parent_post_id VARCHAR(20) REFERENCES posts(post_id),
    sentiment_score DOUBLE PRECISION,
    word_count INTEGER,
    avg_sentence_length DOUBLE PRECISION,
    punctuation_ratio DOUBLE PRECISION,
    technical_term_ratio DOUBLE PRECISION,
    repeated_phrase_flag BOOLEAN
);


-- ------------------------------------------------------------
-- 5. IDENTIFIERS
-- Handles, wallets, PGP keys, aliases and profiles.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS identifiers (
    identifier_id VARCHAR(20) PRIMARY KEY,
    actor_id VARCHAR(20) NOT NULL REFERENCES actors(actor_id),
    identifier_type VARCHAR(50) NOT NULL,
    identifier_value TEXT NOT NULL,
    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1),
    status VARCHAR(50),
    observation_id VARCHAR(20) REFERENCES observations(observation_id)
);


-- ------------------------------------------------------------
-- 6. INFRASTRUCTURE
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS infrastructure (
    indicator_id VARCHAR(20) PRIMARY KEY,
    actor_id VARCHAR(20) REFERENCES actors(actor_id),
    indicator_type VARCHAR(100),
    indicator_value TEXT NOT NULL,
    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),
    observed_at TIMESTAMPTZ,
    indicator_detail TEXT,
    match_target VARCHAR(100),
    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1),
    status VARCHAR(30),
    evidence_id VARCHAR(30)
);


-- ------------------------------------------------------------
-- 7. WALLET TRANSACTIONS
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    from_wallet TEXT NOT NULL,
    to_wallet TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    amount DOUBLE PRECISION,
    currency VARCHAR(20),
    transaction_type VARCHAR(50),
    source_id VARCHAR(20) REFERENCES sources(source_id),
    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1),
    actor_from VARCHAR(20) REFERENCES actors(actor_id),
    actor_to VARCHAR(20) REFERENCES actors(actor_id),
    transaction_cluster VARCHAR(100),
    risk_signal VARCHAR(20)
);


-- ------------------------------------------------------------
-- 8. ACTIVITY TIMELINE
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS activity_timeline (
    event_id VARCHAR(20) PRIMARY KEY,
    actor_id VARCHAR(20) NOT NULL REFERENCES actors(actor_id),
    handle TEXT,
    event_type VARCHAR(50),
    event_timestamp TIMESTAMPTZ NOT NULL,
    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),
    description TEXT,
    metadata JSONB,
    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1)
);


-- ------------------------------------------------------------
-- 9. GRAPH RELATIONSHIPS
--
-- This is intentionally flexible because the dataset contains
-- multiple entity types:
--
-- actor, handle, pgp, wallet, post, infrastructure, source
--
-- We will later load these same relationships into Neo4j.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id VARCHAR(20) PRIMARY KEY,

    source_entity_type VARCHAR(50) NOT NULL,
    source_entity_id VARCHAR(100) NOT NULL,

    relationship_type VARCHAR(100) NOT NULL,

    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id VARCHAR(100) NOT NULL,

    source_id VARCHAR(20) NOT NULL REFERENCES sources(source_id),

    event_timestamp TIMESTAMPTZ NOT NULL,

    confidence DOUBLE PRECISION
        CHECK (confidence >= 0 AND confidence <= 1),

    evidence_id VARCHAR(30),

    relationship_status VARCHAR(30)
);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_observations_actor
    ON observations(actor_id);

CREATE INDEX IF NOT EXISTS idx_observations_source
    ON observations(source_id);

CREATE INDEX IF NOT EXISTS idx_observations_timestamp
    ON observations(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_posts_actor
    ON posts(actor_id);

CREATE INDEX IF NOT EXISTS idx_posts_source
    ON posts(source_id);

CREATE INDEX IF NOT EXISTS idx_posts_timestamp
    ON posts(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_identifiers_actor
    ON identifiers(actor_id);

CREATE INDEX IF NOT EXISTS idx_identifiers_value
    ON identifiers(identifier_value);

CREATE INDEX IF NOT EXISTS idx_infrastructure_actor
    ON infrastructure(actor_id);

CREATE INDEX IF NOT EXISTS idx_infrastructure_value
    ON infrastructure(indicator_value);

CREATE INDEX IF NOT EXISTS idx_relationships_source_entity
    ON relationships(source_entity_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_relationships_target_entity
    ON relationships(target_entity_type, target_entity_id);

CREATE INDEX IF NOT EXISTS idx_relationships_type
    ON relationships(relationship_type);

CREATE INDEX IF NOT EXISTS idx_relationships_confidence
    ON relationships(confidence);

CREATE INDEX IF NOT EXISTS idx_wallet_from
    ON wallet_transactions(from_wallet);

CREATE INDEX IF NOT EXISTS idx_wallet_to
    ON wallet_transactions(to_wallet);

CREATE INDEX IF NOT EXISTS idx_wallet_timestamp
    ON wallet_transactions(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_activity_actor
    ON activity_timeline(actor_id);

CREATE INDEX IF NOT EXISTS idx_activity_timestamp
    ON activity_timeline(event_timestamp);