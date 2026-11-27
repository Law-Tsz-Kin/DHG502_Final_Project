#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_yan_qin_network.py
=======================
Visualisation for the DHG502 Yan-Qin SNA corpus.

Reads:
    data/nodes.csv
    data/edges.csv
    outputs/centrality_rankings.csv   (computed by sna_analysis.py)

Writes (outputs/, 300 DPI PNG):
    network_full.png            - full graph, node size = weighted degree
    network_person_only.png     - person-person subgraph
    network_by_phase.png        - 2x2 phase-filtered panels (P1..P4)

Design:
  * Node colour  = polity (Yan/Qin/Zhao_Dai/Qi/Chu/Wei/Xiongnu/Other)
  * Node shape   = node_type (person = circle, state = square, allusion = diamond)
  * Node size    = weighted_total_degree (floor keeps small nodes legible)
  * Edge style   = edge_type (colour) x valence (solid=positive, dashed=negative,
                  dotted=neutral)
  * CJK fonts    - tries Microsoft JhengHei (Windows), PingFang HK (macOS),
                   Noto Sans CJK TC (Linux / bundled ./fonts copy) so Traditional
                   Chinese never renders as tofu boxes.
"""

from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")  # headless-safe
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
from matplotlib.lines import Line2D
import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
FONT_DIR = ROOT / "fonts"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# CJK font configuration
# ---------------------------------------------------------------------------
def configure_cjk_fonts() -> str:
    """Register CJK-capable fonts across platforms and return the chosen family.

    Priority: Microsoft JhengHei (Windows) > PingFang HK (macOS) >
              Noto Sans CJK TC (Linux; bundled copy in ./fonts as fallback).
    """
    candidates = [
        "Microsoft JhengHei",     # Windows
        "PingFang HK",            # macOS
        "Noto Sans CJK TC",       # Linux (fonts-noto-cjk)
        "Noto Sans TC",
        "Source Han Sans TC",
        "WenQuanYi Micro Hei",
    ]
    # register the bundled Noto font if present (guarantees a CJK fallback)
    if FONT_DIR.exists():
        for f in FONT_DIR.glob("*.otf"):
            font_manager.fontManager.addfont(str(f))
    installed = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in installed), None)
    if chosen is None:
        # last resort: any registered font whose name mentions CJK/TC
        cjk = [n for n in installed if any(k in n for k in
                                           ("CJK", "TC", "Hei", "PingFang"))]
        chosen = cjk[0] if cjk else "sans-serif"
        print(f"WARNING: no preferred CJK font found; using '{chosen}'. "
              "Chinese labels may render as boxes.")
    else:
        print(f"CJK font selected: {chosen}")
    plt.rcParams["font.family"] = [chosen, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


# ---------------------------------------------------------------------------
# Style maps
# ---------------------------------------------------------------------------
POLITY_COLORS = {
    "Yan":      "#1f77b4",   # blue
    "Qin":      "#d62728",   # red
    "Zhao_Dai": "#2ca02c",   # green
    "Qi":       "#9467bd",   # purple
    "Chu":      "#ff7f0e",   # orange
    "Wei":      "#8c564b",   # brown
    "Xiongnu":  "#e377c2",   # pink
    "Other":    "#7f7f7f",   # grey
}
NODE_MARKERS = {"person": "o", "state": "s", "allusion": "D"}
EDGE_COLORS = {
    "diplomatic_attempt":    "#1f77b4",
    "hostage_tie":           "#9467bd",
    "conspiracy_brokerage":  "#d62728",
    "sacrifice_resource":    "#ff7f0e",
    "military_conflict":     "#7f7f7f",
    "allusion_reference":    "#2ca02c",
}
VALENCE_STYLES = {"positive": "-", "negative": "--", "neutral": ":"}
SIZE_FLOOR = 2600         # minimum node area - large enough to hold text
SIZE_SCALE = 260          # area units per unit of weighted degree


def node_size(wdeg: float) -> float:
    return SIZE_FLOOR + SIZE_SCALE * float(wdeg)


def spread_positions(pos: dict, sizes: dict, iters: int = 600,
                     pad: float = 1.38):
    """Iteratively push node pairs apart until every pair of node discs no
    longer overlaps (repulsion-only relaxation, ignoring edges). `sizes` maps
    node -> matplotlib node area (points^2); radius ~ sqrt(area)/2."""
    import math
    nodes = list(pos)
    radii = {n: math.sqrt(sizes[n]) / 2.0 * pad for n in nodes}
    for _ in range(iters):
        moved = False
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                dx = pos[b][0] - pos[a][0]
                dy = pos[b][1] - pos[a][1]
                d = math.hypot(dx, dy) or 1e-9
                min_d = radii[a] + radii[b]
                if d < min_d:
                    push = (min_d - d) / 2.0
                    ux, uy = dx / d, dy / d
                    pos[a][0] -= ux * push
                    pos[a][1] -= uy * push
                    pos[b][0] += ux * push
                    pos[b][1] += uy * push
                    moved = True
        if not moved:
            break
    return pos


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data():
    nodes = pd.read_csv(DATA / "nodes.csv", encoding="utf-8")
    edges = pd.read_csv(DATA / "edges.csv", encoding="utf-8")
    rank_file = OUT / "centrality_rankings.csv"
    rank = (pd.read_csv(rank_file, encoding="utf-8")
            if rank_file.exists() else None)
    if rank is None:
        print("NOTE: outputs/centrality_rankings.csv not found - "
              "computing weighted degree from edges.csv instead.")
        w = (edges.groupby(["source_node", "target_node"]).size()
             .rename("w").reset_index())
        wdeg = pd.concat([w.groupby("source_node")["w"].sum(),
                          w.groupby("target_node")["w"].sum()]) \
             .groupby(level=0).sum().rename("weighted_total_degree")
        rank = nodes[["node_id"]].merge(wdeg, left_on="node_id",
                                        right_index=True, how="left").fillna(0)
        rank["betweenness"] = 0.0
    return nodes, edges, rank


def build_graph(nodes: pd.DataFrame, edges: pd.DataFrame,
                person_only: bool = False, phase: str | None = None):
    """Aggregated DiGraph; weight = number of attestation rows."""
    sub = edges
    if person_only:
        persons = set(nodes.loc[nodes["node_type"] == "person", "node_id"])
        sub = sub[sub["source_node"].isin(persons)
                  & sub["target_node"].isin(persons)]
    if phase is not None:
        sub = sub[sub["phase"] == phase]
    g = nx.DiGraph()
    for _, r in nodes.iterrows():
        g.add_node(r["node_id"], label_zh=r["label_zh"], node_type=r["node_type"],
                   polity=r["polity"])
    agg = (sub.groupby(["source_node", "target_node"], as_index=False)
              .size().rename(columns={"size": "weight"}))
    for _, r in agg.iterrows():
        g.add_edge(r["source_node"], r["target_node"], weight=int(r["weight"]))
    # keep only nodes that participate in this slice
    g.remove_nodes_from([n for n in list(g.nodes) if g.degree(n) == 0])
    # per-edge attestation metadata for styling (dominant type/valence)
    for u, v in g.edges:
        rows = sub[(sub["source_node"] == u) & (sub["target_node"] == v)]
        g.edges[u, v]["edge_type"] = (rows["edge_type"].mode().iat[0]
                                      if not rows["edge_type"].mode().empty
                                      else "military_conflict")
        g.edges[u, v]["valence"] = (rows["valence"].mode().iat[0]
                                    if not rows["valence"].mode().empty
                                    else "neutral")
    return g, sub


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
def draw_network(g: nx.DiGraph, rank: pd.DataFrame, title: str,
                 outfile: Path, figsize=(20, 16), label_min_degree: int = 1,
                 seed: int = 42):
    if len(g) == 0:
        print(f"SKIP {outfile.name}: empty graph")
        return
    pos = nx.spring_layout(g, k=5.2 / max(1, len(g) ** 0.5), seed=seed,
                           weight=None, iterations=500)

    r = rank.set_index("node_id")
    sizes, colors, shapes = [], [], []
    for n in g.nodes:
        wdeg = r["weighted_total_degree"].get(n, 0) if n in r.index else 0
        sizes.append(node_size(wdeg))
        colors.append(POLITY_COLORS.get(g.nodes[n]["polity"],
                                        POLITY_COLORS["Other"]))
        shapes.append(NODE_MARKERS.get(g.nodes[n]["node_type"], "o"))
    # guarantee no two node shapes overlap (labels live inside the shapes)
    size_map = {n: s for n, s in zip(g.nodes, sizes)}
    pos = spread_positions(pos, size_map)

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor("#fafafa")

    # edges grouped by (edge_type, valence) so each style is drawn once
    seen = set()
    for u, v, d in g.edges(data=True):
        key = (d["edge_type"], d["valence"])
        style = VALENCE_STYLES.get(d["valence"], ":")
        nx.draw_networkx_edges(
            g, pos, edgelist=[(u, v)], ax=ax,
            edge_color=EDGE_COLORS.get(d["edge_type"], "#bbbbbb"),
            style=style, width=0.5 + 0.3 * min(d["weight"], 6),
            alpha=0.42, arrows=True, arrowsize=9,
            connectionstyle="arc3,rad=0.06")
        seen.add(key)

    # draw nodes by marker shape so each type gets its own scatter call
    for marker in set(shapes):
        idx = [i for i, s in enumerate(shapes) if s == marker]
        ns = [list(g.nodes)[i] for i in idx]
        nx.draw_networkx_nodes(
            g, pos, nodelist=ns, ax=ax, node_shape=marker,
            node_color=[colors[i] for i in idx],
            node_size=[sizes[i] for i in idx],
            edgecolors="black", linewidths=1.2, alpha=0.95)

    # labels INSIDE the node shapes: white text centred on the node,
    # font size scaled to the node area so text always fits inside.
    for n, (x, y) in pos.items():
        wdeg = r["weighted_total_degree"].get(n, 0) if n in r.index else 0
        area = node_size(wdeg)
        # fit text inside the shape: estimate char width ~ fontsize (CJK),
        # keep text width <= ~80% of the node's inner width
        label = g.nodes[n]["label_zh"]
        fs = max(8.0, min(16.0, 0.82 * (area ** 0.5) / max(2, len(label))))
        ax.text(x, y, label,
                fontsize=fs, ha="center", va="center",
                color="white", fontweight="bold", zorder=6,
                family=plt.rcParams["font.family"][0])

    ax.set_title(title, fontsize=22, pad=14)
    ax.axis("off")

    # ---- legends ----
    polity_handles = [mpatches.Patch(color=c, label=p)
                      for p, c in POLITY_COLORS.items()
                      if p in {g.nodes[n]["polity"] for n in g.nodes}]
    type_handles = [Line2D([0], [0], marker=m, color="w", label=t,
                           markerfacecolor="#cccccc", markeredgecolor="black",
                           markersize=10, linestyle="")
                    for t, m in NODE_MARKERS.items()
                    if t in {g.nodes[n]["node_type"] for n in g.nodes}]
    edge_handles = []
    for et, c in EDGE_COLORS.items():
        if et in {d["edge_type"] for _, _, d in g.edges(data=True)}:
            edge_handles.append(Line2D([0], [0], color=c, lw=2, label=et))
    val_handles = [Line2D([0], [0], color="#555555", lw=2, ls=ls, label=v)
                   for v, ls in VALENCE_STYLES.items()
                   if v in {d["valence"] for _, _, d in g.edges(data=True)}]
    leg1 = ax.legend(handles=polity_handles, title="Polity", loc="upper left",
                     fontsize=13, title_fontsize=14, framealpha=0.9)
    ax.add_artist(leg1)
    ax.legend(handles=type_handles + edge_handles + val_handles,
              title="Node type / Edge type / Valence",
              loc="lower left", fontsize=12, title_fontsize=13,
              framealpha=0.9, ncol=2)
    fig.text(0.99, 0.01,
             "node size = weighted degree (attestation count)  |  "
             "solid=positive  dashed=negative  dotted=neutral",
             ha="right", fontsize=13, color="#444444")

    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {outfile}  (nodes={len(g)}, edges={g.number_of_edges()})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    configure_cjk_fonts()
    nodes, edges, rank = load_data()

    # 1. full graph
    g_full, _ = build_graph(nodes, edges)
    draw_network(g_full, rank,
                 "燕秦關係網路全圖 (Full Yan–Qin Network, 90 nodes)\n"
                 "node size = weighted degree; colour = polity; "
                 "shape = node type",
                 OUT / "network_full.png")

    # 2. person-only subgraph
    g_p, _ = build_graph(nodes, edges, person_only=True)
    draw_network(g_p, rank,
                 "人物子圖 (Person-only Subgraph)\n"
                 "edges connect two person nodes only",
                 OUT / "network_person_only.png", figsize=(17, 14))

    # 3. phase-filtered 2x2 panels
    phases = ["P1_pre_diplomacy", "P2_alliance_vs_plot",
              "P3_assassination", "P4_fall_of_yan"]
    fig, axes = plt.subplots(2, 2, figsize=(24, 19))
    for ax, ph in zip(axes.flat, phases):
        g_ph, sub = build_graph(nodes, edges, phase=ph)
        if len(g_ph) == 0:
            ax.set_title(f"{ph}\n(no edges)")
            ax.axis("off")
            continue
        pos = nx.spring_layout(g_ph, k=6.0 / max(1, len(g_ph) ** 0.5),
                               seed=42, weight=None, iterations=500)
        r = rank.set_index("node_id")
        sizes = [node_size(r["weighted_total_degree"].get(n, 0)
                           if n in r.index else 0) * 0.55 for n in g_ph]
        colors = [POLITY_COLORS.get(g_ph.nodes[n]["polity"],
                                    POLITY_COLORS["Other"]) for n in g_ph]
        size_map = {n: s for n, s in zip(g_ph.nodes, sizes)}
        pos = spread_positions(pos, size_map)
        for u, v, d in g_ph.edges(data=True):
            nx.draw_networkx_edges(
                g_ph, pos, edgelist=[(u, v)], ax=ax,
                edge_color=EDGE_COLORS.get(d["edge_type"], "#bbbbbb"),
                style=VALENCE_STYLES.get(d["valence"], ":"),
                width=0.5 + 0.3 * min(d["weight"], 6), alpha=0.55,
                arrows=True, arrowsize=7, connectionstyle="arc3,rad=0.08")
        nx.draw_networkx_nodes(g_ph, pos, ax=ax, node_size=sizes,
                               node_color=colors, edgecolors="black",
                               linewidths=0.7, alpha=0.92)
        for n, (x, y) in pos.items():
            wdeg = r["weighted_total_degree"].get(n, 0) if n in r.index else 0
            area = node_size(wdeg) * 0.55
            label = g_ph.nodes[n]["label_zh"]
            fs = max(8.0, min(14.0, 0.82 * (area ** 0.5) / max(2, len(label))))
            ax.text(x, y, label,
                    fontsize=fs, ha="center", va="center",
                    color="white", fontweight="bold", zorder=6,
                    family=plt.rcParams["font.family"][0])
        ax.set_title(f"{ph}  (edges rows={len(sub)}, nodes={len(g_ph)})",
                     fontsize=17)
        ax.axis("off")
    # shared legend
    handles = [mpatches.Patch(color=c, label=p) for p, c in POLITY_COLORS.items()]
    handles += [Line2D([0], [0], color=c, lw=2, label=et)
                for et, c in EDGE_COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=7, fontsize=13,
               framealpha=0.9)
    fig.suptitle("分期網路比較 (Phase-filtered Networks P1–P4)", fontsize=22)
    fig.tight_layout(rect=[0, 0.05, 1, 0.97])
    fig.savefig(OUT / "network_by_phase.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {OUT / 'network_by_phase.png'}")


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    main()
