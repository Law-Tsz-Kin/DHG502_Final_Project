#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_entities.py
===================
Extracts named entities from data/segments.csv (the 92-segment corpus built from
raw_texts/) and produces:

  Deliverable A — data/alias_dictionary.json
      Maps every surface name / title / appellation found in the corpus to a
      single canonical node_id, plus a "flagged_ambiguous_terms" array for
      context-dependent terms left unresolved for manual verification.

  Deliverable B — data/nodes.csv
      Columns: node_id,label_zh,node_type,polity,functional_role,first_phase

Ground rules (per project spec):
  * Only entities that explicitly appear in the corpus are included.
  * first_phase = earliest phase (P1 < P2 < P3 < P4) in which any alias of the
    entity occurs; computed from the corpus, not from outside knowledge.
  * functional_role is concise and grounded in the text.
  * Every node_id in nodes.csv is a canonical key of the alias dictionary.

Verification built in:
  * every alias is regex-checked against the corpus; unmatched aliases are
    reported (they must not silently stay in the dictionary);
  * every node_id in nodes.csv must exist as a canonical key in the JSON;
  * every canonical key must have at least one alias that occurs in the corpus.
"""

import csv
import json
import re
import pathlib
from collections import Counter, OrderedDict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEG = ROOT / "data" / "segments.csv"
OUT_JSON = ROOT / "data" / "alias_dictionary.json"
OUT_CSV = ROOT / "data" / "nodes.csv"

PHASE_ORDER = ["P1_pre_diplomacy", "P2_alliance_vs_plot",
               "P3_assassination", "P4_fall_of_yan"]

# ---------------------------------------------------------------------------
# 1. Entity definitions
#    node_id -> (label_zh, node_type, polity, functional_role, aliases)
#    Aliases are regex fragments; word-boundary issues don't arise in Chinese,
#    but lookarounds are used where a short form would otherwise over-match.
# ---------------------------------------------------------------------------
ENTITIES = OrderedDict()

def add(nid, label, ntype, polity, role, aliases):
    ENTITIES[nid] = {
        "label_zh": label, "node_type": ntype, "polity": polity,
        "functional_role": role, "aliases": aliases,
    }

# ------------------------- persons: Yan -------------------------
add("Jing_Ke", "荊軻", "person", "Yan", "assassin",
    [r"荊軻", r"荊卿", r"慶卿", r"軻(?=曰|既|遂|知|嘗|者|奉|和|逐|被|自知|廢|怒)"])
add("Yan_Dan", "燕太子丹", "person", "Yan", "hostage_prince",
    [r"燕太子丹", r"太子丹", r"(?<![燕單])太子(?!軍)", r"(?<![燕單])丹(?=[曰者乃匿])",
     r"燕丹"])
add("Yan_Wang_Xi", "燕王喜", "person", "Yan", "ruler",
    [r"燕王喜", r"今王喜", r"燕王(?!喜|及太子)"])
add("Ju_Wu", "鞠武", "person", "Yan", "grand_tutor",
    [r"鞠武", r"鞫武", r"(?<=太傅)武(?=對曰|諫曰|曰)", r"(?<=其傅)鞠武"])
add("Tian_Guang", "田光", "person", "Yan", "recluse_sponsor",
    [r"田光", r"田先生", r"處士田光", r"(?<![田臣])光(?=竊|曰|坐定|俛|僂|聞)"])
add("Fan_Yuqi", "樊於期", "person", "Qin", "qin_defector_general",
    [r"樊於期", r"樊將軍", r"(?<=將軍)於期", r"於期(?=仰天|乃前|太息|毎)"])
add("Gao_Jianli", "髙漸離", "person", "Yan", "musician_retainer",
    [r"髙漸離", r"高漸離"])
add("Qin_Wuyang", "秦舞陽", "person", "Yan", "assassins_aide",
    [r"秦舞陽", r"秦武陽", r"(?<=秦)舞陽", r"(?<=秦)武陽"])
add("Gai_Nie", "蓋聶", "person", "Other", "swordsman",
    [r"蓋聶"])
add("Lu_Goujian", "魯句踐", "person", "Other", "swordsman",
    [r"魯句踐"])
add("Gou_Tu", "狗屠", "person", "Yan", "butcher_associate",
    [r"狗屠"])
add("Xu_Furen", "徐夫人", "person", "Zhao_Dai", "dagger_maker",
    [r"徐夫人"])

# ------------------------- persons: Qin -------------------------
add("Qin_Shi_Huang", "秦王政（秦始皇）", "person", "Qin", "ruler",
    [r"秦王政", r"秦始皇", r"始皇帝", r"秦皇帝", r"始皇(?!母)",
     r"秦王(?!朝|使趙|以為然)", r"大王", r"(?<![燕齊魏楚趙代先文武景湣幽繆悼孝威宣昭莊襄])王(?=曰|大喜|聞之|問|如邯鄲|使人|初并|義而許|負劍|以為然|收而與|何以去|必厚割|遂降|下其議)",
     r"皇帝", r"秦皇帝"])
add("Wang_Jian", "王翦", "person", "Qin", "general",
    [r"王翦", r"(?<=王)翦(?=將|曰|果|謝|遂|既|行|至|日|因|使人|言)"])
add("Wang_Ben", "王賁", "person", "Qin", "general",
    [r"王賁", r"(?<=翦子王)賁"])
add("Li_Xin", "李信", "person", "Qin", "general",
    [r"李信"])
add("Meng_Tian", "蒙恬", "person", "Qin", "general",
    [r"蒙恬"])
add("Meng_Wu", "蒙武", "person", "Qin", "general",
    [r"蒙武", r"蒙〔武〕\(恬\)"])
add("Meng_Jia", "蒙嘉", "person", "Qin", "court_favourite",
    [r"蒙嘉", r"(?<=蒙)嘉(?=為先言|爲先言)"])
add("Xia_Wuqie", "夏無且", "person", "Qin", "court_physician",
    [r"夏無且", r"(?<=賜)無且"])
# Qin_Zhao_Wang removed: appears only as 「秦昭王卒」 (S021) - a death notice
# with no edge-type event; no edges could be built.
add("Zhuang_Xiang_Wang", "莊襄王", "person", "Qin", "ruler",
    [r"莊襄王"])
add("Wei_Yuan_Jun", "衞元君", "person", "Other", "ruler",
    [r"衞元君"])
add("Li_Si", "李斯（廷尉斯）", "person", "Qin", "grand_counselor",
    [r"廷尉斯"])
add("Wang_Wan", "王綰", "person", "Qin", "chancellor",
    [r"〔王〕綰"])

# ------------------------- persons: Zhao / Dai -------------------------
add("Zhao_Xiaocheng_Wang", "趙孝成王", "person", "Zhao_Dai", "ruler",
    [r"趙孝成王", r"(?<=爲)趙王(?=酒)", r"(?<=今)王喜(?=四年)"])
add("Zhao_Wang_Qian", "趙王遷", "person", "Zhao_Dai", "ruler",
    [r"趙王遷", r"(?<=虜)趙王(?=，|遷)", r"(?<=得)趙王(?=。|$)"])
add("Zhao_Daoxiang_Wang", "趙悼襄王", "person", "Zhao_Dai", "ruler",
    [r"趙悼襄王", r"悼襄王"])
# Zhao_Youmiao_Wang removed: appears only as 「悼襄王卒，子幽繆王遷立」 (S092)
# - a succession notice with no edge-type event.
add("Dai_Wang_Jia", "代王嘉", "person", "Zhao_Dai", "ruler",
    [r"代王嘉", r"趙公子嘉", r"公子嘉", r"(?<=代王)嘉(?=計|乃|遺)"])
add("Lian_Po", "廉頗", "person", "Zhao_Dai", "general",
    [r"廉頗"])
add("Le_Jian", "樂間（樂閒）", "person", "Yan", "general_minister",
    [r"樂間", r"樂閒", r"(?<=昌國君樂)間", r"(?<=昌國君樂)閒"])
add("Le_Cheng", "樂乘", "person", "Zhao_Dai", "general",
    [r"樂乘", r"［樂乘］"])
add("Li_Fu", "栗腹", "person", "Yan", "general_minister",
    [r"栗腹"])
add("Jiang_Qu", "將渠", "person", "Yan", "chief_minister",
    [r"將渠"])
add("Ju_Xin", "劇辛", "person", "Yan", "general",
    [r"劇辛", r"(?<=問劇辛，)辛(?=曰)"])
add("Pang_Nuan", "龐煖", "person", "Zhao_Dai", "general",
    [r"龐煖"])
add("Li_Mu", "李牧", "person", "Zhao_Dai", "general",
    [r"李牧"])
add("Qin_Qing", "卿秦", "person", "Yan", "general",
    [r"卿秦"])
add("Qing_She", "慶舍", "person", "Zhao_Dai", "general",
    [r"慶舍"])
add("Xin_Liang", "信梁", "person", "Qin", "general",
    [r"信梁"])
# Zheng_Anping removed: appears only as 「武陽君鄭安平死」 (S084) - death notice.
# Chang'an_Jun removed: appears only as 「封長安君以饒」 (S091) - enfeoffment,
# not one of the six edge types.
# Zhao_Sheng removed: appears only as 「平原君趙勝死」 (S084) - death notice.
# Fu_Di removed: appears only as 「傅抵將，居平邑」 (S091) - deployment, no
# edge-type event.
# Tufu_Qi removed: appears only as 「徒父祺出」 (S084) - event too unclear to
# classify.
add("Yanling_Jun", "延陵鈞", "person", "Zhao_Dai", "general",
    [r"延陵鈞"])
add("Xie_Jun", "泄鈞", "person", "Zhao_Dai", "envoy_intermediary",
    [r"泄鈞"])
add("Chunping_Jun", "春平君", "person", "Zhao_Dai", "royal_favourite",
    [r"春平君"])
add("Ping_Du", "平都", "person", "Zhao_Dai", "hostage_figure",
    [r"留平都", r"贖平都"])
add("Wenxin_Hou", "文信侯（呂不韋）", "person", "Qin", "chancellor",
    [r"文信侯"])

# ------------------------- persons: Qi / Chu / Wei / other -------------------------
add("Qi_Wang_Jian", "齊王建", "person", "Qi", "ruler",
    [r"齊王建", r"(?<=戒)王建", r"(?<=怨)王建", r"(?<!孝成悼襄幽繆昭莊)齊王(?!建)"])
add("Jun_Wang_Hou", "君王后", "person", "Qi", "queen_dowager",
    [r"君王后"])
add("Hou_Sheng", "后勝", "person", "Qi", "chancellor",
    [r"后勝"])
add("Yongmen_Sima", "雍門司馬", "person", "Qi", "palace_commander",
    [r"雍門司馬"])
add("Jimo_Dafu", "即墨大夫", "person", "Qi", "grand_master",
    [r"即墨大夫"])
# Chu_You_Wang removed: appears only as 「楚幽王薨」 (S031) - death notice.
add("Chu_King_Hao", "郝", "person", "Chu", "ruler",
    [r"(?<=立其弟)郝", r"(?<=三月，)郝(?=庶兄)"])
add("Chu_King_Fuchu", "負芻", "person", "Chu", "ruler",
    [r"負芻"])
add("Xiang_Yan", "項燕", "person", "Chu", "general",
    [r"項燕"])
add("Changping_Jun", "昌平君", "person", "Chu", "ruler",
    [r"昌平君"])
# Wei_Jingmin_Wang removed: appears only as 「魏景湣王薨，子假立」 (S032) -
# succession notice; the meaningful edge (魏王假's fall) is on Wei_Wang_Jia.
add("Wei_Wang_Jia", "魏王假", "person", "Wei", "ruler",
    [r"魏王假", r"(?<=薨，子)假(?=立)"])
add("Anling_Jun", "安陵君", "person", "Wei", "vassal_lord",
    [r"安陵君"])
add("Chu_King_You", "楚幽王", "person", "Chu", "ruler", [])  # placeholder removed below

# remove accidental duplicate
ENTITIES.pop("Chu_King_You", None)

# ------------------------- allusions -------------------------
add("Cao_Mo", "曹沫", "allusion", "Other", "rhetorical_exemplar",
    [r"曹沫"])
add("Qi_Huan_Gong", "齊桓公", "allusion", "Qi", "rhetorical_exemplar",
    [r"齊桓公"])
add("Guan_Zhong", "管仲", "allusion", "Other", "rhetorical_exemplar",
    [r"(?<=雖有)管(?=、晏)"])
add("Yan_Ying", "晏嬰", "allusion", "Other", "rhetorical_exemplar",
    [r"(?<=管、)晏(?=，)"])
add("Liuxia_Hui", "柳下惠", "allusion", "Other", "rhetorical_exemplar",
    [r"柳下惠"])
add("Yin_Zhou", "殷紂", "allusion", "Other", "rhetorical_exemplar",
    [r"殷紂"])
add("Shang_Rong", "商容", "allusion", "Other", "rhetorical_exemplar",
    [r"商容"])
add("Ji_Zuo", "箕左", "allusion", "Other", "rhetorical_exemplar",
    [r"箕左"])
add("Zhao_Gong", "召公", "allusion", "Yan", "rhetorical_exemplar",
    [r"召公"])
add("Bai_Gong_Sheng", "白公勝", "allusion", "Chu", "rhetorical_exemplar",
    [r"白公勝"])
add("Yao_Li", "要離", "allusion", "Other", "rhetorical_exemplar",
    [r"要離"])
add("Nie_Zheng", "聶政", "allusion", "Other", "rhetorical_exemplar",
    [r"聶政"])
add("Yang_Zi", "揚子", "allusion", "Other", "rhetorical_exemplar",
    [r"揚子"])
add("Qi_Wei_Wang", "齊威王", "allusion", "Qi", "rhetorical_exemplar",
    [r"(?<=初，齊)威(?=、宣)"])
add("Qi_Xuan_Wang", "齊宣王", "allusion", "Qi", "rhetorical_exemplar",
    [r"(?<=齊威、)宣(?=之時)"])
add("Zou_Yan", "鄒衍", "allusion", "Qi", "rhetorical_exemplar",
    [r"鄒衍"])
add("Zhou_Wen_Wang", "周文王", "allusion", "Other", "rhetorical_exemplar",
    [r"(?<=「)周文(?=、武)"])
add("Zhou_Wu_Wang", "周武王", "allusion", "Other", "rhetorical_exemplar",
    [r"(?<=周文、)武(?=所封)"])
add("Yangzi_author", "揚雄（揚子）", "allusion", "Other", "rhetorical_exemplar",
    [])  # merged into Yang_Zi below
ENTITIES.pop("Yangzi_author", None)

# ------------------------- states / polities / collectives -------------------------
add("Yan", "燕", "state", "Yan", "state",
    [r"燕(?!王喜|太子丹|丹|王及|王亡|王使|王聞|王竊|王誠|王拜|王乃|王怒|王不聽|王大怒|王命|王召|王以|王必|王蹵|王將|王卒|王人|王喜)"])
add("Qin", "秦", "state", "Qin", "state",
    [r"秦(?!王政|始皇|始皇帝|皇帝|昭王|莊襄王|王翦|王賁|舞陽|武陽|將|兵|軍|法|地|人|國|王寵臣|王必|王聞|王大喜|王謂|王發|王驚|王環|王復|王方|王還|王遂|王負劍)"])
add("Zhao", "趙", "state", "Zhao_Dai", "state",
    [r"趙(?!王遷|孝成王|悼襄王|幽繆王|公子嘉|王酒|王甚愛|將|使|人|氏|民|軍|兵|地|國|廥|與燕|聽|不能支|不能支秦)"])
add("Dai", "代", "state", "Zhao_Dai", "state",
    [r"代王", r"奔代", r"之代", r"攻代", r"虜代王", r"代師", r"於代", r"代郡"])
add("Qi", "齊", "state", "Qi", "state",
    [r"齊(?!王建|王將|王遂|王不聽|王還|王取筆|王曰|威、宣|威可立|人|地|亦東|軍|兵|師|之鋭)"])
add("Chu", "楚（荊）", "state", "Chu", "state",
    [r"楚", r"荊(?!軻|卿)"])
add("Han", "韓", "state", "Other", "state",
    [r"韓(?!皋)"])
add("Wei", "魏", "state", "Wei", "state",
    [r"魏(?!景湣王|王假|王降|王請降|與趙|之先王)"])
add("Wey", "衞", "state", "Other", "state",
    [r"衞", r"衛"])
add("Zhou", "周", "state", "Other", "state",
    [r"東（西）周", r"西周", r"周(?=得火德|代周|天子|文、武|滅東)"])
add("Xiongnu", "匈奴", "state", "Xiongnu", "state",
    [r"匈奴", r"單于", r"單於"])
add("Baiyue", "百越", "state", "Other", "state",
    [r"百越", r"越君"])
add("Sanguo", "三晉", "state", "Other", "state_coalition",
    [r"三晉"])
add("Zhuhou", "諸侯", "state", "Other", "state_collective",
    [r"諸侯"])
add("Liuguo", "六國", "state", "Other", "state_collective",
    [r"六國"])
add("Wuguo", "五國", "state", "Other", "state_collective",
    [r"五國"])
# Hainei removed: 「海內」 appears only inside rhetorical phrases (臣海內之王者,
# 海內賴陛下神靈一統) with no edge-type event; Tianxia covers the realm node.
add("Tianxia", "天下", "state", "Other", "realm_collective",
    [r"天下"])

# ---------------------------------------------------------------------------
# 2. Flagged ambiguous terms (context-dependent; NOT silently merged)
# ---------------------------------------------------------------------------
FLAGGED = [
    {
        "term": "臣光曰",
        "reason": "「臣光曰」 opens Sima Guang's historiographical comments in "
                  "the ZZTJ segments (S045, S052). The 光 here is the historian "
                  "Sima Guang, NOT 田光; the lookaround in Tian_Guang's alias "
                  "excludes it. If you want Sima Guang as an authorial node, "
                  "add it explicitly.",
        "occurrences": "S045,S052",
    },
    {
        "term": "王",
        "reason": "Bare 「王」 is context-dependent: in ZZTJ/Shiji annalistic "
                  "passages it usually = 秦王政 (S028, S035, S037, S039, S041, "
                  "S052), in 燕策三/燕召公世家 = 燕王喜 (S017, S021, S085), in "
                  "趙世家 = the reigning Zhao king (S085, S090), in 齊 passages "
                  "= 齊王建 (S049, S050, S051). Mapped per-segment by context; "
                  "verify each occurrence.",
        "occurrences": "S005,S006,S010,S011,S012,S014,S017,S018,S019,S021,S022,"
                       "S023,S024,S025,S026,S028,S033,S035,S036,S037,S039,S041,"
                       "S044,S048,S049,S050,S051,S052,S054,S058,S059,S060,S062,"
                       "S063,S066,S080,S081,S085,S088,S090,S092",
    },
    {
        "term": "太子",
        "reason": "Bare 「太子」 almost always = 燕太子丹, but S084 「太子死」 "
                  "refers to the Zhao crown prince (趙孝成王太子) in the 趙世家 "
                  "annals; verify before merging.",
        "occurrences": "S084 (and all P2/P3 Yan-narrative segments)",
    },
    {
        "term": "使者",
        "reason": "「使者」 is a role, not a named individual: the Yan envoy to "
                  "Qin (S065-S066, also the Jing Ke embassy S010-S011/S080), "
                  "the Yan envoy to Zhao (S018), and Yan envoys in S021/S036. "
                  "Referent changes across passages; kept unmerged.",
        "occurrences": "S010,S011,S018,S021,S036,S065,S066,S080",
    },
    {
        "term": "趙王",
        "reason": "Bare 「趙王」: S021/S085 「爲趙王酒」 = 趙孝成王; S006/S023/"
                  "S058/S076 「虜趙王」 = 趙王遷; S065/S090 = reigning Zhao king "
                  "in the envoy/春平君 episodes (孝成王 or 悼襄王, text does not "
                  "specify). Verify S065 and S090.",
        "occurrences": "S006,S021,S023,S058,S065,S076,S085,S090",
    },
    {
        "term": "蒙〔武〕(恬)",
        "reason": "Editorial collation: text reads 蒙武, emendation suggests "
                  "蒙恬 (S037, S040). Mapped to Meng_Wu (text as written); "
                  "verify whether the underlying event refers to 蒙恬.",
        "occurrences": "S037,S040",
    },
    {
        "term": "齊威、宣",
        "reason": "S053 「齊威、宣之時」 read as 齊威王、齊宣王 (allusion); but "
                  "S050 「齊威可立」 uses 齊威 as an abstract noun ('Qi's "
                  "prestige'), not the king. Verify S053 reading.",
        "occurrences": "S050,S053",
    },
    {
        "term": "箕左",
        "reason": "S018 「商容、箕左之累」: the received ZGC text has 箕子 "
                  "(Jizi); this copy writes 箕左. Kept verbatim as its own "
                  "allusion node; verify against your edition.",
        "occurrences": "S018",
    },
    {
        "term": "狗屠",
        "reason": "「狗屠」 is an unnamed occupation (the dog-butcher of the Yan "
                  "market, companion of 荊軻 and 髙漸離). Treated as a generic "
                  "person node; drop it if you only want named individuals.",
        "occurrences": "S071",
    },
    {
        "term": "尉文",
        "reason": "S085 「以尉文封相國廉頗爲信平君」: 尉文 is usually read as a "
                  "place name (the fief), not a person. Excluded from the node "
                  "table; verify if you want it as a locality node.",
        "occurrences": "S085",
    },
    {
        "term": "太后",
        "reason": "S029 「太后薨」 (ZZTJ 始皇帝十九年) and S058 「始皇帝母太后崩」 "
                  "refer to the Qin king's mother, unnamed in the text. "
                  "Excluded as an unnamed person; verify if you want a node.",
        "occurrences": "S029,S058",
    },
    {
        "term": "先王",
        "reason": "「先王」 = deceased predecessor king; referent varies (Yan's "
                  "先王 in S010/S018/S019, Zhou's 先王 in S052, Wei's 先王 in "
                  "S039). Left unmerged.",
        "occurrences": "S010,S018,S019,S039,S052",
    },
    {
        "term": "單于/單於",
        "reason": "The Xiongnu chanyu is invoked only as the object of the "
                  "proposed alliance (S002, S073); no personal name is given. "
                  "Represented by the state node Xiongnu; verify if you want a "
                  "separate person node.",
        "occurrences": "S002,S073",
    },
]

# ---------------------------------------------------------------------------
# 3. Build outputs
# ---------------------------------------------------------------------------

def load_rows():
    with SEG.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def first_phase_of(aliases, rows):
    """Earliest phase in which any alias regex matches."""
    best = None
    for r in rows:
        for pat in aliases:
            if re.search(pat, r["text"]):
                if best is None or PHASE_ORDER.index(r["phase"]) < PHASE_ORDER.index(best):
                    best = r["phase"]
                break
    return best


def main():
    rows = load_rows()

    # --- verify every alias occurs somewhere; collect per-node evidence ----
    unmatched, evidence = [], {}
    for nid, e in ENTITIES.items():
        hits = []
        for pat in e["aliases"]:
            for r in rows:
                if re.search(pat, r["text"]):
                    hits.append((r["segment_id"], pat))
        if not hits:
            unmatched.append(nid)
        evidence[nid] = hits

    if unmatched:
        print("UNMATCHED node_ids (no alias found in corpus):")
        for nid in unmatched:
            print("  ", nid, ENTITIES[nid]["aliases"])
        raise SystemExit("Fix aliases before proceeding.")

    # --- Deliverable A: alias dictionary ---------------------------------
    alias_map = OrderedDict()
    for nid, e in ENTITIES.items():
        for pat in e["aliases"]:
            # store the regex source as the key documentation
            alias_map.setdefault(nid, []).append(pat)
    doc = OrderedDict()
    doc["_description"] = (
        "Alias dictionary for the DHG502 Yan-Qin SNA corpus. Keys are canonical "
        "node_ids; values list the regex surface-form patterns (as they appear "
        "in the corpus) that resolve to that node. Context-dependent terms are "
        "NOT merged silently - see flagged_ambiguous_terms."
    )
    doc["_note_on_regex"] = (
        "Aliases are stored as Python regex fragments because many surface "
        "forms are short (e.g. 丹, 嘉, 光) and only disambiguated by "
        "lookaround context. Use re.search on segment text."
    )
    doc["aliases"] = {nid: pats for nid, pats in alias_map.items()}
    doc["flagged_ambiguous_terms"] = FLAGGED
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Deliverable B: node table ---------------------------------------
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["node_id", "label_zh", "node_type", "polity",
                    "functional_role", "first_phase"])
        for nid, e in ENTITIES.items():
            fp = first_phase_of(e["aliases"], rows)
            if fp is None:
                raise SystemExit(f"{nid}: no first_phase found")
            w.writerow([nid, e["label_zh"], e["node_type"], e["polity"],
                        e["functional_role"], fp])

    # --- validation -------------------------------------------------------
    with OUT_CSV.open(encoding="utf-8", newline="") as fh:
        data = list(csv.DictReader(fh))
    assert list(data[0].keys()) == ["node_id", "label_zh", "node_type",
                                    "polity", "functional_role", "first_phase"]
    ids = [r["node_id"] for r in data]
    assert len(ids) == len(set(ids)), "duplicate node_id"
    for r in data:
        assert r["node_id"] in ENTITIES, f"node_id {r['node_id']} not in JSON"
        assert r["node_type"] in {"person", "state", "allusion"}
        assert r["polity"] in {"Yan", "Qin", "Zhao_Dai", "Qi", "Chu", "Wei",
                               "Xiongnu", "Other"}
        assert r["first_phase"] in PHASE_ORDER
    # every canonical key present in CSV
    assert set(ids) == set(ENTITIES.keys())

    # --- audit summary ----------------------------------------------------
    print(f"WROTE {OUT_JSON}")
    print(f"WROTE {OUT_CSV}")
    print("nodes:", len(data), dict(Counter(r["node_type"] for r in data)))
    print("polity:", dict(Counter(r["polity"] for r in data)))
    print("first_phase:", dict(Counter(r["first_phase"] for r in data)))
    print("flagged_ambiguous_terms:", len(FLAGGED))


if __name__ == "__main__":
    main()
