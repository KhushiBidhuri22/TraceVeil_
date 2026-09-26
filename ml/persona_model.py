import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from google.colab import files
uploaded = files.upload()

posts = pd.read_csv("03_posts.csv")
timeline = pd.read_csv("08_activity_timeline.csv")
identifiers = pd.read_csv("04_identifiers.csv")
wallet_tx = pd.read_csv("07_wallet_transactions.csv")
infra = pd.read_csv("05_infrastructure.csv")

dataframes = {
    "posts": posts,
    "timeline": timeline,
    "identifiers": identifiers,
    "wallet_tx": wallet_tx,
    "infra": infra,
}

for name, df in dataframes.items():
    print(f"\n=== {name} ===")
    print("Shape:", df.shape)
    print(df.dtypes)

for name, df in dataframes.items():
    print(f"\n=== {name} — missing % per column ===")
    print((df.isnull().mean() * 100).round(1).sort_values(ascending=False))

for name, df in dataframes.items():
    print(f"\n=== {name} — head ===")
    display(df.head(3))

# Key categorical columns worth checking distinct values for
print("\nPost categories:", posts["category"].unique())
print("Timeline event types:", timeline["event_type"].unique())
print("Identifier types:", identifiers["identifier_type"].unique())
print("Identifier statuses:", identifiers["status"].unique())
print("Wallet transaction types:", wallet_tx["transaction_type"].unique())
print("Wallet risk signals:", wallet_tx["risk_signal"].unique())
print("Infra indicator types:", infra["indicator_type"].unique())

print("Unique actors in posts:", posts["actor_id"].nunique())
print("Unique actors in timeline:", timeline["actor_id"].nunique())
print("Unique actors in identifiers:", identifiers["actor_id"].nunique())
print("Unique handles in identifiers:", identifiers[identifiers["identifier_type"]=="handle"]["identifier_value"].nunique())
print("Unique wallets in identifiers:", identifiers[identifiers["identifier_type"]=="wallet"]["identifier_value"].nunique())

handles_per_actor = identifiers[identifiers["identifier_type"]=="handle"].groupby("actor_id")["identifier_value"].nunique()
wallets_per_actor = identifiers[identifiers["identifier_type"]=="wallet"].groupby("actor_id")["identifier_value"].nunique()

print("Handles per actor — describe:\n", handles_per_actor.describe())
print("\nWallets per actor — describe:\n", wallets_per_actor.describe())

handles_per_actor.hist(bins=15)

wallet_owner_counts = identifiers[identifiers["identifier_type"]=="wallet"].groupby("identifier_value")["actor_id"].nunique()
shared_wallets = wallet_owner_counts[wallet_owner_counts > 1]
print(f"Wallets shared by multiple actors: {len(shared_wallets)}")
print(shared_wallets.head(10))

handle_owner_counts = identifiers[identifiers["identifier_type"]=="handle"].groupby("identifier_value")["actor_id"].nunique()
shared_handles = handle_owner_counts[handle_owner_counts > 1]
print(f"\nHandles shared by multiple actors: {len(shared_handles)}")
print(shared_handles.head(10))

print(timeline["event_type"].value_counts())

migration_events = timeline[timeline["event_type"].isin(["MIGRATION", "HANDLE_CHANGE"])]
print(f"\nTotal migration/handle-change events: {len(migration_events)}")
display(migration_events.head(10))
print("\nActors with migration events:", migration_events["actor_id"].nunique())

style_by_actor = posts.groupby("actor_id")[["avg_sentence_length", "punctuation_ratio", "technical_term_ratio", "sentiment_score"]].mean()
display(style_by_actor.describe())
style_by_actor["avg_sentence_length"].hist(bins=20)

sf_rows = identifiers[identifiers["identifier_value"] == "ShadowForge"]
display(sf_rows[["actor_id", "first_seen", "last_seen", "status"]].sort_values("first_seen"))

import json

handle_changes = timeline[timeline["event_type"] == "HANDLE_CHANGE"].copy()
handle_changes["from_handle"] = handle_changes["metadata"].apply(lambda m: json.loads(m).get("from_handle"))
handle_changes["to_handle"] = handle_changes["metadata"].apply(lambda m: json.loads(m).get("to_handle"))

migration_chain = handle_changes[["actor_id", "from_handle", "to_handle", "timestamp", "confidence"]].sort_values(["actor_id", "timestamp"])
display(migration_chain)

print(migration_chain[(migration_chain["from_handle"] == "ShadowForge") | (migration_chain["to_handle"] == "ShadowForge")])

# Which actors are seen sending/receiving from each wallet, across BOTH wallet columns
from_map = wallet_tx.dropna(subset=["actor_from"])[["from_wallet", "actor_from"]].rename(columns={"from_wallet":"wallet","actor_from":"actor"})
to_map = wallet_tx.dropna(subset=["actor_to"])[["to_wallet", "actor_to"]].rename(columns={"to_wallet":"wallet","actor_to":"actor"})
wallet_actor_links = pd.concat([from_map, to_map]).drop_duplicates()

