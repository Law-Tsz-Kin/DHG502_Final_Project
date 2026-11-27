#!/usr/bin/env python3
"""SNA analysis for the DHG502 Classical Chinese corpus network.

Reads ``data/nodes.csv`` and ``data/edges.csv`` and produces four families of
analytical tables (saved as CSV under ``analysis/``):

1. Global summary      - nodes / edges / components / density for the full
                         multi-layer graph and the person-only subgraph.
2. Centrality rankings - Degree, Weighted Degree (strength) and Betweenness
                         for every node; top-15 tables per metric.
3. Temporal & historiographical slices - the network sliced by narrative
                         ``phase`` and by ``text_source``, with a focus table
                         tracking key actors/brokers across slices.
4. Deduplication check - edge weights and centrality rankings before vs after
                         collapsing parallel edges across sources.

Graph-building conventions (documented because they affect the numbers):

* The raw edge list contains parallel edges: the same pair of actors may be
  linked by several ``edge_type`` values and by several ``text_source``
  values (each row is one textually-evidenced interaction).
* ``G_multi``  : MultiDiGraph preserving every edge record.
* ``G_simple`` : DiGraph projection (parallel edges collapsed); the number of
                 collapsed records is stored as the ``weight`` attribute.
  Density and connected components are computed on this projection, because
  MultiGraph density is not bounded by 1 and would over-count parallel edges.
* "Degree"      = number of distinct neighbours (simple projection).
* "Weighted degree" (strength) = sum of edge weights = total edge records
                 involving the node (parallel edges counted).
* "Betweenness" = unweighted, normalized, on the simple directed projection.

Usage::

    python3 scripts/analyze_network.py            # from project root
    cd scripts && python3 analyze_network.py      # or from scripts/

Only ``pandas``, ``networkx`` and the standard library are used.
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUT_DIR = PROJECT_ROOT / "analysis"

NODES_CSV = DATA_DIR / "nodes.csv"
EDGES_CSV = DATA_DIR / "edges.csv"

# Canonical phase order (chronological) and source order (as in the corpus).
PHASES = [
    "P1_pre227_diplomacy",
    "P2_alliance_vs_plot",
    "P3_assassination_227",
    "P4_fall_of_yan_228_221",
]
SOURCES = ["ZGC", "Shiji_34", "Shiji_43", "Shiji_86", "Shiji_06", "Shiji_73", "ZZTJ"]

# Actors the project brief asks to track across phases and texts.
KEY_ACTORS = [
    "Yue_Jian",      # 樂間/樂閒 - Yan lord of Changguo, defected to Zhao
    "Jiang_Qu",      # 將渠 - Yan minister who opposed the Zhao campaign
    "Ju_Xin",        # 劇辛 - Yan commander killed by Pang Nuan
    "Li_Mu",         # 李牧 - Zhao general attacking Yan
    "Ju_Wu",         # 鞠武/鞫武 - Crown Prince Dan's Grand Tutor
    "Tian_Guang",    # 田光 - recluse who recommended Jing Ke
    "Fan_Yuqi",      # 樊於期 - defected Qin general
    "Dai_King_Jia",  # 代王嘉 - King of Dai (Prince Jia of Zhao)
]

TOP_N = 15


# ---------------------------------------------------------------------------
# Data loading and graph construction
# ---------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load nodes and edges as DataFrames with string dtypes for IDs."""
    nodes = pd.read_csv(NODES_CSV, encoding="utf-8-sig", dtype=str)
    edges = pd.read_csv(
        EDGES_CSV,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,   # keep empty cells as "" not NaN
    )
    # Basic sanity checks - fail loudly if the schema drifts.
    expected_edge_cols = {
        "source_node", "target_node", "edge_type", "valence", "status",
        "phase", "text_source", "segment_id", "evidence_quote",
    }
    missing = expected_edge_cols - set(edges.columns)
    if missing:
        raise SystemExit(f"edges.csv is missing columns: {sorted(missing)}")
    if nodes["node_id"].duplicated().any():
        raise SystemExit("nodes.csv contains duplicate node_id values")
    return nodes, edges


