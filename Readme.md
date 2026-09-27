# TraceVeil

### From authorized evidence to explainable investigative leads

TraceVeil is an evidence-first cybercrime investigation platform that helps authorized analysts connect fragmented digital clues, explore relationships, and review explainable investigative leads.

The platform combines structured intelligence, graph analysis, machine-learning signals, and evidence provenance in one investigation workspace.

> TraceVeil supports analyst decision-making. It does not automatically prove a person's identity or replace human investigation.

---

## Problem

Cybercrime investigations often begin with incomplete clues:

- A username or alias.
- A wallet address.
- A suspicious domain.
- A PGP key or identifier.
- A post, screenshot, or report.
- A transaction or infrastructure indicator.

These clues are usually scattered across different sources. Manually connecting them is slow and can lead to missed links, duplicated work, or unsupported assumptions.

TraceVeil organizes these clues into a searchable, graph-based investigation workflow.

---

## Features

- Actor and identifier search.
- Actor profile and dossier view.
- Relationship graph visualization.
- Alias, wallet, key, post, source, and infrastructure connections.
- PostgreSQL storage for structured intelligence records.
- Neo4j graph representation for relationship traversal.
- Machine-learning attribution signals.
- Explainable graph-supported confidence scoring.
- Evidence and relationship metadata.
- Analyst-oriented investigation workflow.
- JSON and CSV export support.
- Docker-based backend deployment.
- Separate frontend and backend deployment support.
- Evidence fingerprinting architecture using SHA-256 hashes.

---

## System architecture

```text
                    ┌────────────────────┐
                    │  JavaScript UI     │
                    │  Vercel            │
                    └─────────┬──────────┘
                              │ HTTP / JSON
                              ▼
                    ┌────────────────────┐
                    │  FastAPI Backend   │
                    │  Render / Docker   │
                    └──────┬─────┬───────┘
                           │     │
                           │     └──────────────────┐
                           ▼                        ▼
                 ┌────────────────┐      ┌────────────────┐
                 │ PostgreSQL     │      │ Neo4j          │
                 │ Structured     │      │ Relationship   │
                 │ intelligence   │      │ graph          │
                 └────────────────┘      └────────────────┘
                           ▲                        ▲
                           └──── Graph loader ──────┘

                    ┌────────────────────┐
                    │ ML inference layer │
                    │ Attribution signal │
                    └────────────────────┘
```

---

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | JavaScript, HTML, CSS | Investigation dashboard |
| Backend | Python, FastAPI | REST API and application orchestration |
| Validation | Pydantic | Request and response validation |
| Relational database | PostgreSQL | Structured records and metadata |
| Graph database | Neo4j | Entity and relationship analysis |
| Machine learning | Python, scikit-learn/joblib | Attribution signal generation |
| Containerization | Docker | Reproducible deployment |
| Frontend hosting | Vercel | Web interface deployment |
| Backend hosting | Render | API deployment |

---

## Core data flow

```text
1. Analyst enters an identifier.
2. FastAPI receives the request.
3. PostgreSQL is used for structured actor and evidence records.
4. Neo4j is queried for connected entities and relationships.
5. The ML layer generates a model-based signal.
6. Graph evidence contributes an additional explainable signal.
7. The backend combines the results.
8. The frontend displays the actor dossier, graph, evidence, and scores.
```

---

## Data model

### Main entities

- Actor.
- Alias or handle.
- PGP key.
- Wallet.
- Transaction.
- Post.
- Source.
- Observation.
- Infrastructure.
- Activity event.
- Domain.
- URL.
- Email alias.
- Username alias.

### Example relationships

```text
Actor -[:USES]-> Alias
Actor -[:USES_PGP]-> PGP
Actor -[:USES_WALLET]-> Wallet
Actor -[:MENTIONED_IN]-> Post
Actor -[:ASSOCIATED_WITH]-> Source
Actor -[:SHARES_INFRASTRUCTURE]-> Infrastructure
Wallet -[:SENT]-> Transaction
Transaction -[:RECEIVED_BY]-> Wallet
```

Relationships may include:

- Confidence.
- Source ID.
- Event timestamp.
- Original source identifier.
- Relationship ID.

---


## Project structure

```text
.
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── actors.py
│   │   │   ├── graph.py
│   │   │   ├── search.py
│   │   │   └── attribution.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── neo4j_service.py
│   │   │   ├── actor_service.py
│   │   │   └── attribution_service.py
│   │   └── database.py
│   └── graph_loader/
│       ├── neo4j_loader.py
│       ├── test_connections.py
│       └── check_postgres_tables.py
├── frontend/
│   ├── index.html
│   ├── BACKEND_CONNECT.js
│   ├── Dockerfile
│   ├── package.json
│   ├── css/
│   └── js/
├── ml/
│   ├── src/
│   └── artifacts/
├── .env.example
├── .gitignore
└── README.md
```



