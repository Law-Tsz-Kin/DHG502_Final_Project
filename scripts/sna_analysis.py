#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sna_analysis.py
===============
Social Network Analysis for the DHG502 Yan-Qin corpus.

Inputs  (data/):
    nodes.csv  - node_id,label_zh,node_type,polity,functional_role,first_phase
    edges.csv  - source_node,target_node,edge_type,valence,phase,text_source,
                 segment_id,evidence_quote

Outputs (outputs/):
    global_summary.csv       - network-level metrics (full graph + person-only)
    centrality_rankings.csv  - per-node centrality measures (full table)
    top15_centralities.csv   - Top-15 by Degree / Weighted Degree / Betweenness
    phase_comparison.csv     - per-phase degree & betweenness for key actors
    source_comparison.csv    - per-source degree & betweenness for key actors
    dedup_comparison.csv     - edge/node totals & ranking shifts before/after
                               deduplication by (source,target,edge_type)

Design notes:
  * The edge table is a MULTI-edge list: the same (source,target) pair can
    appear many times (one row per attestation). For centrality we therefore
    build a DiGraph whose edge weight = number of attestation rows, and a
    MultiDiGraph view is kept for phase/source slicing.
  * "Weighted degree" = sum of attestation counts (parallel-edge multiplicity),
    i.e. how often a node participates in attested interactions.
  * Betweenness is computed on the weighted DiGraph with weight = 1/weight
    (so frequently-attested ties are "shorter"), normalized to [0, 1].
  * Key actors are matched against whatever canonical IDs actually exist in
    nodes.csv (e.g. Dai_Wang_Jia rather than Dai_King_Jia), with a console
    note for any requested ID that is absent.
