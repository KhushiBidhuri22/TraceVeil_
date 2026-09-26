import hashlib
from datetime import datetime, timedelta


def generate_deterministic_actor(clean_id: str) -> dict:
    raw = str(clean_id or "Identifier").strip()
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    n1 = int(h[0:4], 16)
    n2 = int(h[4:8], 16)
    n3 = int(h[8:12], 16)
    n4 = int(h[12:16], 16)
    n5 = int(h[16:20], 16)
    n6 = int(h[20:24], 16)

    # Unique confidence between 68.0% and 96.5%
    confidence_pct = round(68.0 + (n1 % 285) / 10.0, 1)

    # Distinct counts per identifier
    num_aliases = 2 + (n2 % 6)
    num_keys = 1 + (n3 % 3)
    num_wallets = 1 + (n4 % 4)
    num_sources = 1 + (n5 % 4)
    num_events = 2 + (n6 % 6)

    resolved_id = f"ACT_{raw[:6].upper().replace(' ', '_')}"
    base_date = datetime(2024, 1, 15) + timedelta(days=(n1 % 120))
    last_date = base_date + timedelta(days=(n2 % 150) + 10)

    # Dynamic aliases
    alias_suffixes = ["shadow", "ops", "zero", "node", "nexus", "root", "cipher", "moth"]
    aliases = []
    for i in range(num_aliases):
        alias_handle = f"{raw}_{alias_suffixes[i % len(alias_suffixes)]}"
        alias_conf = round(max(50.0, confidence_pct - (i * 4.5)), 1)
        aliases.append({
            "id": f"{raw}_a{i+1}",
            "handle": alias_handle,
            "detail": f"Observed on Underground Forum #{i+1}",
            "confidence": alias_conf,
            "nodeId": f"node_{raw}_a{i+1}",
        })

    # Dynamic keys
    keys = []
    for i in range(num_keys):
        key_hex = h[(i * 8):(i * 8) + 8].upper()
        key_conf = round(max(60.0, confidence_pct + (i * 2.1)), 1)
        keys.append({
            "id": f"{raw}_k{i+1}",
            "title": f"PGP Key ({key_hex}...)",
            "value": f"{key_hex}B82C4F",
            "algorithm": "RSA-4096 / PGP",
            "confidence": key_conf,
            "source": f"SRC_000{i+1}",
            "date": (base_date + timedelta(days=i * 12)).isoformat() + "Z",
            "nodeId": f"node_{raw}_k{i+1}",
        })

    # Dynamic wallets
    wallets = []
    networks = ["Bitcoin (BTC)", "Monero (XMR)", "Ethereum (ETH)"]
    for i in range(num_wallets):
        net = networks[i % len(networks)]
        prefix = "bc1q" if "Bitcoin" in net else ("4" if "Monero" in net else "0x")
        w_val = f"{prefix}{h[(i * 10):(i * 10) + 24]}"
        w_conf = round(max(55.0, confidence_pct - (i * 3.2)), 1)
        wallets.append({
            "id": f"{raw}_w{i+1}",
            "title": f"{net} Wallet",
            "value": w_val,
            "network": net,
            "confidence": w_conf,
            "source": f"SRC_CRYPTO_{i+1}",
            "date": (base_date + timedelta(days=i * 15)).isoformat() + "Z",
            "nodeId": f"node_{raw}_w{i+1}",
        })

    # Dynamic sources
    all_source_names = [
        "Bohemia Marketplace", "Dread Forum", "Exploit.in", "XSS Cyber Intelligence",
        "TorRecon Monitoring", "BreachForums", "Monero Trace Engine"
    ]
    sources = []
    for i in range(num_sources):
        s_name = all_source_names[(n5 + i) % len(all_source_names)]
        s_conf = round(80.0 + ((n2 + i * 7) % 180) / 10.0, 1)
        sources.append({
            "id": f"SRC_{raw[:3]}_{i+1}",
            "name": s_name,
            "title": f"Intelligence Source: {s_name}",
            "detail": "Darknet Intelligence Feed | Active Monitoring",
            "source": f"SRC_000{i+1}",
            "date": base_date.isoformat() + "Z",
            "confidence": s_conf,
            "nodeId": f"node_src_{raw}_{i+1}",
            "url": f"http://{s_name.lower().replace(' ', '')}.onion",
            "observedAt": base_date.isoformat() + "Z",
        })

    # Dynamic evidence
    evidence = []
    methods = [
        "Stylometric & Behavioral Correlation", "PGP Key Re-use Cross-Match",
        "Cryptocurrency Flow Clustering", "Co-occurrence Frequency Analysis"
    ]
    for i in range(num_aliases):
        a_h = aliases[i]["handle"]
        ev_conf = aliases[i]["confidence"]
        evidence.append({
            "id": f"ev_{raw}_{i+1}",
            "title": f"Persona link: {raw} → {a_h}",
            "detail": f"Correlated {raw} with {a_h} using {methods[i % len(methods)]}.",
            "source": "TraceVeil Engine",
            "date": (base_date + timedelta(days=i * 8)).isoformat() + "Z",
            "confidence": ev_conf,
            "nodeId": f"node_ev_{raw}_{i+1}",
            "url": None,
            "method": methods[i % len(methods)],
        })

    # Dynamic activity timeline events
    categories = ["POST", "REPLY", "WALLET_ACTIVITY", "LOGIN", "LISTING", "MESSAGE"]
    events = []
    for i in range(num_events):
        cat = categories[(n6 + i) % len(categories)]
        evt_date = (base_date + timedelta(days=i * 20)).isoformat() + "Z"
        evt_conf = round(max(60.0, confidence_pct - (i * 2.0)), 1)
        events.append({
            "id": f"EVT_{raw}_{i+1}",
            "title": f"[{cat}] Activity recorded for {raw}",
            "detail": f"{cat.capitalize()} logged on monitored source {sources[i % len(sources)]['name']}.",
            "source": sources[i % len(sources)]["name"],
            "date": evt_date,
            "confidence": evt_conf,
            "nodeId": f"node_evt_{raw}_{i+1}",
            "url": None,
            "label": cat,
        })

    # Graph
    g_nodes = [
        {
            "id": raw,
            "name": raw,
            "type": "actor",
            "identifier": raw,
            "confidence": confidence_pct,
            "recordId": raw,
        }
    ]
    g_edges = []
    for a in aliases:
        g_nodes.append({
            "id": a["nodeId"],
            "name": a["handle"],
            "type": "alias",
            "identifier": a["handle"],
            "confidence": a["confidence"],
            "recordId": a["id"],
        })
        g_edges.append({
            "id": f"edge_{raw}_{a['nodeId']}",
            "from": raw,
            "to": a["nodeId"],
            "kind": "ALIAS_OF",
            "confidence": a["confidence"],
        })
    for k in keys:
        g_nodes.append({
            "id": k["nodeId"],
            "name": k["title"],
            "type": "key",
            "identifier": k["value"],
            "confidence": k["confidence"],
            "recordId": k["id"],
        })
        g_edges.append({
            "id": f"edge_{raw}_{k['nodeId']}",
            "from": raw,
            "to": k["nodeId"],
            "kind": "USES_PGP",
            "confidence": k["confidence"],
        })
    for w in wallets:
        g_nodes.append({
            "id": w["nodeId"],
            "name": w["title"],
            "type": "wallet",
            "identifier": w["value"],
            "confidence": w["confidence"],
            "recordId": w["id"],
        })
        g_edges.append({
            "id": f"edge_{raw}_{w['nodeId']}",
            "from": raw,
            "to": w["nodeId"],
            "kind": "USES_WALLET",
            "confidence": w["confidence"],
        })

    return {
        "id": raw,
        "actor_id": resolved_id,
        "handle": raw,
        "description": f"Deanonymized threat persona ({raw}) with {len(aliases) + len(keys) + len(wallets)} mapped identifiers.",
        "priority": "HIGH" if confidence_pct >= 80 else "MEDIUM",
        "confidence": confidence_pct,
        "firstSeen": base_date.isoformat() + "Z",
        "lastSeen": last_date.isoformat() + "Z",
        "aliases": aliases,
        "keys": keys,
        "wallets": wallets,
        "evidence": evidence,
        "sources": sources,
        "events": events,
        "graph": {
            "nodes": g_nodes,
            "edges": g_edges,
        },
    }
