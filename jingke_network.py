# -*- coding: utf-8 -*-
"""
荊軻傳(史記·刺客列傳)社交網路分析
以 NetworkX 建立人物關係網路,並將荊軻置於圖形中心。
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
import numpy as np

# ============================================================
# 1. 中文字型設定(Noto Sans CJK)
# ============================================================
CJK_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(CJK_FONT_PATH)
cjk_font_name = fm.FontProperties(fname=CJK_FONT_PATH).get_name()
plt.rcParams["font.family"] = cjk_font_name
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 2. 人物節點(依《史記·刺客列傳》荊軻傳原文)
# ============================================================
# (人物, 陣營/類別)
nodes = [
    ("荊軻", "主角"),
    ("燕太子丹", "燕國"),
    ("田光", "燕國"),
    ("高漸離", "燕國"),
    ("樊於期", "秦國降將"),
    ("秦舞陽", "燕國"),
    ("蓋聶", "他國"),
    ("魯句踐", "他國"),
    ("鞠武", "燕國"),
    ("蒙嘉", "秦國"),
    ("秦王政", "秦國"),
    ("夏無且", "秦國"),
    ("燕王喜", "燕國"),
    ("衛元君", "他國"),
    ("徐夫人", "其他"),
]

# ============================================================
# 3. 關係邊(權重=互動強度,每條均有說明與類別)
#    類別:core=與荊軻直接相關 / yan=燕國陣營內部
#          qin=秦國陣營內部   / cross=燕秦對立
# ============================================================
edges = [
    ("荊軻", "燕太子丹", 5, "刺秦之謀", "core"),
    ("荊軻", "田光", 4, "知己薦賢", "core"),
    ("荊軻", "高漸離", 5, "市中飲酒和歌", "core"),
    ("荊軻", "樊於期", 4, "借首獻秦", "core"),
    ("荊軻", "秦舞陽", 3, "副使同行", "core"),
    ("荊軻", "蓋聶", 2, "榆次論劍", "core"),
    ("荊軻", "魯句踐", 2, "邯鄲爭道", "core"),
    ("荊軻", "衛元君", 2, "以術說之", "core"),
    ("荊軻", "秦王政", 5, "圖窮匕見", "core"),
    ("荊軻", "蒙嘉", 2, "賄賂引見", "core"),
    ("荊軻", "夏無且", 2, "藥囊擲之", "core"),
    ("燕太子丹", "田光", 4, "自刎明志", "yan"),
    ("燕太子丹", "鞠武", 4, "太傅", "yan"),
    ("燕太子丹", "樊於期", 3, "收留", "yan"),
    ("燕太子丹", "秦舞陽", 2, "任命為副", "yan"),
    ("燕太子丹", "燕王喜", 3, "父子", "yan"),
    ("燕太子丹", "徐夫人", 2, "百金購匕首", "yan"),
    ("田光", "鞠武", 3, "薦賢", "yan"),
    ("秦王政", "樊於期", 3, "購其首級", "qin"),
    ("秦王政", "蒙嘉", 3, "寵臣", "qin"),
    ("秦王政", "夏無且", 3, "藥囊擲軻", "qin"),
    ("秦王政", "燕王喜", 2, "征伐", "cross"),
    ("秦王政", "燕太子丹", 3, "質秦結怨", "cross"),
]

# ============================================================
# 4. 建立圖
# ============================================================
G = nx.Graph()
for name, faction in nodes:
    G.add_node(name, faction=faction)
for u, v, w, label, cat in edges:
    G.add_edge(u, v, weight=w, label=label, cat=cat)

# ============================================================
# 4. 放射狀版面:荊軻在正中心
#    內圈 = 與荊軻直接相關的人物
#    外圈 = 僅與內圈人物相關的人物
# ============================================================
CENTER = "荊軻"
neighbors = [n for n in G.neighbors(CENTER)]
outer_nodes = [n for n in G.nodes() if n != CENTER and n not in neighbors]

# 內圈依陣營排序,讓同陣營相鄰,減少視覺雜亂
faction_order = {"燕國": 0, "秦國降將": 1, "秦國": 2, "他國": 3}
neighbors_sorted = sorted(
    neighbors, key=lambda n: (faction_order.get(G.nodes[n]["faction"], 9), n)
)

R_INNER, R_OUTER = 3.4, 5.6
pos = {CENTER: np.array([0.0, 0.0])}

# 內圈均勻分布(從正上方開始,順時針)
n_inner = len(neighbors_sorted)
for i, name in enumerate(neighbors_sorted):
    theta = np.pi / 2 - 2 * np.pi * i / n_inner
    pos[name] = R_INNER * np.array([np.cos(theta), np.sin(theta)])

# 外圈節點放在其相鄰內圈節點的平均角度方向上
for name in outer_nodes:
    inner_nbrs = [n for n in G.neighbors(name) if n in pos]
    angles = [
        np.arctan2(pos[n][1], pos[n][0]) for n in inner_nbrs
    ]
    # 處理角度環繞問題:取向量平均
    vec = np.mean([np.array([np.cos(a), np.sin(a)]) for a in angles], axis=0)
    norm = np.linalg.norm(vec)
    if norm < 1e-9:
        vec, norm = np.array([1.0, 0.0]), 1.0
    pos[name] = R_OUTER * vec / norm

# ============================================================
# 6. 視覺化
# ============================================================
faction_colors = {
    "主角": "#E63946",      # 紅
    "燕國": "#457B9D",      # 藍
    "秦國": "#2A9D8F",      # 綠
    "秦國降將": "#8AB17D",  # 淡綠
    "他國": "#E9C46A",      # 黃
    "其他": "#9B5DE5",      # 紫
}

node_colors = [faction_colors[G.nodes[n]["faction"]] for n in G.nodes()]
# 節點大小:確保 3~4 字標籤完整落在圓內
# matplotlib node_size 單位是 points^2,直徑 = sqrt(size);13.5pt 字體的
# 3 個字約需 45pt 寬 → 直徑 >= 50pt → size >= 2500
node_sizes = [5200 if n == CENTER else 2600 + 350 * G.degree(n) for n in G.nodes()]

# 邊配色:依關係類別區分,讓線條不混淆
cat_styles = {
    "core":  {"color": "#D64545", "alpha": 0.75, "rad": 0.0},   # 紅:與荊軻直接相關
    "yan":   {"color": "#2E6FAF", "alpha": 0.70, "rad": 0.25},  # 藍:燕國陣營內部(弧線)
    "qin":   {"color": "#1F8A70", "alpha": 0.70, "rad": -0.25}, # 綠:秦國陣營內部(反向弧線)
    "cross": {"color": "#E76F51", "alpha": 0.85, "rad": 0.35},  # 橘:燕秦對立(大弧線)
}

fig, ax = plt.subplots(figsize=(20, 18), facecolor="white")

from matplotlib.patches import ConnectionStyle

def _ctrl_point(p0, p1, rad):
    """用 matplotlib 自身的 ConnectionStyle 取 arc3 控制點,
    保證與實際繪出的弧線完全一致"""
    path = ConnectionStyle("arc3", rad=rad).connect(tuple(p0), tuple(p1))
    return np.asarray(path.vertices[1], dtype=float)

# 特殊邊:自訂弧度大小與凸出方向
#   質秦結怨(秦王政—燕太子丹):弦線貫穿中央,向右(+x)大幅彎開
#   購其首級(秦王政—樊於期):夏無且恰在兩人中間,改向內彎避開
_BULGE_OVERRIDE = {
    frozenset(("秦王政", "燕太子丹")): (0.50, "right"),
    frozenset(("秦王政", "樊於期")): (0.36, "inward"),
}

def _resolve_rad(u, v):
    """決定每條定每條邊的弧度:預設向外彎(遠離圖心),特殊邊依指定方向"""
    key = frozenset((u, v))
    if key in _BULGE_OVERRIDE:
        mag, direction = _BULGE_OVERRIDE[key]
        p0, p1 = np.array(pos[u]), np.array(pos[v])
        mid = (p0 + p1) / 2.0
        d = _ctrl_point(p0, p1, mag) - mid
        if direction == "inward":
            if np.dot(d, mid) > 0:      # 目前向外 → 翻轉為向內
                mag = -mag
        elif direction == "right":
            if d[0] < 0:                # 凸出方向偏左 → 翻轉為向右
                mag = -mag
        return mag
    rad = cat_styles[G[u][v]["cat"]]["rad"]
    if rad == 0.0:
        return 0.0
    p0, p1 = np.array(pos[u]), np.array(pos[v])
    mid = (p0 + p1) / 2.0
    d = _ctrl_point(p0, p1, rad) - mid
    if np.dot(d, mid) < 0:              # 弧線凹向圖心 → 翻轉為向外
        rad = -rad
    return rad

edge_rads = {(u, v): _resolve_rad(u, v) for u, v in G.edges()}

# 邊:逐條繪製(arrows=True 強制使用 FancyArrowPatch,弧線才會生效)
for (u, v), rad in edge_rads.items():
    style = cat_styles[G[u][v]["cat"]]
    nx.draw_networkx_edges(
        G, pos, ax=ax, edgelist=[(u, v)],
        width=[G[u][v]["weight"] * 0.85],
        edge_color=style["color"], alpha=style["alpha"],
        style="solid", arrows=True, arrowstyle="-",
        connectionstyle=f"arc3,rad={rad}",
    )

# 節點
nx.draw_networkx_nodes(
    G, pos, ax=ax, node_color=node_colors,
    node_size=node_sizes, edgecolors="white", linewidths=2.5
)

# 節點標籤(荊軻字體最大)
labels_main = {n: n for n in G.nodes() if n != CENTER}
nx.draw_networkx_labels(
    G, pos, labels=labels_main, ax=ax, font_size=13.5,
    font_family=cjk_font_name, font_color="white", font_weight="bold"
)
nx.draw_networkx_labels(
    G, pos, labels={CENTER: CENTER}, ax=ax, font_size=22,
    font_family=cjk_font_name, font_color="white", font_weight="bold"
)

# 先繪製一次,取得 renderer 與精確座標轉換(供標籤實測外框用)
fig.canvas.draw()
_renderer = fig.canvas.get_renderer()
_inv = ax.transData.inverted()

# ------------------------------------------------------------
# 邊標籤:全部 23 條連線都標註說明
# 標籤沿弧線放置,並以自動避讓演算法避免標籤之間、標籤與節點重疊
# ------------------------------------------------------------
def _bezier_point(p0, p1, rad, t):
    """arc3 二次貝茲曲線上的點(直接使用 matplotlib 的 ConnectionStyle,
    確保與實際繪製的弧線完全一致)"""
    ctrl = _ctrl_point(p0, p1, rad)
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * p1

node_pos = {n: np.array(pos[n]) for n in G.nodes()}
placed_boxes = []  # 已放置標籤的 (x, y, half_w, half_h)

def _text_extent_px(s):
    """實測文字在顯示座標(px)下的外框"""
    t = _renderer.get_text_width_height_descent(
        s, fm.FontProperties(family=cjk_font_name, size=9), False
    )
    return t[0], t[1]

def _conflict(x, y, half_w, half_h):
    for bx, by, bw, bh in placed_boxes:
        if abs(x - bx) < (half_w + bw) and abs(y - by) < (half_h + bh):
            return True
    for n, p in node_pos.items():
        r = 0.78 if n == CENTER else 0.62
        if np.hypot(x - p[0], y - p[1]) < r + 0.30:
            return True
    return False

# 長邊優先放置:長邊的弧中點空間大,先佔位可減少後續擠壓
_edges_sorted = sorted(
    G.edges(), key=lambda e: -np.linalg.norm(node_pos[e[0]] - node_pos[e[1]])
)
for u, v in _edges_sorted:
    label = G[u][v]["label"]
    rad = edge_rads[(u, v)]
    # 標籤框半寬/半高:以 renderer 實測文字尺寸換算為資料座標
    w_px, h_px = _text_extent_px(label)
    p0_disp = ax.transData.transform((0, 0))
    p1_disp = ax.transData.transform((1, 1))
    unit_w = abs(p1_disp[0] - p0_disp[0])  # 1 資料單位的 px 寬
    unit_h = abs(p1_disp[1] - p0_disp[1])
    half_w = (w_px / unit_w) / 2 + 0.08
    half_h = (h_px / unit_h) / 2 + 0.06
    p = None
    for t in [0.5, 0.38, 0.62, 0.30, 0.70, 0.22, 0.78, 0.15, 0.85]:
        cand = _bezier_point(node_pos[u], node_pos[v], rad, t)
        if not _conflict(cand[0], cand[1], half_w, half_h):
            p = cand
            break
    if p is None:
        # 全部候選點都衝突:沿弧線逐點掃描,找離節點最遠的可用點
        best, best_score = None, -1.0
        for t in np.linspace(0.05, 0.95, 37):
            cand = _bezier_point(node_pos[u], node_pos[v], rad, t)
            if _conflict(cand[0], cand[1], half_w, half_h):
                continue
            score = min(
                np.hypot(cand[0] - q[0], cand[1] - q[1])
                for q in node_pos.values()
            )
            if score > best_score:
                best, best_score = cand, score
        if best is not None:
            p = best
        else:
            # 弧線上完全無可用點:沿弧線垂直方向逐步偏移
            base = _bezier_point(node_pos[u], node_pos[v], rad, 0.5)
            d = node_pos[v] - node_pos[u]
            dist = np.linalg.norm(d)
            perp = np.array([-d[1], d[0]]) / (dist + 1e-12)
            for k in range(1, 10):
                sign = 1 if k % 2 else -1
                cand = base + sign * 0.4 * ((k + 1) // 2) * perp
                if not _conflict(cand[0], cand[1], half_w, half_h):
                    p = cand
                    break
            if p is None:
                p = base
    placed_boxes.append((p[0], p[1], half_w, half_h))
    ax.text(
        p[0], p[1], label, fontsize=9,
        fontfamily=cjk_font_name, color="#3D3D3D",
        ha="center", va="center", zorder=6,
        bbox={"facecolor": "white", "edgecolor": "none",
              "alpha": 0.82, "pad": 1},
    )

# 圖例:節點(陣營)+ 邊(關係類別)
legend_handles = [
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
               markersize=13, label=f)
    for f, c in faction_colors.items()
]
legend_edges = [
    plt.Line2D([0], [0], color=s["color"], lw=3, alpha=s["alpha"],
               label=lbl)
    for lbl, s in [
        ("與荊軻直接相關", cat_styles["core"]),
        ("燕國陣營內部", cat_styles["yan"]),
        ("秦國陣營內部", cat_styles["qin"]),
        ("燕秦對立", cat_styles["cross"]),
    ]
]
leg1 = ax.legend(
    handles=legend_handles, loc="upper left", fontsize=11,
    title="節點:陣營", title_fontsize=12, framealpha=0.9,
    bbox_to_anchor=(0.0, 1.0)
)
ax.add_artist(leg1)
ax.legend(
    handles=legend_edges, loc="lower left", fontsize=11,
    title="連線:關係類別", title_fontsize=12, framealpha=0.9,
    bbox_to_anchor=(0.0, 0.0)
)

ax.set_title(
    "荊軻社交網路 —— 《史記·刺客列傳》\n"
    "(節點大小 = 連結數,線寬 = 互動強度,連線顏色 = 關係類別,荊軻居中)",
    fontsize=18, fontweight="bold", pad=20
)
ax.axis("off")
ax.set_xlim(-7.6, 7.6)
ax.set_ylim(-7.6, 7.6)
ax.set_aspect("equal")
plt.tight_layout()
plt.savefig(
    "/workspaces/DHG502_Final_Project/jingke_social_network.png",
    dpi=220, bbox_inches="tight", facecolor="white"
)
print("圖片已儲存:jingke_social_network.png")

# ============================================================
# 7. 網路統計
# ============================================================
print(f"\n節點數:{G.number_of_nodes()}")
print(f"邊數:{G.number_of_edges()}")
print("\n度中心性(前 5):")
for name, score in sorted(
    nx.degree_centrality(G).items(), key=lambda x: -x[1]
)[:5]:
    print(f"  {name}: {score:.3f}")