wallet_actor_counts = wallet_actor_links.groupby("wallet")["actor"].nunique()
shared_via_tx = wallet_actor_counts[wallet_actor_counts > 1]
print(f"Wallets linked to multiple actors via transactions: {len(shared_via_tx)}")
print(shared_via_tx.head(10))

print("Unique transaction clusters:", wallet_tx["transaction_cluster"].nunique())
print(wallet_tx["transaction_cluster"].dropna().unique()[:20])

# Clusters that reference two different actor IDs in their name (like the STRO one you saw)
import re
multi_actor_clusters = wallet_tx["transaction_cluster"].dropna().unique()
multi_actor_clusters = [c for c in multi_actor_clusters if len(re.findall(r"ACT_\d+", c)) > 1]
print(f"\nClusters naming multiple actors: {len(multi_actor_clusters)}")
print(multi_actor_clusters[:15])

import networkx as nx

G = nx.Graph()
for _, row in wallet_tx.iterrows():
    G.add_edge(row["from_wallet"], row["to_wallet"])

components = list(nx.connected_components(G))
print(f"Total connected wallet components: {len(components)}")

# For each component, find which actors touch it (via actor_from/actor_to)
wallet_to_actor = pd.concat([
    wallet_tx.dropna(subset=["actor_from"])[["from_wallet","actor_from"]].rename(columns={"from_wallet":"wallet","actor_from":"actor"}),
    wallet_tx.dropna(subset=["actor_to"])[["to_wallet","actor_to"]].rename(columns={"to_wallet":"wallet","actor_to":"actor"})
]).drop_duplicates()

multi_actor_components = []
for comp in components:
    actors_in_comp = wallet_to_actor[wallet_to_actor["wallet"].isin(comp)]["actor"].unique()
    if len(actors_in_comp) > 1:
        multi_actor_components.append((comp, actors_in_comp))

print(f"\nConnected components touching multiple actors: {len(multi_actor_components)}")
for comp, actors in multi_actor_components[:5]:
    print(f"  {len(comp)} wallets, actors: {actors}")

# Direct wallet-to-wallet edges only — who's directly connected without long chains
direct_edges = wallet_tx[["from_wallet", "to_wallet"]].drop_duplicates()

# Map each wallet to its actor(s)
wallet_actors = wallet_to_actor.groupby("wallet")["actor"].apply(set).to_dict()

direct_actor_pairs = set()
for _, row in direct_edges.iterrows():
    actors_a = wallet_actors.get(row["from_wallet"], set())
    actors_b = wallet_actors.get(row["to_wallet"], set())
    for a in actors_a:
        for b in actors_b:
            if a != b:
                direct_actor_pairs.add(tuple(sorted([a, b])))

print(f"Actor pairs with a DIRECT wallet transaction between them: {len(direct_actor_pairs)}")
for pair in list(direct_actor_pairs)[:15]:
    print(pair)

# For a sample of actor pairs, compute shortest path length between their wallet sets
import itertools

sample_actors = list(wallet_to_actor["actor"].unique())[:10]  # small sample first, to check runtime
actor_wallets = wallet_to_actor.groupby("actor")["wallet"].apply(list).to_dict()

path_lengths = {}
for a, b in itertools.combinations(sample_actors, 2):
    min_dist = float("inf")
    for wa in actor_wallets[a][:3]:      # limit to avoid huge runtime
        for wb in actor_wallets[b][:3]:
            if nx.has_path(G, wa, wb):
                d = nx.shortest_path_length(G, wa, wb)
                min_dist = min(min_dist, d)
    path_lengths[(a, b)] = min_dist

print(pd.Series(path_lengths).sort_values().head(15))

print("Total unique clusters:", wallet_tx["transaction_cluster"].nunique())
print("\nSample cluster names:")
print(wallet_tx["transaction_cluster"].dropna().unique()[:20])

# Extract the prefix pattern (e.g. STRO, MED, etc.) before the actor IDs
import re
def extract_prefix(cluster):
    match = re.match(r"CLUSTER_([A-Z]+)_", str(cluster))
    return match.group(1) if match else None

wallet_tx["cluster_prefix"] = wallet_tx["transaction_cluster"].apply(extract_prefix)
print("\nCluster prefix counts:")
print(wallet_tx["cluster_prefix"].value_counts())

def extract_actor_pair(cluster):
    if pd.isna(cluster):
        return None
    actors = re.findall(r"ACT_\d+", cluster)
    return tuple(sorted(set(actors))) if len(set(actors)) > 1 else None