"""

from pathlib import Path
import sys

import pandas as pd
import networkx as nx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

NODES_FILE = DATA / "nodes.csv"
EDGES_FILE = DATA / "edges.csv"

PHASES = ["P1_pre_diplomacy", "P2_alliance_vs_plot",
          "P3_assassination", "P4_fall_of_yan"]
SOURCES = ["ZGC", "Shiji", "ZZTJ"]

# Requested key actors; resolved against nodes.csv at runtime.
REQUESTED_ACTORS = [
    "Yue_Jian", "Jiang_Qu", "Ju_Xin", "Li_Mu", "Ju_Wu", "Tian_Guang",
    "Fan_Yuqi", "Yan_Dan", "Jing_Ke", "Qin_Shi_Huang", "Dai_King_Jia",
    "Dai_Wang_Jia",  # canonical ID for King Jia of Dai in this corpus
]


# ---------------------------------------------------------------------------
# 1. Load & integrity audit
# ---------------------------------------------------------------------------
def load_and_audit():
    nodes = pd.read_csv(NODES_FILE, encoding="utf-8")
    edges = pd.read_csv(EDGES_FILE, encoding="utf-8")

    print("=" * 70)
    print("1. INTEGRITY AUDIT")
    print("=" * 70)
    print(f"nodes.csv : {len(nodes)} rows, columns = {list(nodes.columns)}")
    print(f"edges.csv : {len(edges)} rows, columns = {list(edges.columns)}")

    node_ids = set(nodes["node_id"])
    orphans = set(edges["source_node"]) | set(edges["target_node"])
    orphans -= node_ids
    if orphans:
        print(f"WARNING - orphan endpoints not in nodes.csv: {sorted(orphans)}")
    else:
        print("OK - every edge endpoint exists in nodes.csv")

    # isolated nodes (degree == 0 in the full multigraph)
    deg = pd.concat([
        edges["source_node"].value_counts(),
        edges["target_node"].value_counts(),
    ]).groupby(level=0).sum()
    isolated = sorted(node_ids - set(deg.index))
    if isolated:
        print(f"WARNING - isolated nodes (degree == 0): {isolated}")
    else:
        print("OK - no isolated nodes")

    # duplicate attestations on the full key
    dup_key = ["source_node", "target_node", "edge_type", "segment_id"]
    dups = edges[edges.duplicated(subset=dup_key, keep=False)]
    if len(dups):
        print(f"WARNING - {len(dups)} duplicate rows on {dup_key}:")
        print(dups[dup_key].to_string(index=False))
    else:
        print(f"OK - no duplicate rows on {dup_key}")

    # optional-column graceful handling
    for col, default in [("valence", "neutral"), ("phase", None),
                         ("text_source", None), ("evidence_quote", "")]:
        if col not in edges.columns:
            print(f"NOTE - edges.csv lacks column '{col}'; filling with {default!r}")
            edges[col] = default
    for col in ["node_type", "polity", "functional_role", "first_phase"]:
        if col not in nodes.columns:
            print(f"NOTE - nodes.csv lacks column '{col}'; filling with 'Unknown'")
            nodes[col] = "Unknown"

    return nodes, edges


# ---------------------------------------------------------------------------
# 2. Graph builders
# ---------------------------------------------------------------------------
def build_graphs(nodes: pd.DataFrame, edges: pd.DataFrame):
    """Full multigraph + aggregated weighted DiGraph + person-only subgraph."""
    multi = nx.MultiDiGraph()
    for _, r in nodes.iterrows():
        multi.add_node(r["node_id"], **{k: r[k] for k in
                                        ("label_zh", "node_type", "polity",
                                         "functional_role", "first_phase")})
    for _, e in edges.iterrows():
        multi.add_edge(e["source_node"], e["target_node"],
                       edge_type=e["edge_type"], valence=e["valence"],
                       phase=e["phase"], text_source=e["text_source"],
                       segment_id=e["segment_id"])

    # aggregate parallel edges -> weight = attestation count
    agg = (edges.groupby(["source_node", "target_node"], as_index=False)
                .size().rename(columns={"size": "weight"}))
    di = nx.DiGraph()
    di.add_nodes_from(multi.nodes(data=True))
    for _, r in agg.iterrows():
        di.add_edge(r["source_node"], r["target_node"], weight=int(r["weight"]))

    # person-only subgraph: person nodes + edges whose BOTH endpoints are persons
    persons = set(nodes.loc[nodes["node_type"] == "person", "node_id"])
    p_edges = edges[edges["source_node"].isin(persons)
                    & edges["target_node"].isin(persons)]
    p_multi = multi.subgraph(persons).copy()
    # rebuild person-only aggregated DiGraph from p_edges
    p_agg = (p_edges.groupby(["source_node", "target_node"], as_index=False)
                    .size().rename(columns={"size": "weight"}))
    p_di = nx.DiGraph()
    p_di.add_nodes_from((n, multi.nodes[n]) for n in persons if n in multi)
    for _, r in p_agg.iterrows():
        p_di.add_edge(r["source_node"], r["target_node"], weight=int(r["weight"]))

    return multi, di, p_multi, p_di, p_edges


def graph_summary(G: nx.Graph, label: str) -> dict:
    n, m = G.number_of_nodes(), G.number_of_edges()
    if n == 0:
        return {"graph": label, "nodes": 0, "edges": 0,
                "weakly_connected_components": 0,
                "strongly_connected_components": 0, "density": 0.0}
    wcc = nx.number_weakly_connected_components(G)
    scc = nx.number_strongly_connected_components(G)
    density = nx.density(G)
    print(f"\n[{label}] nodes={n}  edges={m}  WCC={wcc}  SCC={scc}  "
          f"density={density:.6f}")
    return {"graph": label, "nodes": n, "edges": m,
            "weakly_connected_components": wcc,
            "strongly_connected_components": scc, "density": round(density, 6)}


# ---------------------------------------------------------------------------
# 3. Centrality tables
# ---------------------------------------------------------------------------
def centrality_table(di: nx.DiGraph, multi: nx.MultiDiGraph) -> pd.DataFrame:
    """In/Out/Total degree (distinct partners) + weighted (attestation) degree
    + betweenness on the weighted graph."""
    rows = []
    # betweenness with distance = 1/weight (frequent ties are shorter)
    dist = {(u, v): 1.0 / d["weight"] for u, v, d in di.edges(data=True)}
    nx.set_edge_attributes(di, dist, "dist")
    bet = nx.betweenness_centrality(di, weight="dist", normalized=True)

    for n in di.nodes:
        w_in = sum(d["weight"] for _, _, d in di.in_edges(n, data=True))
        w_out = sum(d["weight"] for _, _, d in di.out_edges(n, data=True))
        rows.append({
            "node_id": n,
            "label_zh": multi.nodes[n].get("label_zh", ""),
            "node_type": multi.nodes[n].get("node_type", ""),
            "polity": multi.nodes[n].get("polity", ""),
            "in_degree": di.in_degree(n),
            "out_degree": di.out_degree(n),
            "total_degree": di.degree(n),
            "weighted_in_degree": w_in,
            "weighted_out_degree": w_out,
            "weighted_total_degree": w_in + w_out,
            "betweenness": round(bet.get(n, 0.0), 6),
        })
    return pd.DataFrame(rows).sort_values(
        "weighted_total_degree", ascending=False).reset_index(drop=True)


def top15(rank: pd.DataFrame) -> pd.DataFrame:
    """Top-15 summary for Degree, Weighted Degree, Betweenness."""
    out = []
    for metric, col in [("total_degree", "total_degree"),
                        ("weighted_total_degree", "weighted_total_degree"),
                        ("betweenness", "betweenness")]:
        top = rank.nlargest(15, col)[["node_id", "label_zh", "node_type",
                                      "polity", col]]
        top = top.reset_index(drop=True)
        top.insert(0, "rank", top.index + 1)
        top.insert(1, "metric", metric)
        top = top.rename(columns={col: "value"})
        out.append(top)
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------------------
# 4. Temporal & historiographical comparisons
# ---------------------------------------------------------------------------
def slice_metrics(edges: pd.DataFrame, nodes: pd.DataFrame,
                  key_col: str, values: list, actors: list) -> pd.DataFrame:
    """For each slice value, build the aggregated DiGraph of that slice and
    record degree/betweenness for the key actors."""
    rows = []
    for val in values:
        sub = edges[edges[key_col] == val]
        if sub.empty:
            continue
        g = nx.DiGraph()
        agg = (sub.groupby(["source_node", "target_node"], as_index=False)
                  .size().rename(columns={"size": "weight"}))
        for _, r in agg.iterrows():
            g.add_edge(r["source_node"], r["target_node"],
                       weight=int(r["weight"]))
        dist = {(u, v): 1.0 / d["weight"] for u, v, d in g.edges(data=True)}
        nx.set_edge_attributes(g, dist, "dist")
        bet = nx.betweenness_centrality(g, weight="dist", normalized=True)
        for a in actors:
            if a not in g:
                continue
            w_in = sum(d["weight"] for _, _, d in g.in_edges(a, data=True))
            w_out = sum(d["weight"] for _, _, d in g.out_edges(a, data=True))
            rows.append({
                key_col: val, "node_id": a,
                "label_zh": nodes.set_index("node_id").loc[a, "label_zh"]
                if a in nodes.set_index("node_id").index else "",
                "in_degree": g.in_degree(a), "out_degree": g.out_degree(a),
                "total_degree": g.degree(a),
                "weighted_in_degree": w_in, "weighted_out_degree": w_out,
                "weighted_total_degree": w_in + w_out,
                "betweenness": round(bet.get(a, 0.0), 6),
                "slice_edges": int(len(sub)),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. Deduplication check
# ---------------------------------------------------------------------------
def dedup_check(nodes: pd.DataFrame, edges: pd.DataFrame,
                rank_full: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collapse attestations to one row per (source,target,edge_type), recording
    source_count / segment_count; compare totals & top rankings."""
    dedup = (edges.groupby(["source_node", "target_node", "edge_type"],
                           as_index=False)
                  .agg(source_count=("text_source", "nunique"),
                       segment_count=("segment_id", "nunique"),
                       valence=("valence", "first"),
                       phase=("phase", "first"),
                       text_source=("text_source", "first"),
                       segment_id=("segment_id", "first"),
                       evidence_quote=("evidence_quote", "first")))
    # keep the FIRST attestation's quote/segment for auditability
    dedup = dedup[["source_node", "target_node", "edge_type", "valence",
                   "phase", "text_source", "segment_id", "evidence_quote",
                   "source_count", "segment_count"]]
    dedup.to_csv(OUT / "deduplicated_edges.csv", index=False,
                 encoding="utf-8-sig")

    # deduplicated weighted graph
    g = nx.DiGraph()
    for _, r in dedup.iterrows():
        g.add_edge(r["source_node"], r["target_node"],
                   weight=int(r["source_count"]))
    dist = {(u, v): 1.0 / d["weight"] for u, v, d in g.edges(data=True)}
    nx.set_edge_attributes(g, dist, "dist")
    bet = nx.betweenness_centrality(g, weight="dist", normalized=True)

    rows = []
    for n in g.nodes:
        w_in = sum(d["weight"] for _, _, d in g.in_edges(n, data=True))
        w_out = sum(d["weight"] for _, _, d in g.out_edges(n, data=True))
        rows.append({"node_id": n,
                     "weighted_total_degree_dedup": w_in + w_out,
                     "betweenness_dedup": round(bet.get(n, 0.0), 6)})
    rank_dedup = pd.DataFrame(rows).sort_values(
        "weighted_total_degree_dedup", ascending=False).reset_index(drop=True)

    # comparison table: full vs dedup totals + per-node rank shifts
    comp_edges = pd.DataFrame([
        {"view": "full_attestations", "edge_rows": len(edges),
         "unique_pairs": edges[["source_node", "target_node"]]
         .drop_duplicates().shape[0]},
        {"view": "dedup_by_type", "edge_rows": len(dedup),
         "unique_pairs": dedup[["source_node", "target_node"]]
         .drop_duplicates().shape[0]},
    ])

    full = rank_full[["node_id", "weighted_total_degree", "betweenness"]].copy()
    full.columns = ["node_id", "wtd_deg_full", "betweenness_full"]
    comp = full.merge(rank_dedup, on="node_id", how="outer").fillna(0)
    comp["wtd_deg_delta"] = comp["weighted_total_degree_dedup"] - comp["wtd_deg_full"]
    comp["rank_full"] = comp["wtd_deg_full"].rank(ascending=False,
                                                  method="min").astype(int)
    comp["rank_dedup"] = comp["weighted_total_degree_dedup"].rank(
        ascending=False, method="min").astype(int)
    comp["rank_shift"] = comp["rank_full"] - comp["rank_dedup"]
    comp = comp.sort_values("weighted_total_degree_dedup",
                            ascending=False).reset_index(drop=True)
    return dedup, comp


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    nodes, edges = load_and_audit()

    # resolve requested key actors against actual node_ids
    present = [a for a in REQUESTED_ACTORS if a in set(nodes["node_id"])]
    missing = [a for a in REQUESTED_ACTORS if a not in set(nodes["node_id"])]
    print("\nKey actors resolved:", present)
    if missing:
        print("Key actors NOT in nodes.csv (skipped):", missing)

    multi, di, p_multi, p_di, p_edges = build_graphs(nodes, edges)

    # ---- 2. global summary ------------------------------------------------
    print("\n" + "=" * 70)
    print("2. GLOBAL NETWORK SUMMARY")
    print("=" * 70)
    summary = [graph_summary(di, "full_graph_aggregated"),
               graph_summary(p_di, "person_only_subgraph")]
    # multi-edge counts for reference
    summary[0]["edge_rows_attestations"] = len(edges)
    summary[1]["edge_rows_attestations"] = len(p_edges)
    pd.DataFrame(summary).to_csv(OUT / "global_summary.csv", index=False,
                                 encoding="utf-8-sig")
    print(f"saved {OUT / 'global_summary.csv'}")

    # ---- 3. centrality ----------------------------------------------------
    print("\n" + "=" * 70)
    print("3. CENTRALITY RANKINGS")
    print("=" * 70)
    rank = centrality_table(di, multi)
    rank.to_csv(OUT / "centrality_rankings.csv", index=False,
                encoding="utf-8-sig")
    top15(rank).to_csv(OUT / "top15_centralities.csv", index=False,
                       encoding="utf-8-sig")
    print(f"saved {OUT / 'centrality_rankings.csv'} "
          f"({len(rank)} nodes)")
    print("\nTop 5 by weighted total degree:")
    print(rank.head(5)[["node_id", "label_zh", "weighted_total_degree",
                        "betweenness"]].to_string(index=False))

    # ---- 4. phase & source comparisons ------------------------------------
    print("\n" + "=" * 70)
    print("4. TEMPORAL & HISTORIOGRAPHICAL COMPARISONS")
    print("=" * 70)
    phase_cmp = slice_metrics(edges, nodes, "phase", PHASES, present)
    phase_cmp.to_csv(OUT / "phase_comparison.csv", index=False,
                     encoding="utf-8-sig")
    print(f"saved {OUT / 'phase_comparison.csv'} ({len(phase_cmp)} rows)")
    if not phase_cmp.empty:
        pivot = phase_cmp.pivot_table(index="node_id", columns="phase",
                                      values="weighted_total_degree",
                                      fill_value=0)
        print("\nWeighted degree by phase (key actors):")
        print(pivot.to_string())

    source_cmp = slice_metrics(edges, nodes, "text_source", SOURCES, present)
    source_cmp.to_csv(OUT / "source_comparison.csv", index=False,
                      encoding="utf-8-sig")
    print(f"\nsaved {OUT / 'source_comparison.csv'} ({len(source_cmp)} rows)")
    if not source_cmp.empty:
        pivot = source_cmp.pivot_table(index="node_id", columns="text_source",
                                       values="weighted_total_degree",
                                       fill_value=0)
        print("\nWeighted degree by source (key actors):")
        print(pivot.to_string())

    # ---- 5. deduplication --------------------------------------------------
    print("\n" + "=" * 70)
    print("5. DEDUPLICATION CHECK")
    print("=" * 70)
    dedup, comp = dedup_check(nodes, edges, rank)
    comp.to_csv(OUT / "dedup_comparison.csv", index=False,
                encoding="utf-8-sig")
    print(f"saved {OUT / 'dedup_comparison.csv'} ({len(comp)} rows)")
    print(f"saved {OUT / 'deduplicated_edges.csv'} ({len(dedup)} rows)")
    print("\nEdge totals before/after dedup:")
    print(comp_edges_table(edges, dedup).to_string(index=False))
    print("\nTop 10 rank shifts (full -> dedup):")
    print(comp.head(10)[["node_id", "wtd_deg_full",
                         "weighted_total_degree_dedup",
                         "rank_shift"]].to_string(index=False))

    print("\nAll outputs written to", OUT)


def comp_edges_table(edges: pd.DataFrame, dedup: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([
        {"view": "full_attestations", "rows": len(edges)},
        {"view": "dedup_by_(src,tgt,edge_type)", "rows": len(dedup)},
    ])


if __name__ == "__main__":
    sys.exit(main())
