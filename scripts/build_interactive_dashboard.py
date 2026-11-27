#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_interactive_dashboard.py
==============================
Builds a single self-contained HTML dashboard (outputs/dashboard.html) with
separated "pages" (tab navigation) of interactive Plotly charts for the
Yan-Qin SNA corpus, and regenerates screen-friendly resized PNGs.

Pages:
  1. Overview        - global summary cards + edge-type / valence / phase bars
  2. Network Graph   - interactive network (spring layout, hover = node details)
  3. Centrality      - Top-15 bars for degree / weighted degree / betweenness
  4. Phase Timeline  - key-actor weighted degree across P1..P4
  5. Source Compare  - key-actor weighted degree across ZGC / Shiji / ZZTJ
  6. Static Maps     - the resized high-res PNG figures

Also writes resized PNGs (outputs/png_resized/) at ~2000 px wide for clear
on-screen viewing, keeping the 300 DPI originals untouched.
"""

from pathlib import Path
import json
import base64

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
RESIZED = OUT / "png_resized"
RESIZED.mkdir(exist_ok=True)

PHASES = ["P1_pre_diplomacy", "P2_alliance_vs_plot",
          "P3_assassination", "P4_fall_of_yan"]
PHASE_SHORT = {"P1_pre_diplomacy": "P1", "P2_alliance_vs_plot": "P2",
               "P3_assassination": "P3", "P4_fall_of_yan": "P4"}
SOURCES = ["ZGC", "Shiji", "ZZTJ"]

POLITY_COLORS = {
    "Yan": "#1f77b4", "Qin": "#d62728", "Zhao_Dai": "#2ca02c",
    "Qi": "#9467bd", "Chu": "#ff7f0e", "Wei": "#8c564b",
    "Xiongnu": "#e377c2", "Other": "#7f7f7f",
}
EDGE_COLORS = {
    "diplomatic_attempt": "#1f77b4", "hostage_tie": "#9467bd",
    "conspiracy_brokerage": "#d62728", "sacrifice_resource": "#ff7f0e",
    "military_conflict": "#7f7f7f", "allusion_reference": "#2ca02c",
}

KEY_ACTORS = ["Yan_Dan", "Jing_Ke", "Qin_Shi_Huang", "Ju_Wu", "Tian_Guang",
              "Fan_Yuqi", "Jiang_Qu", "Ju_Xin", "Li_Mu", "Dai_Wang_Jia",
              "Yan_Wang_Xi", "Wang_Jian", "Le_Jian"]


# ---------------------------------------------------------------------------
# Resize PNGs for clear on-screen viewing
# ---------------------------------------------------------------------------
def resize_pngs(target_width: int = 2600) -> list[dict]:
    """Downscale the 300-DPI figures to ~target_width px wide (LANCZOS),
    keeping aspect ratio, then apply a mild unsharp mask so labels stay crisp
    after downsampling. Returns metadata for the dashboard."""
    from PIL import ImageFilter
    metas = []
    titles = {
        "network_full.png": "Full Network (90 nodes / 148 edges)",
        "network_person_only.png": "Person-only Subgraph (50 nodes / 73 edges)",
        "network_by_phase.png": "Phase-filtered Networks P1–P4",
    }
    for png in sorted(OUT.glob("network_*.png")):
        im = Image.open(png).convert("RGB")
        w, h = im.size
        if w > target_width:
            nh = round(h * target_width / w)
            im = im.resize((target_width, nh), Image.LANCZOS)
            # mild sharpening compensates for LANCZOS softening of text
            im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=90,
                                                   threshold=2))
        dest = RESIZED / png.name
        im.save(dest, "PNG", optimize=True)
        metas.append({"file": dest.name, "title": titles.get(png.name, png.name),
                      "orig": f"{w}×{h}", "new": f"{im.size[0]}×{im.size[1]}"})
        print(f"resized {png.name}: {w}×{h} -> {im.size[0]}×{im.size[1]}")
    return metas


# ---------------------------------------------------------------------------
# Chart builders (each returns a Plotly figure)
# ---------------------------------------------------------------------------
def fig_overview_bars(edges: pd.DataFrame) -> list[go.Figure]:
    figs = []
    # edge types
    et = edges["edge_type"].value_counts().reset_index()
    et.columns = ["edge_type", "count"]
    figs.append(go.Figure(go.Bar(
        x=et["count"], y=et["edge_type"], orientation="h",
        marker_color=[EDGE_COLORS.get(t, "#888") for t in et["edge_type"]],
        text=et["count"], textposition="outside"))
        .update_layout(title="Edges by Type (329 attestations)",
                       xaxis_title="attestation rows", height=380,
                       margin=dict(l=150, r=20, t=50, b=40)))
    # valence
    va = edges["valence"].value_counts().reset_index()
    va.columns = ["valence", "count"]
    figs.append(go.Figure(go.Pie(labels=va["valence"], values=va["count"],
                                 hole=0.45, marker_colors=["#d62728", "#1f77b4", "#7f7f7f"]))
                 .update_layout(title="Valence", height=380,
                                margin=dict(t=50, b=20)))
    # phase
    ph = edges["phase"].value_counts().reindex(PHASES).fillna(0).reset_index()
    ph.columns = ["phase", "count"]
    figs.append(go.Figure(go.Bar(
        x=[PHASE_SHORT[p] for p in ph["phase"]], y=ph["count"],
        marker_color="#2ca02c", text=ph["count"], textposition="outside"))
        .update_layout(title="Edges by Phase", xaxis_title="phase",
                       yaxis_title="rows", height=380,
                       margin=dict(t=50, b=40)))
    # source
    so = edges["text_source"].value_counts().reindex(SOURCES).fillna(0).reset_index()
    so.columns = ["source", "count"]
    figs.append(go.Figure(go.Pie(labels=so["source"], values=so["count"],
                                 hole=0.45,
                                 marker_colors=["#9467bd", "#ff7f0e", "#1f77b4"]))
                 .update_layout(title="Edges by Source", height=380,
                                margin=dict(t=50, b=20)))
    return figs


def fig_network(nodes: pd.DataFrame, edges: pd.DataFrame,
                rank: pd.DataFrame, person_only: bool = False) -> go.Figure:
    """Interactive network with spring layout; hover shows node details."""
    sub = edges
    if person_only:
        persons = set(nodes.loc[nodes["node_type"] == "person", "node_id"])
        sub = edges[edges["source_node"].isin(persons)
                    & edges["target_node"].isin(persons)]
    g = nx.DiGraph()
    for _, r in nodes.iterrows():
        g.add_node(r["node_id"], label_zh=r["label_zh"], node_type=r["node_type"],
                   polity=r["polity"], first_phase=r["first_phase"])
    agg = (sub.groupby(["source_node", "target_node"], as_index=False)
              .size().rename(columns={"size": "weight"}))
    for _, r in agg.iterrows():
        g.add_edge(r["source_node"], r["target_node"], weight=int(r["weight"]))
    g.remove_nodes_from([n for n in list(g.nodes) if g.degree(n) == 0])

    pos = nx.spring_layout(g, k=1.7 / max(1, len(g) ** 0.5), seed=42,
                           weight="weight", iterations=120)
    r = rank.set_index("node_id")

    # edges: one trace per (edge_type, valence) for legend cleanliness
    edge_traces = []
    # dominant (edge_type, valence) per aggregated pair
    pair_style = {}
    for u, v in g.edges:
        rows = sub[(sub.source_node == u) & (sub.target_node == v)]
        if rows.empty:
            continue
        et = rows["edge_type"].mode().iat[0] if not rows["edge_type"].mode().empty \
            else "military_conflict"
        va = rows["valence"].mode().iat[0] if not rows["valence"].mode().empty \
            else "neutral"
        pair_style[(u, v)] = (et, va)
    combos = sorted(set(pair_style.values()))
    for et, va in combos:
        ex, ey = [], []
        for (u, v), style in pair_style.items():
            if style == (et, va):
                ex += [pos[u][0], pos[v][0], None]
                ey += [pos[u][1], pos[v][1], None]
        dash = {"positive": "solid", "negative": "dash", "neutral": "dot"}[va]
        edge_traces.append(go.Scatter(
            x=ex, y=ey, mode="lines",
            line=dict(width=1.1, color=EDGE_COLORS.get(et, "#bbb"), dash=dash),
            hoverinfo="none", name=f"{et} ({va})",
            legendgroup=f"{et}-{va}"))

    # nodes
    node_trace = go.Scatter(
        x=[pos[n][0] for n in g.nodes], y=[pos[n][1] for n in g.nodes],
        mode="markers+text",
        marker=dict(
            size=[10 + 1.15 * float(r["weighted_total_degree"].get(n, 0)
                                  if n in r.index else 0) for n in g.nodes],
            color=[POLITY_COLORS.get(g.nodes[n]["polity"], "#7f7f7f")
                   for n in g.nodes],
            symbol=["circle" if g.nodes[n]["node_type"] == "person"
                    else "square" if g.nodes[n]["node_type"] == "state"
                    else "diamond" for n in g.nodes],
            line=dict(width=1, color="#333")),
        text=[g.nodes[n]["label_zh"] for n in g.nodes],
        textposition="top center", textfont=dict(size=9),
        hovertemplate=(
            "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
            "polity: %{customdata[2]}<br>"
            "first_phase: %{customdata[3]}<br>"
            "weighted degree: %{customdata[4]}<br>"
            "betweenness: %{customdata[5]}<extra></extra>"),
        customdata=[[g.nodes[n]["label_zh"], g.nodes[n]["node_type"],
                     g.nodes[n]["polity"], g.nodes[n]["first_phase"],
                     int(r["weighted_total_degree"].get(n, 0))
                     if n in r.index else 0,
                     float(r["betweenness"].get(n, 0.0))
                     if n in r.index else 0.0] for n in g.nodes],
        name="nodes")

    title = ("Interactive Network — Person-only Subgraph"
             if person_only else "Interactive Network — Full Graph")
    all_traces = edge_traces + [node_trace]
    fig = go.Figure(data=all_traces)
    fig.update_layout(
        title=title, height=760, hovermode="closest",
        xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x",
                                              scaleratio=1),
        legend=dict(orientation="v", yanchor="top", y=0.99, x=1.02,
                    font=dict(size=9)),
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="#fafafa")
    return fig


def fig_top15(rank: pd.DataFrame, metric: str, title: str,
              horizontal: bool = True) -> go.Figure:
    top = rank.nlargest(15, metric)[["node_id", "label_zh", metric,
                                     "node_type", "polity"]]
    y = [f"{r.label_zh} ({r.node_id})" for r in top.itertuples()]
    fig = go.Figure(go.Bar(
        x=top[metric] if horizontal else None,
        y=y if horizontal else None,
        orientation="h" if horizontal else "v",
        marker_color=[POLITY_COLORS.get(p, "#888") for p in top["polity"]],
        text=top[metric], textposition="outside",
        customdata=top[["node_type", "polity"]].values,
        hovertemplate="<b>%{y}</b><br>%{x}<br>type: %{customdata[0]}"
                      "<br>polity: %{customdata[1]}<extra></extra>"))
    fig.update_layout(title=title, height=520,
                      margin=dict(l=170 if horizontal else 40, r=30,
                                  t=50, b=40),
                      yaxis=dict(autorange="reversed") if horizontal else {})
    return fig


def fig_slice_heatmap(cmp: pd.DataFrame, col: str, title: str) -> go.Figure:
    pivot = cmp.pivot_table(index="node_id", columns=col,
                            values="weighted_total_degree", fill_value=0)
    # order columns canonically
    order = [c for c in (PHASES if col == "phase" else SOURCES) if c in pivot.columns]
    pivot = pivot[order]
    labels = [PHASE_SHORT.get(c, c) for c in pivot.columns]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=labels,
        y=[f"{n}" for n in pivot.index],
        colorscale="YlOrRd", text=pivot.values,
        texttemplate="%{text:.0f}", textfont=dict(size=10),
        hovertemplate="node: %{y}<br>%{x}: %{z}<extra></extra>"))
    fig.update_layout(title=title, height=520,
                      margin=dict(l=140, r=20, t=50, b=40),
                      yaxis=dict(autorange="reversed"))
    return fig


def fig_slice_lines(cmp: pd.DataFrame, col: str, title: str) -> go.Figure:
    fig = go.Figure()
    order = [c for c in (PHASES if col == "phase" else SOURCES)
             if c in cmp[col].unique()]
    for actor in KEY_ACTORS:
        d = cmp[(cmp["node_id"] == actor) & (cmp[col].isin(order))]
        if d.empty:
            continue
        d = d.set_index(col).reindex(order)
        d["weighted_total_degree"] = pd.to_numeric(
            d["weighted_total_degree"], errors="coerce").fillna(0.0)
        fig.add_trace(go.Scatter(
            x=[PHASE_SHORT.get(c, c) for c in order],
            y=d["weighted_total_degree"], mode="lines+markers+text",
            name=actor, text=d["weighted_total_degree"].astype(int),
            textposition="top center", textfont=dict(size=9),
            line=dict(width=2), hovertemplate=(
                f"<b>{actor}</b><br>%{{x}}: %{{y}}<extra></extra>")))
    fig.update_layout(title=title, height=520,
                      xaxis_title="phase" if col == "phase" else "source",
                      yaxis_title="weighted total degree",
                      margin=dict(t=50, b=40))
    return fig


# ---------------------------------------------------------------------------
# HTML assembly with tab pages
# ---------------------------------------------------------------------------
PAGE_TMPL = """
<div class="page{active}" id="{pid}">
{content}
</div>
"""

FIG_DIV = '<div class="chart" id="{div}"></div>'

JS_PLOT = """
// ---- plot all registered figures ----
// Charts on hidden pages (display:none) get 0x0 containers, so we plot each
// figure LAZILY the first time its page becomes visible, and resize on
// subsequent visits. The Overview page is visible on load and plotted at once.
const FIGS = {figs_json};
const PLOTTED = new Set();