wallet_tx["cluster_actor_pair"] = wallet_tx["transaction_cluster"].apply(extract_actor_pair)
named_pairs = wallet_tx.dropna(subset=["cluster_actor_pair"])[["cluster_actor_pair", "cluster_prefix"]].drop_duplicates()
print(f"Distinct named actor-pairs in clusters: {len(named_pairs)}")
display(named_pairs)

cluster_summary = wallet_tx.dropna(subset=["cluster_actor_pair"]).groupby("cluster_prefix").agg(
    mean_confidence=("confidence", "mean"),
    mean_amount=("amount", "mean"),
    n_transactions=("transaction_id", "count"),
    risk_signals=("risk_signal", lambda x: x.value_counts().to_dict())
)
display(cluster_summary)

for a, b in named_pairs[named_pairs["cluster_prefix"]=="SHAR"]["cluster_actor_pair"]:
    a_ids = set(identifiers[identifiers["actor_id"]==a]["identifier_value"])
    b_ids = set(identifiers[identifiers["actor_id"]==b]["identifier_value"])
    print(f"{a} vs {b} — shared identifiers: {a_ids & b_ids}")

for prefix in ["STRO", "MEDI"]:
    print(f"\n=== {prefix} pairs ===")
    for a, b in named_pairs[named_pairs["cluster_prefix"]==prefix]["cluster_actor_pair"]:
        a_ids = set(identifiers[identifiers["actor_id"]==a]["identifier_value"])
        b_ids = set(identifiers[identifiers["actor_id"]==b]["identifier_value"])
        style_a = style_by_actor.loc[a] if a in style_by_actor.index else None
        style_b = style_by_actor.loc[b] if b in style_by_actor.index else None
        style_dist = None
        if style_a is not None and style_b is not None:
            style_dist = ((style_a - style_b)**2).sum()**0.5
        print(f"{a} vs {b} — shared identifiers: {a_ids & b_ids} | stylometric distance: {style_dist:.3f}" if style_dist is not None else f"{a} vs {b} — shared identifiers: {a_ids & b_ids}")

# Does infrastructure indicator_value/match_target overlap for known pairs?
for prefix in ["STRO", "MEDI", "SHAR"]:
    print(f"\n=== {prefix} pairs — infrastructure overlap ===")
    for a, b in named_pairs[named_pairs["cluster_prefix"]==prefix]["cluster_actor_pair"]:
        infra_a = set(infra[infra["actor_id"]==a]["match_target"].dropna())
        infra_b = set(infra[infra["actor_id"]==b]["match_target"].dropna())
        print(f"{a} vs {b} — shared infra clusters: {infra_a & infra_b}")

import re

def extract_actor_pair_infra(val):
    if pd.isna(val):
        return None
    actors = re.findall(r"ACT_\d+", str(val))
    return tuple(sorted(set(actors))) if len(set(actors)) > 1 else None

# Check both indicator_value and match_target for embedded actor-pair naming
infra["pair_from_value"] = infra["indicator_value"].apply(extract_actor_pair_infra)
infra["pair_from_target"] = infra["match_target"].apply(extract_actor_pair_infra)

print("Actor pairs named in indicator_value:", infra["pair_from_value"].dropna().unique())
print("Actor pairs named in match_target:", infra["pair_from_target"].dropna().unique())

# Also look at match_target's naming pattern generally
print("\nSample match_target values:")
print(infra["match_target"].dropna().unique()[:15])

import numpy as np
import json

# Stylometric profile
style_profile = posts.groupby("actor_id")[
    ["avg_sentence_length", "punctuation_ratio", "technical_term_ratio", "sentiment_score"]
].mean()

# Behavioral profile: posting-hour distribution per actor (from timeline metadata)
def get_hour(metadata_str):
    try:
        return json.loads(metadata_str).get("hour")
    except Exception:
        return None

timeline["hour"] = timeline["metadata"].apply(get_hour)
hour_dist = timeline.dropna(subset=["hour"]).groupby("actor_id")["hour"].apply(
    lambda hours: np.histogram(hours, bins=24, range=(0,24), density=True)[0]
)

# Identifier sets per actor, split by type
def id_set(actor_id, id_type):
    return set(identifiers[(identifiers["actor_id"]==actor_id) & (identifiers["identifier_type"]==id_type)]["identifier_value"])

actors = sorted(identifiers["actor_id"].unique())
pgp_sets = {a: id_set(a, "pgp") for a in actors}
handle_sets = {a: id_set(a, "handle") for a in actors}
wallet_sets = {a: id_set(a, "wallet") for a in actors}

# Infra sets per actor
infra_sets = {a: set(infra[infra["actor_id"]==a]["match_target"].dropna()) for a in actors}

print("Actors profiled:", len(actors))
print("Sample PGP set:", list(pgp_sets.items())[:2])

from itertools import combinations
from scipy.spatial.distance import euclidean, cosine