def build_graphs(edges: pd.DataFrame, nodes: pd.DataFrame):
    """Build the multi graph, the weighted simple projection and subgraphs.

    Returns
    -------
    (G_multi, G_simple, G_person, person_ids)
        G_multi   : MultiDiGraph, one edge per record.
        G_simple  : DiGraph with ``weight`` = number of collapsed records.
        G_person  : person-only induced subgraph of G_simple.
        person_ids: set of person node ids.
    """
    node_meta = nodes.set_index("node_id")

    # --- MultiDiGraph: every edge record preserved -------------------------
    G_multi = nx.MultiDiGraph()
    for node_id, row in node_meta.iterrows():
        G_multi.add_node(node_id, label_zh=row["label_zh"], label_en=row["label_en"],
                         node_type=row["node_type"], polity=row["polity"])
    for r in edges.itertuples(index=False):
        G_multi.add_edge(r.source_node, r.target_node,
                         edge_type=r.edge_type, valence=r.valence,
                         status=r.status, phase=r.phase,
                         text_source=r.text_source, segment_id=r.segment_id)

    # --- Simple weighted projection ----------------------------------------
    # Group parallel edges (same u, v - direction preserved) and count them.
    # NOTE: deduplication for analysis 4 groups by (u, v, edge_type); this
    # projection is coarser (u, v only) and is used for density/components.
    counts = edges.groupby(["source_node", "target_node"], sort=False).size()
    G_simple = nx.DiGraph()
    G_simple.add_nodes_from(G_multi.nodes(data=True))
    for (u, v), w in counts.items():
        G_simple.add_edge(u, v, weight=int(w))

    # --- Person-only subgraph ----------------------------------------------
    person_ids = set(node_meta.index[node_meta["node_type"] == "person"])
    G_person = G_simple.subgraph(person_ids).copy()

    return G_multi, G_simple, G_person, person_ids