function plotFig(div) {{
    if (!FIGS[div] || PLOTTED.has(div)) return;
    const cfg = JSON.parse(FIGS[div]);
    Plotly.newPlot(div, cfg.data, cfg.layout, {{responsive: true,
        displaylogo: false, toImageButtonOptions: {{format: 'png', scale: 2}}}});
    PLOTTED.add(div);
}}

function plotPage(pid) {{
    document.querySelectorAll('#' + pid + ' .chart').forEach(d => plotFig(d.id));
}}

function showPage(pid, btn) {{
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(pid).classList.add('active');
    btn.classList.add('active');
    window.scrollTo({{top: 0, behavior: 'smooth'}});
    // plot (first visit) then resize (revisit) so widths are correct
    plotPage(pid);
    requestAnimationFrame(() => {{
        document.querySelectorAll('#' + pid + ' .chart').forEach(d => {{
            if (PLOTTED.has(d.id)) Plotly.Plots.resize(d.id);
        }});
    }});
}}

// initial load: plot the active page only
window.addEventListener('DOMContentLoaded', () => {{
    const active = document.querySelector('.page.active');
    if (active) plotPage(active.id);
}});
"""


def build_html(pages: dict, png_metas: list[dict]) -> str:
    tabs = "".join(
        f'<button class="tab{" active" if i == 0 else ""}" '
        f'onclick="showPage(\'{pid}\', this)">{label}</button>'
        for i, (pid, (label, _)) in enumerate(pages.items()))
    body = "".join(
        PAGE_TMPL.format(pid=pid, content=content,
                         active=" active" if i == 0 else "")
        for i, (pid, (label, content)) in enumerate(pages.items()))

    # embed resized PNGs as base64 so the HTML is fully self-contained
    png_html = ""
    for m in png_metas:
        b64 = base64.b64encode((RESIZED / m["file"]).read_bytes()).decode()
        png_html += f"""
        <div class="pngcard">
          <h3>{m['title']}</h3>
          <p class="meta">original {m['orig']} → resized {m['new']} (300 DPI original kept in outputs/)</p>
          <img src="data:image/png;base64,{b64}" alt="{m['title']}">
        </div>"""

    if png_html:
        body += PAGE_TMPL.format(pid="page-static", content=png_html,
                                 active="")

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>燕秦關係 SNA Dashboard — DHG502</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{ --bg:#f5f6fa; --card:#ffffff; --ink:#222; --accent:#1f3b73; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Microsoft JhengHei","PingFang HK","Noto Sans CJK TC",
         "Noto Sans TC",sans-serif; margin:0; background:var(--bg); color:var(--ink); }}
  header {{ background:var(--accent); color:#fff; padding:18px 28px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header p {{ margin:4px 0 0; opacity:.85; font-size:13px; }}
  nav {{ display:flex; flex-wrap:wrap; gap:6px; padding:10px 28px;
        background:#fff; border-bottom:1px solid #ddd; position:sticky; top:0;
        z-index:10; }}
  .tab {{ border:1px solid #ccd; background:#eef; padding:8px 16px;
         border-radius:18px; cursor:pointer; font-size:14px; }}
  .tab.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  .page {{ display:none; padding:20px 28px 60px; }}
  .page.active {{ display:block; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
           gap:12px; margin-bottom:18px; }}
  .card {{ background:var(--card); border-radius:10px; padding:14px 16px;
          box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .card .num {{ font-size:26px; font-weight:700; color:var(--accent); }}
  .card .lbl {{ font-size:12px; color:#666; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  @media (max-width:900px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  .chart {{ background:var(--card); border-radius:10px; padding:8px;
           box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:14px; }}
  .pngcard {{ background:var(--card); border-radius:10px; padding:14px;
             box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:20px; }}
  .pngcard img {{ width:100%; height:auto; border:1px solid #e2e2e2;
                 border-radius:6px; }}
  .meta {{ color:#777; font-size:12px; }}
  h2.sec {{ border-left:5px solid var(--accent); padding-left:10px;
           font-size:18px; margin:26px 0 12px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px;
          background:var(--card); }}
  th,td {{ border:1px solid #e3e3e3; padding:6px 10px; text-align:left; }}
  th {{ background:#eef1f8; }}
</style>
</head>
<body>
<header>
  <h1>燕秦關係社會網路分析 Dashboard</h1>
  <p>Yan–Qin SNA · 90 nodes · 329 attestation edges · sources: ZGC / Shiji / ZZTJ ·
     phases P1–P4 — DHG502 Final Project</p>
</header>
<nav>{tabs}<button class="tab" onclick="showPage('page-static', this)">Static Maps</button></nav>
{body}
<script>
{JS_PLOT.format(figs_json='__FIGS_JSON__')}
</script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    nodes = pd.read_csv(DATA / "nodes.csv", encoding="utf-8")
    edges = pd.read_csv(DATA / "edges.csv", encoding="utf-8")
    rank = pd.read_csv(OUT / "centrality_rankings.csv", encoding="utf-8")
    phase_cmp = pd.read_csv(OUT / "phase_comparison.csv", encoding="utf-8")
    source_cmp = pd.read_csv(OUT / "source_comparison.csv", encoding="utf-8")
    dedup = pd.read_csv(OUT / "dedup_comparison.csv", encoding="utf-8")
    summary = pd.read_csv(OUT / "global_summary.csv", encoding="utf-8")

    print("Resizing PNGs ...")
    png_metas = resize_pngs(target_width=2600)

    figs = {}          # div_id -> plotly figure
    pages = {}         # page_id -> (label, content_html)

    # ---- Page 1: Overview -------------------------------------------------
    cards = [
        ("90", "nodes"), ("329", "attestation edges"), ("148", "aggregated edges"),
        ("166", "deduplicated edges"), ("2", "weakly connected components"),
        ("0.0185", "density (full graph)"),
    ]
    cards_html = '<div class="cards">' + "".join(
        f'<div class="card"><div class="num">{n}</div><div class="lbl">{l}</div></div>'
        for n, l in cards) + "</div>"

    ov_figs = fig_overview_bars(edges)
    ov_html = cards_html + '<div class="grid2">'
    for i, f in enumerate(ov_figs):
        div = f"ov{i}"
        figs[div] = f
        ov_html += FIG_DIV.format(div=div)
    ov_html += "</div>"
    # summary table
    ov_html += "<h2 class='sec'>Global Summary</h2><table><tr>" \
               "<th>graph</th><th>nodes</th><th>edges</th><th>WCC</th>" \
               "<th>SCC</th><th>density</th></tr>"
    for _, r in summary.iterrows():
        ov_html += (f"<tr><td>{r['graph']}</td><td>{r['nodes']}</td>"
                    f"<td>{r['edges']}</td><td>{r['weakly_connected_components']}</td>"
                    f"<td>{r['strongly_connected_components']}</td>"
                    f"<td>{r['density']}</td></tr>")
    ov_html += "</table>"
    pages["page-overview"] = ("Overview", ov_html)

    # ---- Page 2: Network ---------------------------------------------------
    net_html = ('<h2 class="sec">Full Graph</h2>')
    figs["net-full"] = fig_network(nodes, edges, rank, person_only=False)
    net_html += FIG_DIV.format(div="net-full")
    net_html += '<h2 class="sec">Person-only Subgraph</h2>'
    figs["net-person"] = fig_network(nodes, edges, rank, person_only=True)
    net_html += FIG_DIV.format(div="net-person")
    net_html += ('<p class="meta">Hover a node for label / type / polity / '
                 'first_phase / weighted degree / betweenness. Node size = '
                 'weighted degree; colour = polity; marker shape = node type '
                 '(circle=person, square=state, diamond=allusion); line dash = '
                 'valence (solid=positive, dash=negative, dot=neutral). '
                 'Drag to pan, scroll to zoom, double-click to reset.</p>')
    pages["page-network"] = ("Network", net_html)

    # ---- Page 3: Centrality -------------------------------------------------
    cen_html = ""
    for metric, title in [
        ("total_degree", "Top 15 — Total Degree (distinct partners)"),
        ("weighted_total_degree", "Top 15 — Weighted Degree (attestation count)"),
        ("betweenness", "Top 15 — Betweenness Centrality (normalized)"),
    ]:
        div = f"cen-{metric}"
        figs[div] = fig_top15(rank, metric, title)
        cen_html += FIG_DIV.format(div=div)
    pages["page-centrality"] = ("Centrality", cen_html)

    # ---- Page 4: Phase comparison -------------------------------------------
    ph_html = ""
    div = "ph-heat"
    figs[div] = fig_slice_heatmap(phase_cmp, "phase",
                                  "Key Actors × Phase — Weighted Degree")
    ph_html += FIG_DIV.format(div=div)
    div = "ph-line"
    figs[div] = fig_slice_lines(phase_cmp, "phase",
                                "Key Actors across P1–P4 (weighted degree)")
    ph_html += FIG_DIV.format(div=div)
    pages["page-phase"] = ("Phase P1–P4", ph_html)

    # ---- Page 5: Source comparison -------------------------------------------
    so_html = ""
    div = "so-heat"
    figs[div] = fig_slice_heatmap(source_cmp, "text_source",
                                  "Key Actors × Source — Weighted Degree")
    so_html += FIG_DIV.format(div=div)
    div = "so-line"
    figs[div] = fig_slice_lines(source_cmp, "text_source",
                                "Key Actors across ZGC / Shiji / ZZTJ")
    so_html += FIG_DIV.format(div=div)
    pages["page-source"] = ("Source Compare", so_html)

    # ---- Page 6: Dedup ---------------------------------------------------------
    dd_html = ('<p class="meta">Full table: 329 attestation rows → 166 '
               'deduplicated edges grouped by (source_node, target_node, '
               'edge_type). rank_shift = rank_full − rank_dedup '
               '(positive = rose after dedup).</p>')
    top = dedup.head(20)
    dd_html += ("<table><tr><th>node_id</th><th>wtd_deg_full</th>"
                "<th>wtd_deg_dedup</th><th>delta</th><th>rank_full</th>"
                "<th>rank_dedup</th><th>rank_shift</th></tr>")
    for _, r in top.iterrows():
        dd_html += (f"<tr><td>{r['node_id']}</td><td>{r['wtd_deg_full']}</td>"
                    f"<td>{r['weighted_total_degree_dedup']}</td>"
                    f"<td>{r['wtd_deg_delta']}</td><td>{r['rank_full']}</td>"
                    f"<td>{r['rank_dedup']}</td><td>{r['rank_shift']}</td></tr>")
    dd_html += "</table>"
    pages["page-dedup"] = ("Dedup Check", dd_html)

    # ---- serialize figures & build html ---------------------------------------
    figs_json = json.dumps(
        {k: json.loads(v.to_json()) for k, v in figs.items()},
        ensure_ascii=False)
    html = build_html(pages, png_metas)
    html = html.replace("__FIGS_JSON__",
                        json.dumps(figs_json, ensure_ascii=False))
    dest = OUT / "dashboard.html"
    dest.write_text(html, encoding="utf-8")
    print(f"\nWROTE {dest}  ({dest.stat().st_size/1e6:.1f} MB, "
          f"{len(figs)} interactive charts, {len(pages)+1} pages)")


if __name__ == "__main__":
    main()