def compute_features(a, b):
    feats = {}

    # Stylometric distance (validated: real but noisy signal)
    if a in style_profile.index and b in style_profile.index:
        feats["stylometric_distance"] = euclidean(style_profile.loc[a], style_profile.loc[b])
    else:
        feats["stylometric_distance"] = np.nan

    # Behavioral similarity (posting-hour pattern)
    if a in hour_dist.index and b in hour_dist.index:
        feats["behavior_similarity"] = 1 - cosine(hour_dist[a], hour_dist[b])
    else:
        feats["behavior_similarity"] = np.nan

    # Shared PGP (validated: your strongest clean signal)
    feats["shared_pgp"] = int(len(pgp_sets[a] & pgp_sets[b]) > 0)

    # Shared infra cluster (validated: strong, mirrors PGP)
    feats["shared_infra"] = int(len(infra_sets[a] & infra_sets[b]) > 0)

    # Shared wallet-transaction cluster (validated: needs corroboration, not standalone)
    cluster_a = set(wallet_tx[wallet_tx["actor_from"]==a]["transaction_cluster"].dropna()) | \
                set(wallet_tx[wallet_tx["actor_to"]==a]["transaction_cluster"].dropna())
    cluster_b = set(wallet_tx[wallet_tx["actor_from"]==b]["transaction_cluster"].dropna()) | \
                set(wallet_tx[wallet_tx["actor_to"]==b]["transaction_cluster"].dropna())
    feats["shared_wallet_cluster"] = int(len(cluster_a & cluster_b) > 0)

    # Shared handle WITH temporal overlap (validated: raw shared handle alone is unsafe — ShadowForge case)
    shared_handle_overlap = 0
    for h in handle_sets[a] & handle_sets[b]:
        rows_a = identifiers[(identifiers["actor_id"]==a) & (identifiers["identifier_value"]==h)]
        rows_b = identifiers[(identifiers["actor_id"]==b) & (identifiers["identifier_value"]==h)]
        for _, ra in rows_a.iterrows():
            for _, rb in rows_b.iterrows():
                if not (ra["last_seen"] < rb["first_seen"] or rb["last_seen"] < ra["first_seen"]):
                    shared_handle_overlap = 1
    feats["shared_handle_with_overlap"] = shared_handle_overlap

    # Evidence count (validated conclusion: verdict should scale with # of corroborating types)
    feats["evidence_count"] = feats["shared_pgp"] + feats["shared_infra"] + feats["shared_handle_with_overlap"]

    return feats

rows = []
for a, b in combinations(actors, 2):
    f = compute_features(a, b)
    f["actor_a"] = a
    f["actor_b"] = b
    rows.append(f)

pair_features = pd.DataFrame(rows)
print("Total pairs:", len(pair_features))
pair_features.head()

wallet_to_actor = pd.concat([
    wallet_tx.dropna(subset=["actor_from"])[["from_wallet","actor_from"]].rename(columns={"from_wallet":"wallet","actor_from":"actor"}),
    wallet_tx.dropna(subset=["actor_to"])[["to_wallet","actor_to"]].rename(columns={"to_wallet":"wallet","actor_to":"actor"})
]).drop_duplicates()
cluster_actor_counts = wallet_to_actor.groupby("wallet")["actor"].nunique()

# How many actors touch each transaction_cluster value overall?
cluster_membership = wallet_tx.dropna(subset=["transaction_cluster"]).groupby("transaction_cluster").apply(
    lambda df: set(df["actor_from"].dropna()) | set(df["actor_to"].dropna())
)
cluster_sizes = cluster_membership.apply(len)
print(cluster_sizes.sort_values(ascending=False).head(15))

import re

def extract_actor_pair(cluster):
    if pd.isna(cluster):
        return None
    actors_found = re.findall(r"ACT_\d+", str(cluster))
    return tuple(sorted(set(actors_found))) if len(set(actors_found)) > 1 else None

wallet_tx["cluster_actor_pair"] = wallet_tx["transaction_cluster"].apply(extract_actor_pair)
named_cluster_values = set(wallet_tx.dropna(subset=["cluster_actor_pair"])["transaction_cluster"])
print("Named (meaningful) clusters:", named_cluster_values)

def get_named_clusters(actor):
    a_clusters = set(wallet_tx[wallet_tx["actor_from"]==actor]["transaction_cluster"].dropna()) | \
                 set(wallet_tx[wallet_tx["actor_to"]==actor]["transaction_cluster"].dropna())
    return a_clusters & named_cluster_values

named_wallet_clusters = {a: get_named_clusters(a) for a in actors}

def get_named_clusters(actor):
    a_clusters = set(wallet_tx[wallet_tx["actor_from"]==actor]["transaction_cluster"].dropna()) | \
                 set(wallet_tx[wallet_tx["actor_to"]==actor]["transaction_cluster"].dropna())
    return a_clusters & named_cluster_values