# ---------------------------------------------------------------------------
# 1. Global network summary
# ---------------------------------------------------------------------------
def global_summary(G_multi: nx.MultiDiGraph, G_simple: nx.DiGraph,
                   G_person: nx.DiGraph, edges: pd.DataFrame) -> pd.DataFrame:
    """Nodes / edges / components / density for full and person-only graphs."""
    def describe(name: str, G: nx.DiGraph, n_edges: int) -> dict:
        n = G.number_of_nodes()
        # Weakly connected components treat the directed graph as undirected;
        # strongly connected components respect edge direction.
        wcc = nx.number_weakly_connected_components(G)
        scc = nx.number_strongly_connected_components(G)
        return {
            "graph": name,
            "nodes": n,
            "edges": n_edges,
            "weakly_connected_components": wcc,
            "strongly_connected_components": scc,
            "density": round(nx.density(G), 6),
        }

    rows = [
        # NOTE: the simple projection collapses parallel records, so its edge
        # count (144) is smaller than the raw record count (290). Density is
        # computed on this projection, so the edge count shown must match it.
        describe("full_multi_layer (simple projection)", G_simple,
                 G_simple.number_of_edges()),
        describe("full_multi_layer (MultiDiGraph, raw records)", G_multi,
                 G_multi.number_of_edges()),
        describe("person_only_subgraph", G_person,
                 G_person.number_of_edges()),
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Centrality rankings
# ---------------------------------------------------------------------------
def centrality_table(G_simple: nx.DiGraph) -> pd.DataFrame:
    """Degree, weighted degree (strength) and betweenness for every node."""
    # Degree = distinct neighbours (in + out, self-loops impossible here).
    degree = dict(G_simple.degree())
    # Weighted degree = sum of parallel-edge counts (= total edge records).
    weighted_degree = dict(G_simple.degree(weight="weight"))
    # Betweenness: unweighted shortest paths on the directed projection.
    betweenness = nx.betweenness_centrality(G_simple, normalized=True,
                                            weight=None)

    df = pd.DataFrame({
        "node_id": list(G_simple.nodes()),
        "degree": pd.Series(degree),
        "weighted_degree": pd.Series(weighted_degree),
        "betweenness": pd.Series(betweenness),
    })
    return df


def export_centrality(cent: pd.DataFrame, nodes: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Attach labels and write top-15 tables for each metric."""
    meta = nodes.set_index("node_id")[["label_zh", "label_en", "node_type", "polity"]]
    cent = cent.join(meta, on="node_id")

    metric_cols = {
        "degree": "degree",
        "weighted_degree": "weighted_degree",
        "betweenness": "betweenness",
    }
    outputs = {}
    for metric, col in metric_cols.items():
        top = (cent.sort_values(col, ascending=False)
                   .head(TOP_N)
                   .reset_index(drop=True))
        top.insert(0, "rank", top.index + 1)
        fname = f"02_centrality_{metric}_top{TOP_N}.csv"
        top.to_csv(OUT_DIR / fname, index=False, encoding="utf-8-sig")
        outputs[metric] = top

    # Full table for every node (useful for plotting / appendix).
    cent.sort_values("weighted_degree", ascending=False).to_csv(
        OUT_DIR / "02_centrality_all_nodes.csv",
        index=False, encoding="utf-8-sig")
    return outputs


# ---------------------------------------------------------------------------
# 3. Temporal & historiographical slices
# ---------------------------------------------------------------------------
def slice_stats(sub_edges: pd.DataFrame, label_col: str, label: str,
                nodes: pd.DataFrame) -> dict:
    """Summary + top actors for one slice of the edge list."""
    meta = nodes.set_index("node_id")
    pair_counts = sub_edges.groupby(["source_node", "target_node"]).size()
    G = nx.DiGraph()
    G.add_nodes_from(meta.index)                 # keep all nodes for density
    for (u, v), w in pair_counts.items():
        G.add_edge(u, v, weight=int(w))

    # Degree within the slice counts only interactions attested in this slice.
    deg = dict(G.degree())
    bet = nx.betweenness_centrality(G, normalized=True, weight=None)

    top = (pd.Series(deg).sort_values(ascending=False).head(5))
    return {
        "slice_type": label_col,
        "slice": label,
        "edges": len(sub_edges),
        "active_nodes": int((pd.Series(deg) > 0).sum()),
        "density": round(nx.density(G), 6),
        "top5_by_degree": "; ".join(f"{n}({d})" for n, d in top.items()),
        "_degree": deg,
        "_betweenness": bet,
    }


def slice_tables(edges: pd.DataFrame, nodes: pd.DataFrame):
    """Build per-phase and per-source slice summaries + key-actor pivots."""
    # ---- slice summaries ---------------------------------------------------
    slice_rows = []
    for phase in PHASES:
        sub = edges[edges["phase"] == phase]
        if len(sub):
            slice_rows.append(slice_stats(sub, "phase", phase, nodes))
    for src in SOURCES:
        sub = edges[edges["text_source"] == src]
        if len(sub):
            slice_rows.append(slice_stats(sub, "text_source", src, nodes))
    slice_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")}
                             for r in slice_rows])
    slice_df.to_csv(OUT_DIR / "03_slice_summaries.csv",
                    index=False, encoding="utf-8-sig")

    # ---- key-actor tracking across slices ----------------------------------
    # Long format: one row per (slice, actor) with participation counts and
    # within-slice centrality. Actors absent from a slice are omitted.
    long_rows = []
    for r in slice_rows:
        deg, bet = r["_degree"], r["_betweenness"]
        sub = (edges[edges["phase"] == r["slice"]]
               if r["slice_type"] == "phase"
               else edges[edges["text_source"] == r["slice"]])
        for actor in KEY_ACTORS:
            as_src = int((sub["source_node"] == actor).sum())
            as_tgt = int((sub["target_node"] == actor).sum())
            if as_src == 0 and as_tgt == 0:
                continue
            long_rows.append({
                "slice_type": r["slice_type"],
                "slice": r["slice"],
                "actor": actor,
                "edges_as_source": as_src,
                "edges_as_target": as_tgt,
                "total_edges": as_src + as_tgt,
                "degree_in_slice": deg.get(actor, 0),
                "betweenness_in_slice": round(bet.get(actor, 0.0), 6),
            })
    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(OUT_DIR / "03_key_actors_long.csv",
                   index=False, encoding="utf-8-sig")

    # ---- wide pivots for quick reading --------------------------------------
    for col, fname in [("phase", "03_key_actors_by_phase.csv"),
                       ("text_source", "03_key_actors_by_source.csv")]:
        sub = long_df[long_df["slice_type"] == col]
        if sub.empty:
            continue
        order = PHASES if col == "phase" else SOURCES
        pivot = (sub.pivot_table(index="actor", columns="slice",
                                 values="total_edges", aggfunc="sum",
                                 fill_value=0)
                    .reindex(columns=[c for c in order if c in sub["slice"].unique()],
                             fill_value=0)
                    .reindex(KEY_ACTORS, fill_value=0))
        pivot.to_csv(OUT_DIR / fname, encoding="utf-8-sig")
    return slice_df, long_df


# ---------------------------------------------------------------------------
# 4. Deduplication check
# ---------------------------------------------------------------------------
def dedup_check(edges: pd.DataFrame, nodes: pd.DataFrame):
    """Compare the raw network with its cross-source deduplicated version.

    Deduplication key: (source_node, target_node, edge_type). The collapsed
    edge keeps ``weight`` = number of records and ``n_sources`` = number of
    distinct ``text_source`` values backing it.
    """
    meta = nodes.set_index("node_id")

    # ---- deduplicated edge table -------------------------------------------
    grp = edges.groupby(["source_node", "target_node", "edge_type"], sort=False)
    dedup = grp.agg(
        weight=("segment_id", "size"),
        n_sources=("text_source", "nunique"),
        sources=("text_source", lambda s: "|".join(sorted(set(s)))),
        segment_ids=("segment_id", lambda s: "|".join(sorted(set(s)))),
    ).reset_index()
    dedup.to_csv(OUT_DIR / "04_dedup_edges.csv", index=False, encoding="utf-8-sig")

    # ---- graphs before / after ---------------------------------------------
    # BEFORE: every record is its own edge; degree counts parallel records.
    G_before = nx.MultiDiGraph()
    G_before.add_nodes_from(meta.index)
    for r in edges.itertuples(index=False):
        G_before.add_edge(r.source_node, r.target_node)

    # AFTER: one edge per (u, v, edge_type) with weight = record count.
    G_after = nx.MultiDiGraph()
    G_after.add_nodes_from(meta.index)
    for r in dedup.itertuples(index=False):
        G_after.add_edge(r.source_node, r.target_node,
                         key=r.edge_type, weight=int(r.weight))

    # Simple projections for comparable metrics.
    def simple(G: nx.MultiDiGraph, weighted: bool) -> nx.DiGraph:
        H = nx.DiGraph()
        H.add_nodes_from(G.nodes())
        for u, v, k, d in G.edges(keys=True, data=True):
            w = d.get("weight", 1) if weighted else 1
            if H.has_edge(u, v):
                H[u][v]["weight"] += w
            else:
                H.add_edge(u, v, weight=w)
        return H

    S_before = simple(G_before, weighted=False)   # all weights 1
    S_after = simple(G_after, weighted=True)      # weights = record counts

    deg_before = dict(G_before.degree())                       # records counted
    deg_after = dict(S_after.degree())                         # distinct partners
    wdeg_before = dict(S_before.degree(weight="weight"))       # == records
    wdeg_after = dict(S_after.degree(weight="weight"))
    bet_before = nx.betweenness_centrality(S_before, normalized=True)
    bet_after = nx.betweenness_centrality(S_after, normalized=True)

    comp = pd.DataFrame({
        "node_id": list(meta.index),
        "degree_raw_records": pd.Series(deg_before),
        "degree_dedup_partners": pd.Series(deg_after),
        "weighted_degree": pd.Series(wdeg_after),
        "betweenness_raw": pd.Series(bet_before).round(6),
        "betweenness_dedup": pd.Series(bet_after).round(6),
    })
    # Rank nodes by raw degree and by dedup degree; report rank movement.
    comp["rank_raw"] = comp["degree_raw_records"].rank(ascending=False,
                                                       method="min").astype(int)
    comp["rank_dedup"] = comp["degree_dedup_partners"].rank(
        ascending=False, method="min").astype(int)
    comp["rank_shift"] = comp["rank_raw"] - comp["rank_dedup"]
    comp = comp.join(meta[["label_zh", "label_en", "node_type"]], on="node_id")
    comp.sort_values("rank_raw").to_csv(
        OUT_DIR / "04_dedup_centrality_comparison.csv",
        index=False, encoding="utf-8-sig")

    # ---- console-facing summary --------------------------------------------
    w = dedup["weight"]
    stats = {
        "records_before": len(edges),
        "edges_after_dedup": len(dedup),
        "collapsed_away": len(edges) - len(dedup),
        "triples_with_weight_gt1": int((w > 1).sum()),
        "max_weight": int(w.max()),
        "mean_weight": round(float(w.mean()), 3),
        "triples_multi_source": int((dedup["n_sources"] > 1).sum()),
        "max_sources": int(dedup["n_sources"].max()),
    }
    return dedup, comp, stats


# ---------------------------------------------------------------------------
# Console reporting
# ---------------------------------------------------------------------------
def report(summary: pd.DataFrame, cent: pd.DataFrame, tops: dict,
           slice_df: pd.DataFrame, long_df: pd.DataFrame,
           dedup: pd.DataFrame, comp: pd.DataFrame, dstats: dict) -> None:
    sep = "=" * 72
    print(sep)
    print("1. GLOBAL NETWORK SUMMARY")
    print(sep)
    print(summary.to_string(index=False))

    print("\n" + sep)
    print("2. CENTRALITY - TOP {n} PER METRIC".format(n=TOP_N))
    print(sep)
    for metric, top in tops.items():
        print(f"\n--- {metric} ---")
        cols = ["rank", "node_id", "label_zh", metric]
        print(top[cols].to_string(index=False))

    print("\n" + sep)
    print("3. SLICE SUMMARIES (phase / text_source)")
    print(sep)
    print(slice_df.to_string(index=False))

    print("\n--- key actors: total edges per phase ---")
    piv_phase = (long_df[long_df["slice_type"] == "phase"]
                 .pivot_table(index="actor", columns="slice",
                              values="total_edges", aggfunc="sum", fill_value=0))
    piv_phase = piv_phase.reindex(columns=PHASES, fill_value=0)
    print(piv_phase.reindex(KEY_ACTORS, fill_value=0).to_string())

    print("\n--- key actors: total edges per text source ---")
    piv_src = (long_df[long_df["slice_type"] == "text_source"]
               .pivot_table(index="actor", columns="slice",
                            values="total_edges", aggfunc="sum", fill_value=0))
    piv_src = piv_src.reindex(columns=SOURCES, fill_value=0)
    print(piv_src.reindex(KEY_ACTORS, fill_value=0).to_string())

    print("\n" + sep)
    print("4. DEDUPLICATION CHECK")
    print(sep)
    for k, v in dstats.items():
        print(f"  {k:<28}: {v}")

    movers = comp[comp["rank_shift"] != 0].sort_values("rank_shift",
                                                       ascending=False)
    print(f"\n  nodes whose degree rank changes after dedup: {len(movers)}")
    if len(movers):
        show = movers[["node_id", "label_zh", "degree_raw_records",
                       "degree_dedup_partners", "rank_raw", "rank_dedup",
                       "rank_shift"]]
        print(show.head(12).to_string(index=False))

    print("\nOutput directory:", OUT_DIR)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    nodes, edges = load_data()
    G_multi, G_simple, G_person, _ = build_graphs(edges, nodes)

    # 1. global summary
    summary = global_summary(G_multi, G_simple, G_person, edges)
    summary.to_csv(OUT_DIR / "01_global_summary.csv",
                   index=False, encoding="utf-8-sig")

    # 2. centrality
    cent = centrality_table(G_simple)
    tops = export_centrality(cent, nodes)

    # 3. slices
    slice_df, long_df = slice_tables(edges, nodes)

    # 4. dedup
    dedup, comp, dstats = dedup_check(edges, nodes)

    report(summary, cent, tops, slice_df, long_df, dedup, comp, dstats)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(f"ERROR: required input file not found: {exc}", file=sys.stderr)
        raise SystemExit(1)