named_wallet_clusters = {a: get_named_clusters(a) for a in actors}

def compute_features(a, b):
    feats = {}

    if a in style_profile.index and b in style_profile.index:
        feats["stylometric_distance"] = euclidean(style_profile.loc[a], style_profile.loc[b])
    else:
        feats["stylometric_distance"] = np.nan

    if a in hour_dist.index and b in hour_dist.index:
        feats["behavior_similarity"] = 1 - cosine(hour_dist[a], hour_dist[b])
    else:
        feats["behavior_similarity"] = np.nan

    feats["shared_pgp"] = int(len(pgp_sets[a] & pgp_sets[b]) > 0)
    feats["shared_infra"] = int(len(infra_sets[a] & infra_sets[b]) > 0)
    feats["shared_wallet_cluster"] = int(len(named_wallet_clusters[a] & named_wallet_clusters[b]) > 0)

    shared_handle_overlap = 0
    for h in handle_sets[a] & handle_sets[b]:
        rows_a = identifiers[(identifiers["actor_id"]==a) & (identifiers["identifier_value"]==h)]
        rows_b = identifiers[(identifiers["actor_id"]==b) & (identifiers["identifier_value"]==h)]
        for _, ra in rows_a.iterrows():
            for _, rb in rows_b.iterrows():
                if not (ra["last_seen"] < rb["first_seen"] or rb["last_seen"] < ra["first_seen"]):
                    shared_handle_overlap = 1
    feats["shared_handle_with_overlap"] = shared_handle_overlap

    feats["evidence_count"] = feats["shared_pgp"] + feats["shared_infra"] + feats["shared_handle_with_overlap"]

    return feats

rows = []
for a, b in combinations(actors, 2):
    f = compute_features(a, b)
    f["actor_a"] = a
    f["actor_b"] = b
    rows.append(f)

pair_features = pd.DataFrame(rows)
print("Total pairs:", len(pair_features))
print("\nPairs with shared_wallet_cluster=1:", pair_features["shared_wallet_cluster"].sum())
pair_features.head()

def extract_actor_pair(cluster):
    if pd.isna(cluster):
        return None
    actors_found = re.findall(r"ACT_\d+", str(cluster))
    return tuple(sorted(set(actors_found))) if len(set(actors_found)) > 1 else None

def extract_prefix(cluster):
    match = re.match(r"CLUSTER_([A-Z]+)_", str(cluster))
    return match.group(1) if match else None

# Make sure both columns exist on wallet_tx
wallet_tx["cluster_actor_pair"] = wallet_tx["transaction_cluster"].apply(extract_actor_pair)
wallet_tx["cluster_prefix"] = wallet_tx["transaction_cluster"].apply(extract_prefix)

named_pairs = wallet_tx.dropna(subset=["cluster_actor_pair"])[["cluster_actor_pair", "cluster_prefix"]].drop_duplicates()
print(f"Named pairs rebuilt: {len(named_pairs)}")
display(named_pairs)

label_map = {}
for a, b in named_pairs[named_pairs["cluster_prefix"].isin(["STRO","MEDI"])]["cluster_actor_pair"]:
    label_map[tuple(sorted([a,b]))] = 1
for a, b in named_pairs[named_pairs["cluster_prefix"]=="SHAR"]["cluster_actor_pair"]:
    label_map[tuple(sorted([a,b]))] = 0

pair_features["pair_key"] = pair_features.apply(lambda r: tuple(sorted([r["actor_a"], r["actor_b"]])), axis=1)
pair_features["label"] = pair_features["pair_key"].map(label_map)

labeled = pair_features.dropna(subset=["label"])
print(f"Labeled pairs: {len(labeled)} out of {len(pair_features)} total")
labeled[["actor_a","actor_b","shared_pgp","shared_infra","shared_wallet_cluster","shared_handle_with_overlap","evidence_count","stylometric_distance","label"]].sort_values("label", ascending=False)

labeled_full = pair_features.dropna(subset=["label"])
labeled_full[["actor_a","actor_b","behavior_similarity","stylometric_distance","evidence_count","label"]].sort_values("label", ascending=False)

# Weak label: 1 for confirmed pairs, 0 for everything else (weak assumption: most pairs are unrelated)
pair_features["weak_label"] = pair_features["label"].fillna(0)

print(pair_features["weak_label"].value_counts())

!pip install -q sentence-transformers

from sentence_transformers import SentenceTransformer

embed_model = SentenceTransformer('all-MiniLM-L6-v2')

import numpy as np

actor_embeddings = {}

for actor_id in actors:
    actor_posts = posts[posts["actor_id"] == actor_id]["content"].dropna().tolist()
    if len(actor_posts) == 0:
        actor_embeddings[actor_id] = None
        continue
    post_vecs = embed_model.encode(actor_posts, show_progress_bar=False)
    actor_embeddings[actor_id] = np.mean(post_vecs, axis=0)  # average embedding = actor's "semantic fingerprint"

print("Actors embedded:", sum(1 for v in actor_embeddings.values() if v is not None))
print("Embedding dimension:", len(next(v for v in actor_embeddings.values() if v is not None)))

from sklearn.metrics.pairwise import cosine_similarity

def embedding_similarity(a, b):
    vec_a, vec_b = actor_embeddings.get(a), actor_embeddings.get(b)
    if vec_a is None or vec_b is None:
        return np.nan
    return float(cosine_similarity(vec_a.reshape(1,-1), vec_b.reshape(1,-1))[0][0])

pair_features["embedding_similarity"] = pair_features.apply(
    lambda r: embedding_similarity(r["actor_a"], r["actor_b"]), axis=1
)

pair_features[["actor_a","actor_b","stylometric_distance","embedding_similarity"]].head()

labeled_check = pair_features.dropna(subset=["label"])
labeled_check[["actor_a","actor_b","embedding_similarity","stylometric_distance","behavior_similarity","evidence_count","label"]].sort_values("label", ascending=False)

#model training
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

feature_cols = ["stylometric_distance", "behavior_similarity", "embedding_similarity",
                 "shared_pgp", "shared_infra", "shared_wallet_cluster",
                 "shared_handle_with_overlap", "evidence_count"]

X = pair_features[feature_cols].fillna(0)
y = pair_features["weak_label"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)   # needed for Logistic Regression; RF doesn't need itm

logreg = LogisticRegression(max_iter=1000, class_weight="balanced")
logreg.fit(X_scaled, y)

print("Logistic Regression coefficients:")
for name, coef in sorted(zip(feature_cols, logreg.coef_[0]), key=lambda t: -abs(t[1])):
    print(f"  {name}: {coef:.3f}")

rf = RandomForestClassifier(n_estimators=300, max_depth=6, class_weight="balanced", random_state=42)
rf.fit(X, y)   # RF doesn't need scaling

print("Random Forest feature importances:")
for name, imp in sorted(zip(feature_cols, rf.feature_importances_), key=lambda t: -t[1]):
    print(f"  {name}: {imp:.3f}")

labeled_idx = pair_features.dropna(subset=["label"]).index

X_known = X.loc[labeled_idx]
X_known_scaled = scaler.transform(X_known)

validation = pair_features.loc[labeled_idx, ["actor_a","actor_b","label"]].copy()
validation["logreg_probability"] = logreg.predict_proba(X_known_scaled)[:, 1]
validation["rf_probability"] = rf.predict_proba(X_known)[:, 1]

print(validation.sort_values("label", ascending=False))

print("Random Forest feature importances:")
for name, imp in sorted(zip(feature_cols, rf.feature_importances_), key=lambda t: -t[1]):
    print(f"  {name}: {imp:.3f}")

print(pair_features["shared_handle_with_overlap"].value_counts())

!pip install -q shap
import shap

explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X_known)  # X_known =  11 labeled pairs from before

# shap_values shape depends on sklearn/shap version — this handles both binary-output formats
if isinstance(shap_values, list):
    shap_vals_positive = shap_values[1]
else:
    shap_vals_positive = shap_values[:, :, 1] if shap_values.ndim == 3 else shap_values

shap.summary_plot(shap_vals_positive, X_known, feature_names=feature_cols)

for i, idx in enumerate(labeled_idx):
    row = pair_features.loc[idx]
    print(f"\n{row['actor_a']} vs {row['actor_b']} — label={row['label']}, RF probability={rf.predict_proba(X.loc[[idx]])[:,1][0]:.3f}")
    contributions = sorted(zip(feature_cols, shap_vals_positive[i]), key=lambda t: -abs(t[1]))
    for name, val in contributions[:3]:
        direction = "pushed UP" if val > 0 else "pushed DOWN"
        print(f"   {name}: {direction} by {abs(val):.3f}")

feature_cols_no_wallet = ["stylometric_distance", "behavior_similarity", "embedding_similarity",
                           "shared_pgp", "shared_infra", "shared_handle_with_overlap", "evidence_count"]

X2 = pair_features[feature_cols_no_wallet].fillna(0)
rf2 = RandomForestClassifier(n_estimators=300, max_depth=6, class_weight="balanced", random_state=42)
rf2.fit(X2, y)

X2_known = X2.loc[labeled_idx]
probs2 = rf2.predict_proba(X2_known)[:, 1]
comparison = pair_features.loc[labeled_idx, ["actor_a","actor_b","label"]].copy()
comparison["rf_with_wallet"] = rf.predict_proba(X.loc[labeled_idx])[:,1]
comparison["rf_without_wallet"] = probs2
print(comparison.sort_values("label", ascending=False))

import numpy as np

# Build a consistent per-actor behavioral feature matrix
behavior_rows = []
for a in actors:
    posting_freq = len(timeline[timeline["actor_id"] == a])
    avg_hour = timeline[timeline["actor_id"] == a]["hour"].mean() if a in timeline["actor_id"].values else np.nan
    hour_std = timeline[timeline["actor_id"] == a]["hour"].std() if a in timeline["actor_id"].values else np.nan
    n_migrations = len(timeline[(timeline["actor_id"] == a) & (timeline["event_type"].isin(["MIGRATION","HANDLE_CHANGE"]))])
    behavior_rows.append([a, posting_freq, avg_hour, hour_std, n_migrations])

behavior_df = pd.DataFrame(behavior_rows, columns=["actor_id", "posting_freq", "avg_hour", "hour_std", "n_migrations"]).fillna(0)
behavior_df = behavior_df.set_index("actor_id")
behavior_df.head()

# training K-means and isolation forest .
#  the previous model selected was random forest neither logistic regression nor sentence-BRET Nerural Network
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

scaler_kmeans = StandardScaler()
behavior_scaled = scaler_kmeans.fit_transform(behavior_df)

kmeans = KMeans(n_clusters=5, n_init=10, random_state=42)
behavior_df["cluster"] = kmeans.fit_predict(behavior_scaled)

print(behavior_df["cluster"].value_counts())
behavior_df.head(10)

from sklearn.ensemble import IsolationForest

iso = IsolationForest(contamination=0.15, random_state=42)
iso.fit(behavior_scaled)
behavior_df["anomaly_score"] = iso.decision_function(behavior_scaled)
behavior_df["is_anomalous"] = iso.predict(behavior_scaled) == -1

print(f"Actors flagged as anomalous: {behavior_df['is_anomalous'].sum()} out of {len(behavior_df)}")
behavior_df.sort_values("anomaly_score").head(10)

for a, b in named_pairs["cluster_actor_pair"]:
    a_anom = behavior_df.loc[a, "is_anomalous"] if a in behavior_df.index else None
    b_anom = behavior_df.loc[b, "is_anomalous"] if b in behavior_df.index else None
    print(f"{a}: {a_anom}  |  {b}: {b_anom}")

def kmeans_features(a, b):
    same_cluster = int(behavior_df.loc[a, "cluster"] == behavior_df.loc[b, "cluster"]) if a in behavior_df.index and b in behavior_df.index else 0
    return same_cluster

def isolation_features(a, b):
    if a not in behavior_df.index or b not in behavior_df.index:
        return 0, 0.0
    both_anomalous = int(behavior_df.loc[a, "is_anomalous"] and behavior_df.loc[b, "is_anomalous"])
    anomaly_score_diff = abs(behavior_df.loc[a, "anomaly_score"] - behavior_df.loc[b, "anomaly_score"])
    return both_anomalous, anomaly_score_diff

pair_features["same_kmeans_cluster"] = pair_features.apply(lambda r: kmeans_features(r["actor_a"], r["actor_b"]), axis=1)
iso_results = pair_features.apply(lambda r: isolation_features(r["actor_a"], r["actor_b"]), axis=1)
pair_features["both_anomalous"] = iso_results.apply(lambda t: t[0])
pair_features["anomaly_score_diff"] = iso_results.apply(lambda t: t[1])

pair_features[["actor_a","actor_b","same_kmeans_cluster","both_anomalous","anomaly_score_diff"]].head()

# For actors with a migration event, compute posting frequency in the 14 days before vs after
migration_actors = timeline[timeline["event_type"]=="MIGRATION"]["actor_id"].unique()
print(f"Actors with at least one MIGRATION event: {len(migration_actors)}")

migration_events = timeline[timeline["event_type"]=="MIGRATION"].copy()
migration_events["timestamp"] = pd.to_datetime(migration_events["timestamp"])
timeline["timestamp"] = pd.to_datetime(timeline["timestamp"])

# Take the FIRST migration event per actor as the transition point
first_migration = migration_events.sort_values("timestamp").groupby("actor_id").first()["timestamp"]

window_days = 14
behavior_shift_rows = []

for actor_id, migration_time in first_migration.items():
    actor_events = timeline[timeline["actor_id"] == actor_id]

    before = actor_events[(actor_events["timestamp"] >= migration_time - pd.Timedelta(days=window_days)) &
                            (actor_events["timestamp"] < migration_time)]
    after = actor_events[(actor_events["timestamp"] >= migration_time) &
                           (actor_events["timestamp"] < migration_time + pd.Timedelta(days=window_days))]

    freq_before, freq_after = len(before), len(after)
    hour_before = before["hour"].mean() if len(before) > 0 else np.nan
    hour_after = after["hour"].mean() if len(after) > 0 else np.nan

    behavior_shift_rows.append({
        "actor_id": actor_id,
        "freq_before": freq_before,
        "freq_after": freq_after,
        "freq_change": freq_after - freq_before,
        "hour_before": hour_before,
        "hour_after": hour_after,
        "hour_shift": abs(hour_after - hour_before) if not (pd.isna(hour_before) or pd.isna(hour_after)) else np.nan,
    })

behavior_shift_df = pd.DataFrame(behavior_shift_rows).set_index("actor_id")
behavior_shift_df.head(10)

shift_features = behavior_shift_df[["freq_change", "hour_shift"]].fillna(0)
scaler_shift = StandardScaler()
shift_scaled = scaler_shift.fit_transform(shift_features)

iso_shift = IsolationForest(contamination=0.2, random_state=42)
iso_shift.fit(shift_scaled)
behavior_shift_df["shift_anomaly_score"] = iso_shift.decision_function(shift_scaled)
behavior_shift_df["shift_is_anomalous"] = iso_shift.predict(shift_scaled) == -1

print(f"Actors with anomalous behavior SHIFT: {behavior_shift_df['shift_is_anomalous'].sum()} out of {len(behavior_shift_df)}")
behavior_shift_df.sort_values("shift_anomaly_score").head(10)

for a, b in named_pairs["cluster_actor_pair"]:
    a_shift = behavior_shift_df.loc[a, "shift_is_anomalous"] if a in behavior_shift_df.index else "no migration"
    b_shift = behavior_shift_df.loc[b, "shift_is_anomalous"] if b in behavior_shift_df.index else "no migration"
    print(f"{a}: {a_shift}  |  {b}: {b_shift}")

""" Final random forest training - it includes stylometric_distance, behavior_similarity, embedding_similarity, shared_pgp, shared_infra, shared_handle_with_overlap, evidence_count, same_kmeans_cluster — 8 features, all validated to contribute real, generalizable signal."""
from sklearn.ensemble import RandomForestClassifier

FINAL_FEATURES = [
    "stylometric_distance", "behavior_similarity", "embedding_similarity",
    "shared_pgp", "shared_infra", "shared_handle_with_overlap",
    "evidence_count", "same_kmeans_cluster"
]

X_final = pair_features[FINAL_FEATURES].fillna(0)
y_final = pair_features["weak_label"]

rf_final = RandomForestClassifier(n_estimators=300, max_depth=6, class_weight="balanced", random_state=42)
rf_final.fit(X_final, y_final)

print("Feature importances:")
for name, imp in sorted(zip(FINAL_FEATURES, rf_final.feature_importances_), key=lambda t: -t[1]):
    print(f"  {name}: {imp:.3f}")

X_known_final = X_final.loc[labeled_idx]
probs_final = rf_final.predict_proba(X_known_final)[:, 1]

validation_final = pair_features.loc[labeled_idx, ["actor_a", "actor_b", "label"]].copy()
validation_final["rf_probability"] = probs_final
print(validation_final.sort_values("label", ascending=False))

import shap
import json

explainer_final = shap.TreeExplainer(rf_final)

def attribution_engine(actor_a, actor_b, feature_row):
    x = feature_row[FINAL_FEATURES].to_frame().T.astype(float)
    prob = rf_final.predict_proba(x)[0, 1]

    shap_vals = explainer_final.shap_values(x)
    shap_vals = shap_vals[1][0] if isinstance(shap_vals, list) else (shap_vals[0][:, 1] if shap_vals.ndim == 3 else shap_vals[0])

    contributions = sorted(zip(FINAL_FEATURES, shap_vals), key=lambda t: -abs(t[1]))
    top_evidence = [
        {"feature": name, "effect": "supports_match" if val > 0 else "against_match", "impact": round(float(val), 3)}
        for name, val in contributions[:4] if abs(val) > 0.005
    ]

    confidence_band = "high" if prob >= 0.75 else "moderate" if prob >= 0.5 else "weak" if prob >= 0.2 else "very_low"

    return {
        "persona_a": actor_a,
        "persona_b": actor_b,
        "relationship_probability": round(float(prob), 3),
        "confidence_band": confidence_band,
        "top_contributing_evidence": top_evidence,
    }

# Test on your known pairs
results = [attribution_engine(row["actor_a"], row["actor_b"], row) for _, row in pair_features.loc[labeled_idx].iterrows()]
print(json.dumps(results[:3], indent=2))

import joblib

joblib.dump(rf_final, "rf_final.joblib")

import json

with open("model_features.json", "w") as f:
    json.dump(FINAL_FEATURES, f)

joblib.dump(rf_final, "rf_final.joblib")
from google.colab import files

files.download("rf_final.joblib")
files.download("model_features.json")
