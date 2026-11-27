#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_edges.py
================
Builds data/edges.csv — directed relationships between the canonical nodes in
data/nodes.csv, evidenced from data/segments.csv.

Columns: source_node,target_node,edge_type,valence,phase,text_source,segment_id,evidence_quote

Edge types:
  diplomatic_attempt   proposed/failed/strained diplomacy: envoy missions, peace
                       overtures, alliance proposals, territory exchanges,
                       submission offers (NOT completed alliances)
  hostage_tie          a person held as hostage in/by a state
  conspiracy_brokerage recruitment/brokerage inside the assassination plot
  sacrifice_resource   a person gives life/head/wealth/land as a resource
  military_conflict    armed attack, battle, siege, capture, killing in war
  allusion_reference   a speaker cites a historical figure/precedent as argument

Strict rules enforced by code:
  * source_node/target_node must exist in nodes.csv
  * evidence_quote must be a verbatim substring of the cited segment's text
  * no duplicate (source_node,target_node,edge_type,segment_id)
  * phase/text_source must match the cited segment
"""

import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEG = ROOT / "data" / "segments.csv"
NODES = ROOT / "data" / "nodes.csv"
OUT = ROOT / "data" / "edges.csv"

# ---------------------------------------------------------------------------
# Edge definitions.
# Each tuple: (source, target, edge_type, valence, segment_id, evidence_quote)
# phase and text_source are derived from the segment at build time.
# ---------------------------------------------------------------------------
E = []

def add(src, tgt, etype, val, sid, quote):
    E.append((src, tgt, etype, val, sid, quote))

# =============== P1: pre-diplomacy (Yan-Zhao wars, Qin rise) ===============

# --- S017 (ZGC): 栗腹 mission & Yan attack on Zhao ---
add("Yan_Wang_Xi", "Zhao_Xiaocheng_Wang", "diplomatic_attempt", "positive", "S017",
    "燕王喜使栗腹以百金為趙孝成王壽，酒三日")
add("Yan", "Zhao", "military_conflict", "negative", "S017",
    "遽起六十萬以攻趙。令栗腹以四十萬攻鄗，使慶秦以二十萬攻代")
add("Li_Fu", "Zhao", "military_conflict", "negative", "S017",
    "令栗腹以四十萬攻鄗")
add("Qin_Qing", "Dai", "military_conflict", "negative", "S017",
    "使慶秦以二十萬攻代")
add("Lian_Po", "Li_Fu", "military_conflict", "negative", "S017",
    "趙使廉頗以八萬遇栗腹於鄗")
add("Le_Cheng", "Qin_Qing", "military_conflict", "negative", "S017",
    "使樂乘以五萬遇慶秦於代")
add("Le_Jian", "Zhao", "diplomatic_attempt", "neutral", "S017",
    "樂間入趙")

# --- S018/S019 (ZGC): 燕王喜 apology letter to 樂間 ---
add("Yan_Wang_Xi", "Le_Jian", "diplomatic_attempt", "positive", "S018",
    "燕王以書且謝焉")
add("Yan_Wang_Xi", "Le_Jian", "allusion_reference", "neutral", "S018",
    "寡人雖不肖乎，未如殷紂之亂也；君雖不得意乎，未如商容、箕左之累也")
add("Yan_Wang_Xi", "Le_Jian", "allusion_reference", "neutral", "S019",
    "昔者，柳下惠吏於魯，三黜而不去")

# --- S020 (ZGC): 樂間/樂乘 stay in Zhao ---
add("Le_Jian", "Zhao", "diplomatic_attempt", "negative", "S020",
    "樂間、樂乘怨不用其計二人卒留趙，不報")

# --- S021 (Shiji): 栗腹約歡趙, war, 將渠 peace ---
add("Yan_Wang_Xi", "Zhao", "diplomatic_attempt", "positive", "S021",
    "燕王命相栗腹約歡趙，以五百金爲趙王酒")
add("Yan", "Zhao", "military_conflict", "negative", "S021",
    "卒起二軍，車二千乘，栗腹將而攻鄗，卿秦攻代")
add("Jiang_Qu", "Yan_Wang_Xi", "diplomatic_attempt", "neutral", "S021",
    "唯獨大夫將渠謂燕王曰：「與人通關約交，以五百金飲人之王，使者報而反攻之，不祥，兵無成功。」")
add("Lian_Po", "Li_Fu", "military_conflict", "negative", "S021",
    "趙使廉頗將，撃破栗腹於鄗")
add("Lian_Po", "Yan", "military_conflict", "negative", "S021",
    "廉頗逐之五百餘里，圍其國")
add("Jiang_Qu", "Zhao", "diplomatic_attempt", "positive", "S021",
    "燕相將渠以處和。趙聽將渠，解燕圍")
add("Le_Jian", "Zhao", "diplomatic_attempt", "neutral", "S021",
    "樂閒奔趙")

# --- S022 (Shiji): Zhao-Yan wars, 劇辛/龐煖, hostage return ---
add("Zhao", "Yan", "military_conflict", "negative", "S022",
    "趙使李牧攻燕，拔武遂、方城")
add("Yan", "Zhao", "military_conflict", "negative", "S022",
    "燕使劇辛將撃趙")
add("Pang_Nuan", "Ju_Xin", "military_conflict", "negative", "S022",
    "趙使龐煖撃之，取燕軍二萬，殺劇辛")
add("Yan_Dan", "Qin", "hostage_tie", "negative", "S022",
    "二十三年，太子丹質於秦，亡歸燕")
add("Qin", "Zhao", "military_conflict", "negative", "S022",
    "秦拔趙楡次三十七城，秦置大原郡")
add("Qin", "Wei", "military_conflict", "negative", "S022",
    "秦拔魏二十城，置東郡")
add("Qin", "Zhou", "military_conflict", "negative", "S022",
    "秦滅東（西）周，置三川郡")

# --- S084-S092 (Shiji 趙世家) P1 Yan-Zhao / Zhao-Qin relations ---
add("Yan", "Zhao", "military_conflict", "negative", "S084",
    "十年，燕攻昌壯，五月拔之")
add("Le_Cheng", "Xin_Liang", "military_conflict", "negative", "S084",
    "趙將樂乘、慶舍攻秦信梁軍，破之")
add("Qin", "Zhou", "military_conflict", "negative", "S084",
    "秦攻西周，拔之")
add("Lian_Po", "Yan", "military_conflict", "negative", "S085",
    "廉頗爲趙將，破殺栗腹，虜卿秦、樂閒")
add("Lian_Po", "Yan", "military_conflict", "negative", "S086",
    "十六年，廉頗圍燕")
add("Le_Cheng", "Yan", "military_conflict", "negative", "S086",
    "十七年，假相大將武襄君攻燕，圍其國")
add("Yanling_Jun", "Yan", "military_conflict", "negative", "S086",
    "十八年，延陵鈞率師從相國信平君助魏攻燕")
add("Zhao", "Yan", "diplomatic_attempt", "neutral", "S086",
    "十九年，趙與燕易土：以龍兌、汾門、臨樂與燕；燕以葛、武陽、平舒與趙")
add("Yan", "Zhao", "diplomatic_attempt", "neutral", "S086",
    "趙與燕易土：以龍兌、汾門、臨樂與燕；燕以葛、武陽、平舒與趙")
add("Qin", "Zhao", "military_conflict", "negative", "S086",
    "秦拔我楡次三十七城")
add("Li_Mu", "Yan", "military_conflict", "negative", "S090",
    "二年，李牧將，攻燕，拔武遂、方城")
# 趙王 in S090 = 趙悼襄王: the annalistic sequence within 趙世家 dates this
# block — S088 「子偃立，是爲悼襄王」, S089 「悼襄王元年」, S090 「二年…」.
# The reigning Zhao king in 悼襄王二年 is therefore 悼襄王.
add("Zhao_Daoxiang_Wang", "Chunping_Jun", "diplomatic_attempt", "positive", "S090",
    "春平君者，趙王甚愛之而郎中之")
add("Zhao_Daoxiang_Wang", "Ping_Du", "diplomatic_attempt", "neutral", "S090",
    "君不如遣春平君而留平都")
add("Qin", "Chunping_Jun", "diplomatic_attempt", "negative", "S090",
    "秦召春平君，因而留之")
add("Xie_Jun", "Wenxin_Hou", "diplomatic_attempt", "positive", "S090",
    "泄鈞爲之謂文信侯曰")
add("Wenxin_Hou", "Chunping_Jun", "diplomatic_attempt", "positive", "S090",
    "君不如遣春平君而留平都")
add("Pang_Nuan", "Yan", "military_conflict", "negative", "S091",
    "三年，龐煖將，攻燕，禽其將劇辛")
add("Zhao", "Qin", "military_conflict", "negative", "S091",
    "四年，龐煖將趙、楚、魏、燕之鋭師，攻秦蕞，不拔")
add("Zhao", "Qi", "military_conflict", "negative", "S091",
    "移攻齊，取饒安")
add("Zhao", "Yan", "military_conflict", "negative", "S092",
    "九年，趙攻燕，取貍、陽城")
add("Qin", "Zhao", "military_conflict", "negative", "S092",
    "兵未罷，秦攻鄴，拔之")

# --- S013/S028/S030/S058 (Qin destroys Zhao; Dai founded) ---
add("Qin", "Han", "military_conflict", "negative", "S013",
    "秦虜滅韓王安，置潁川郡")
add("Qin", "Zhao", "military_conflict", "negative", "S013",
    "秦虜趙王遷，滅趙")
add("Dai_Wang_Jia", "Dai", "diplomatic_attempt", "neutral", "S013",
    "趙公子嘉自立爲代王")
add("Qin", "Zhao", "military_conflict", "negative", "S028",
    "克邯鄲，虜趙王遷")
add("Dai_Wang_Jia", "Dai", "diplomatic_attempt", "neutral", "S030",
    "趙公子嘉帥其宗族數百人奔代，自立為代王")
add("Dai", "Yan", "diplomatic_attempt", "positive", "S030",
    "與燕合兵，軍上谷")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S030",
    "王翦屯中山以臨燕")
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S058",
    "王翦、羌瘣盡定取趙地東陽，得趙王")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S058",
    "引兵欲攻燕，屯中山")
add("Dai", "Yan", "diplomatic_attempt", "positive", "S058",
    "趙公子嘉率其宗數百人之代，自立為代王，東與燕合兵，軍上谷")

# --- S031/S032 (Chu/Wei successions) ---
add("Chu_King_Fuchu", "Chu_King_Hao", "military_conflict", "negative", "S031",
    "郝庶兄負芻殺之，自立")

# --- S067-S071 (Jing Ke background) ---
add("Jing_Ke", "Wei_Yuan_Jun", "diplomatic_attempt", "negative", "S068",
    "以術説衞元君，衞元君不用")
add("Qin", "Wey", "military_conflict", "negative", "S068",
    "其後秦伐魏，置東郡，徙衞元君之支屬於野王")
add("Jing_Ke", "Gai_Nie", "diplomatic_attempt", "neutral", "S069",
    "荊軻嘗游過楡次，與蓋聶論劍")
add("Lu_Goujian", "Jing_Ke", "diplomatic_attempt", "negative", "S070",
    "魯句踐與荊軻博，爭道，魯句踐怒而叱之")
add("Jing_Ke", "Gou_Tu", "diplomatic_attempt", "positive", "S071",
    "荊軻既至燕，愛燕之狗屠及善撃筑者髙漸離")
add("Jing_Ke", "Gao_Jianli", "diplomatic_attempt", "positive", "S071",
    "荊軻既至燕，愛燕之狗屠及善撃筑者髙漸離")
add("Tian_Guang", "Jing_Ke", "diplomatic_attempt", "positive", "S071",
    "燕之處士田光先生亦善待之，知其非庸人也")

# =============== P2: alliance vs plot ===============

# --- S001 (ZGC): 丹歸國、問鞫武 ---
add("Yan_Dan", "Qin", "hostage_tie", "negative", "S001",
    "燕太子丹質於秦，亡歸")
add("Yan_Dan", "Ju_Wu", "diplomatic_attempt", "neutral", "S001",
    "太子丹患之，謂其太傅鞫武曰：「燕秦不兩立，愿太傅幸而圖之。」")
add("Ju_Wu", "Yan_Dan", "diplomatic_attempt", "neutral", "S001",
    "奈何以見陵之怨，欲排其逆鱗哉")

# --- S002 (ZGC): 樊於期奔燕、合縱之議、田光薦軻 ---
add("Fan_Yuqi", "Yan_Dan", "diplomatic_attempt", "positive", "S002",
    "樊將軍亡秦之燕，太子容之")
add("Ju_Wu", "Yan_Dan", "diplomatic_attempt", "neutral", "S002",
    "愿太子急遣樊將軍入匈奴以滅口。請西約三晉，南連齊、楚，北講於單於，然後乃可圖也")
add("Ju_Wu", "Sanguo", "diplomatic_attempt", "positive", "S002",
    "請西約三晉，南連齊、楚，北講於單於")
add("Ju_Wu", "Qi", "diplomatic_attempt", "positive", "S002",
    "南連齊、楚")
add("Ju_Wu", "Chu", "diplomatic_attempt", "positive", "S002",
    "南連齊、楚")
add("Ju_Wu", "Xiongnu", "diplomatic_attempt", "positive", "S002",
    "北講於單於")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S002",
    "夫樊將軍困窮於天下，歸身於丹，丹終不迫於強秦")
add("Ju_Wu", "Yan_Dan", "conspiracy_brokerage", "positive", "S002",
    "燕有田光先生者，其智深，其勇沉，可與之謀也")
add("Yan_Dan", "Tian_Guang", "diplomatic_attempt", "positive", "S002",
    "愿因太傅交於田先生，可乎")
add("Ju_Wu", "Tian_Guang", "diplomatic_attempt", "positive", "S002",
    "出見田光，道太子曰：「愿圖國事於先生。」")
add("Ju_Wu", "Yan_Dan", "allusion_reference", "neutral", "S002",
    "雖有管、晏，不能為謀")
add("Ju_Wu", "Fan_Yuqi", "diplomatic_attempt", "negative", "S002",
    "是以委肉當餓虎之蹊，禍必不振矣")

# --- S003 (ZGC): 田光見太子、薦荊軻 ---
add("Yan_Dan", "Tian_Guang", "diplomatic_attempt", "positive", "S003",
    "太子跪而逢迎，卻行為道，跪而拂席")
add("Tian_Guang", "Yan_Dan", "conspiracy_brokerage", "positive", "S003",
    "所善荊軻，可使也")
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S003",
    "愿因先生得愿交於荊軻，可乎")
add("Yan_Dan", "Tian_Guang", "conspiracy_brokerage", "neutral", "S003",
    "丹所報，先生所言者，國大事也，愿先生勿泄也")

# --- S004 (ZGC): 田光自刎 ---
add("Tian_Guang", "Jing_Ke", "conspiracy_brokerage", "positive", "S004",
    "光竊不自外，言足下於太子，愿足下過太子於宮")
add("Tian_Guang", "Yan_Dan", "sacrifice_resource", "negative", "S004",
    "於自殺以激荊軻，曰：「愿足下急過太子，言光已死，明不言也。」遂自剄而死。")

# --- S005 (ZGC): 丹謀劃、荊軻許諾 ---
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S005",
    "此丹之上愿，而不知所以委命，唯荊卿留意焉")
add("Yan_Dan", "Qin_Shi_Huang", "military_conflict", "negative", "S005",
    "誠得劫秦王，使悉反諸侯之侵地，若曹沫之與齊桓公，則大善矣；則不可，因而刺殺之")
add("Yan_Dan", "Jing_Ke", "allusion_reference", "neutral", "S005",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "positive", "S005",
    "於是尊荊軻為上卿，舍上舍，太子日日造問，供太牢異物，間進車騎美女，恣荊軻所欲")
add("Qin", "Han", "military_conflict", "negative", "S005",
    "今秦已虜韓王，盡納其地")
add("Qin", "Chu", "military_conflict", "negative", "S005",
    "又舉兵南伐楚，北臨趙")
add("Qin", "Zhao", "military_conflict", "negative", "S005",
    "王翦將數十萬之眾臨漳、鄴，而李信出太原，云中")
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S005",
    "王翦將數十萬之眾臨漳、鄴")
add("Li_Xin", "Zhao", "military_conflict", "negative", "S005",
    "李信出太原，云中")

# --- S006 (ZGC): 王翦破趙、荊軻索樊首 ---
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S006",
    "秦將王翦破趙，虜趙王，盡收其地，進兵北略地，至燕南界")
add("Jing_Ke", "Yan_Dan", "conspiracy_brokerage", "neutral", "S006",
    "誠能得樊將軍首，與燕督之地圖獻秦王秦王必說見臣，臣乃得有以報太子")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S006",
    "樊將軍以窮困來歸丹，丹不忍以己之私，而傷長者之意")

# --- S007 (ZGC): 樊於期自刎 ---
add("Jing_Ke", "Fan_Yuqi", "conspiracy_brokerage", "neutral", "S007",
    "荊軻知太子不忍，乃遂私見樊於期曰")
add("Fan_Yuqi", "Jing_Ke", "sacrifice_resource", "negative", "S007",
    "樊於期偏袒扼腕而進曰：「此臣日夜切齒拊心也，乃今得聞教。」遂自刎。")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S007",
    "太子聞之馳往，伏尸而哭，極哀")

# --- S008 (ZGC): 匕首、秦舞陽為副 ---
add("Yan_Dan", "Xu_Furen", "sacrifice_resource", "positive", "S008",
    "得趙人徐夫人之匕首，取之百金")
add("Yan_Dan", "Qin_Wuyang", "conspiracy_brokerage", "positive", "S008",
    "乃令秦武陽為副")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "neutral", "S008",
    "丹請先遣秦武陽")

# --- S009 (ZGC): 易水送別 ---
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "neutral", "S009",
    "太子及賓客知其事者，皆白衣冠以送之")
add("Gao_Jianli", "Jing_Ke", "diplomatic_attempt", "positive", "S009",
    "高漸離擊筑，荊軻和而歌，為變徵之聲")

# --- S033 (ZZTJ): 鞠武合縱之議、樊於期奔燕 ---
add("Yan_Dan", "Qin", "hostage_tie", "negative", "S033",
    "燕太子丹怨王，欲報之")
add("Yan_Dan", "Ju_Wu", "diplomatic_attempt", "neutral", "S033",
    "燕太子丹怨王，欲報之，以問其傅鞠武")
add("Ju_Wu", "Sanguo", "diplomatic_attempt", "positive", "S033",
    "鞠武請西約三晉，南連齊、楚，北媾匈奴以圖秦")
add("Ju_Wu", "Qi", "diplomatic_attempt", "positive", "S033",
    "南連齊、楚")
add("Ju_Wu", "Chu", "diplomatic_attempt", "positive", "S033",
    "南連齊、楚")
add("Ju_Wu", "Xiongnu", "diplomatic_attempt", "positive", "S033",
    "北媾匈奴以圖秦")
add("Fan_Yuqi", "Yan_Dan", "diplomatic_attempt", "positive", "S033",
    "將軍樊於期得罪，亡之燕；太子受而舍之")
add("Ju_Wu", "Yan_Dan", "diplomatic_attempt", "neutral", "S033",
    "願太子疾遣樊將軍入匈奴")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S033",
    "樊將軍窮困於天下，歸身於丹")
add("Ju_Wu", "Yan_Dan", "allusion_reference", "neutral", "S033",
    "是謂委肉當餓虎之蹊也")

# --- S034 (ZZTJ): 荊軻受命 ---
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S034",
    "太子聞衛人荊軻之賢，卑辭厚禮而請見之")
add("Yan_Dan", "Qin_Shi_Huang", "military_conflict", "negative", "S034",
    "劫秦王，使悉反諸侯侵地，若曹沫之與齊桓公，則大善矣；則不可，因而刺殺之")
add("Yan_Dan", "Jing_Ke", "allusion_reference", "neutral", "S034",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "positive", "S034",
    "於是舍荊卿於上舍，太子日造門下，所以奉養荊軻，無所不至")
add("Qin", "Han", "military_conflict", "negative", "S034",
    "今秦已虜韓王")
add("Qin", "Chu", "military_conflict", "negative", "S034",
    "又舉兵南伐楚，北臨趙")
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S034",
    "及王翦滅趙，太子聞之懼")
add("Jing_Ke", "Yan_Dan", "conspiracy_brokerage", "neutral", "S034",
    "誠得樊將軍首與燕督亢之地圖，奉獻秦王")
add("Jing_Ke", "Fan_Yuqi", "conspiracy_brokerage", "neutral", "S034",
    "荊軻乃私見樊於期曰：「秦之遇將軍，可謂深矣，父母宗族皆為戮沒")

# --- S072-S078 (Shiji 刺客列傳 P2) ---
add("Yan_Dan", "Qin", "hostage_tie", "negative", "S072",
    "會燕太子丹質秦亡歸燕")
add("Yan_Dan", "Zhao", "hostage_tie", "neutral", "S072",
    "燕太子丹者，故嘗質於趙")
add("Qin_Shi_Huang", "Yan_Dan", "diplomatic_attempt", "negative", "S072",
    "秦王政生於趙，其少時與丹驩。及政立爲秦王，而丹質於秦。秦王之遇燕太子丹不善")
add("Yan_Dan", "Qin_Shi_Huang", "diplomatic_attempt", "negative", "S072",
    "秦王之遇燕太子丹不善，故丹怨而亡歸。歸而求爲報秦王者，國小，力不能")
add("Yan_Dan", "Ju_Wu", "diplomatic_attempt", "neutral", "S072",
    "太子丹患之，問其傅鞠武")
add("Ju_Wu", "Yan_Dan", "diplomatic_attempt", "neutral", "S072",
    "柰何以見陵之怨，欲批其逆鱗哉")
add("Fan_Yuqi", "Yan_Dan", "diplomatic_attempt", "positive", "S073",
    "秦將樊於期得罪於秦王，亡之燕，太子受而舍之")
add("Ju_Wu", "Sanguo", "diplomatic_attempt", "positive", "S073",
    "請西約三晉，南連齊、楚，北購於單于")
add("Ju_Wu", "Qi", "diplomatic_attempt", "positive", "S073",
    "南連齊、楚")
add("Ju_Wu", "Chu", "diplomatic_attempt", "positive", "S073",
    "南連齊、楚")
add("Ju_Wu", "Xiongnu", "diplomatic_attempt", "positive", "S073",
    "北購於單于")
add("Ju_Wu", "Yan_Dan", "diplomatic_attempt", "neutral", "S073",
    "願太子疾遣樊將軍入匈奴以滅口")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S073",
    "夫樊將軍窮困於天下，歸身於丹，丹終不以迫於彊秦而棄所哀憐之交")
add("Ju_Wu", "Yan_Dan", "allusion_reference", "neutral", "S073",
    "雖有管、晏，不能爲之謀也")
add("Ju_Wu", "Yan_Dan", "conspiracy_brokerage", "positive", "S073",
    "燕有田光先生，其爲人智深而勇沈，可與謀")
add("Yan_Dan", "Tian_Guang", "diplomatic_attempt", "positive", "S073",
    "願因太傅而得交於田先生，可乎")
add("Yan_Dan", "Tian_Guang", "diplomatic_attempt", "positive", "S074",
    "太子逢迎，卻行爲導，跪而蔽席")
add("Tian_Guang", "Yan_Dan", "conspiracy_brokerage", "positive", "S074",
    "所善荊卿可使也")
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S074",
    "願因先生得結交於荊卿，可乎")
add("Yan_Dan", "Tian_Guang", "conspiracy_brokerage", "neutral", "S074",
    "丹所報，先生所言者，國之大事也，願先生勿泄也")
add("Tian_Guang", "Jing_Ke", "conspiracy_brokerage", "positive", "S074",
    "光竊不自外，言足下於太子也，願足下過太子於宮")
add("Tian_Guang", "Yan_Dan", "sacrifice_resource", "negative", "S074",
    "欲自殺以激荊卿，曰：「願足下急過太子，言光已死，明不言也。」")
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S075",
    "此丹之上願，而不知所委命，唯荊卿留意焉")
add("Yan_Dan", "Qin_Shi_Huang", "military_conflict", "negative", "S075",
    "誠得劫秦王，使悉反諸侯侵地，若曹沫之與齊桓公，則大善矣；則不可，因而刺殺之")
add("Yan_Dan", "Jing_Ke", "allusion_reference", "neutral", "S075",
    "若曹沫之與齊桓公，則大善矣")
add("Qin", "Han", "military_conflict", "negative", "S075",
    "今秦已虜韓王，盡納其地")
add("Qin", "Chu", "military_conflict", "negative", "S075",
    "又舉兵南伐楚，北臨趙")
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S075",
    "王翦將數十萬之衆距漳、鄴")
add("Li_Xin", "Zhao", "military_conflict", "negative", "S075",
    "李信出太原、雲中")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "positive", "S075",
    "於是尊荊卿爲上卿，舍上舍。太子日造門下，供太牢具")
add("Wang_Jian", "Zhao", "military_conflict", "negative", "S076",
    "秦將王翦破趙，虜趙王，盡收入其地，進兵北略地至燕南界")
add("Jing_Ke", "Yan_Dan", "conspiracy_brokerage", "neutral", "S076",
    "誠得樊將軍首與燕督亢之地圖，奉獻秦王，秦王必説見臣")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S076",
    "樊將軍窮困來歸丹，丹不忍以己之私而傷長者之意")
add("Jing_Ke", "Fan_Yuqi", "conspiracy_brokerage", "neutral", "S077",
    "荊軻知太子不忍，乃遂私見樊於期曰")
add("Fan_Yuqi", "Jing_Ke", "sacrifice_resource", "negative", "S077",
    "樊於期偏袒搤捥而進曰：「此臣之日夜切齒腐心也，乃今得聞教！」遂自剄。")
add("Yan_Dan", "Fan_Yuqi", "diplomatic_attempt", "positive", "S077",
    "太子聞之，馳往，伏尸而哭，極哀")
add("Yan_Dan", "Xu_Furen", "sacrifice_resource", "positive", "S078",
    "得趙人徐夫人匕首，取之百金")
add("Yan_Dan", "Qin_Wuyang", "conspiracy_brokerage", "positive", "S078",
    "乃令秦舞陽爲副")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "neutral", "S078",
    "丹請得先遣秦舞陽")
add("Yan_Dan", "Jing_Ke", "diplomatic_attempt", "neutral", "S079",
    "太子及賓客知其事者，皆白衣冠以送之")
add("Gao_Jianli", "Jing_Ke", "diplomatic_attempt", "positive", "S079",
    "髙漸離撃筑，荊軻和而歌，爲變徴之聲")

# =============== P3: assassination ===============

# --- S010 (ZGC): 賄蒙嘉、偽裝臣服 ---
add("Yan_Dan", "Meng_Jia", "diplomatic_attempt", "positive", "S010",
    "持千金之資幣物，厚遺秦王寵臣中庶子蒙嘉")
add("Meng_Jia", "Qin_Shi_Huang", "diplomatic_attempt", "positive", "S010",
    "嘉為先言於秦王曰")
add("Yan", "Qin", "diplomatic_attempt", "positive", "S010",
    "燕王誠振畏慕大王之威，不敢興兵以拒大王，愿舉國為內臣，比諸侯之列，給貢職如郡縣")
add("Yan_Dan", "Fan_Yuqi", "sacrifice_resource", "negative", "S010",
    "謹斬樊於期頭，及獻燕之督亢之地圖")
add("Yan", "Qin", "sacrifice_resource", "neutral", "S010",
    "謹斬樊於期頭，及獻燕之督亢之地圖，函封，燕王拜送於庭")

# --- S011 (ZGC): 咸陽宮行刺 ---
add("Qin_Shi_Huang", "Jing_Ke", "diplomatic_attempt", "positive", "S011",
    "乃朝服，設九賓，見燕使者咸陽宮")
add("Jing_Ke", "Qin_Shi_Huang", "military_conflict", "negative", "S011",
    "圖窮而匕首見。因左手拔秦王之袖，右持匕首揕抗之")
add("Qin_Shi_Huang", "Jing_Ke", "military_conflict", "negative", "S011",
    "遂拔以擊荊軻，斷其左股")
add("Xia_Wuqie", "Jing_Ke", "military_conflict", "negative", "S011",
    "侍醫夏無且，以其所奉藥曩體軻")

# --- S014 (Shiji): 使荊軻刺秦王 ---
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S014",
    "太子丹陰養壯士二十人，使荊軻獻督亢地圖於秦，因襲刺秦王")
add("Yan_Dan", "Qin_Shi_Huang", "military_conflict", "negative", "S014",
    "使荊軻獻督亢地圖於秦，因襲刺秦王")
add("Qin_Shi_Huang", "Jing_Ke", "military_conflict", "negative", "S014",
    "秦王覺，殺軻")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S014",
    "使將軍王翦撃燕")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S014",
    "使將軍王翦撃燕")
add("Yan", "Qin", "sacrifice_resource", "neutral", "S014",
    "使荊軻獻督亢地圖於秦")

# --- S035 (ZZTJ): 咸陽宮行刺 ---
add("Jing_Ke", "Meng_Jia", "diplomatic_attempt", "positive", "S035",
    "荊軻至咸陽，因王寵臣蒙嘉卑辭以求見")
add("Meng_Jia", "Qin_Shi_Huang", "diplomatic_attempt", "positive", "S035",
    "因王寵臣蒙嘉卑辭以求見，王大喜")
add("Jing_Ke", "Qin_Shi_Huang", "military_conflict", "negative", "S035",
    "圖窮而匕首見，因把王袖而揕之")
add("Qin_Shi_Huang", "Jing_Ke", "military_conflict", "negative", "S035",
    "遂體解荊軻以徇")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S035",
    "王於是大怒，益發兵詣趙，就王翦以伐燕")
add("Qin", "Yan", "military_conflict", "negative", "S035",
    "與燕師、代師戰於易水之西，大破之")
add("Qin", "Dai", "military_conflict", "negative", "S035",
    "與燕師、代師戰於易水之西，大破之")

# --- S059 (Shiji): 刺秦、易水之西 ---
add("Yan_Dan", "Jing_Ke", "conspiracy_brokerage", "positive", "S059",
    "燕太子丹患秦兵至國，恐，使荊軻刺秦王")
add("Yan_Dan", "Qin_Shi_Huang", "military_conflict", "negative", "S059",
    "使荊軻刺秦王")
add("Qin_Shi_Huang", "Jing_Ke", "military_conflict", "negative", "S059",
    "秦王覺之，體解軻以徇")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S059",
    "而使王翦、辛勝攻燕")
add("Qin", "Yan", "military_conflict", "negative", "S059",
    "燕、代發兵擊秦軍，秦軍破燕易水之西")
add("Yan", "Qin", "military_conflict", "negative", "S059",
    "燕、代發兵擊秦軍")
add("Dai", "Qin", "military_conflict", "negative", "S059",
    "燕、代發兵擊秦軍")

# --- S080 (Shiji): 賄蒙嘉、行刺（長段） ---
add("Yan_Dan", "Meng_Jia", "diplomatic_attempt", "positive", "S080",
    "持千金之資幣物，厚遺秦王寵臣中庶子蒙嘉")
add("Meng_Jia", "Qin_Shi_Huang", "diplomatic_attempt", "positive", "S080",
    "嘉爲先言於秦王曰")
add("Yan", "Qin", "diplomatic_attempt", "positive", "S080",
    "燕王誠振怖大王之威，不敢舉兵以逆軍吏，願舉國爲内臣，比諸侯之列，給貢職如郡縣")
add("Yan_Dan", "Fan_Yuqi", "sacrifice_resource", "negative", "S080",
    "謹斬樊於期之頭，及獻燕督亢之地圖")
add("Yan", "Qin", "sacrifice_resource", "neutral", "S080",
    "謹斬樊於期之頭，及獻燕督亢之地圖，函封，燕王拜送于庭")
add("Qin_Shi_Huang", "Jing_Ke", "diplomatic_attempt", "positive", "S080",
    "秦王聞之，大喜，乃朝服，設九賓，見燕使者咸陽宮")
add("Jing_Ke", "Qin_Shi_Huang", "military_conflict", "negative", "S080",
    "圖窮而匕首見。因左手把秦王之袖，而右手持匕首揕之")
add("Qin_Shi_Huang", "Jing_Ke", "military_conflict", "negative", "S080",
    "秦王驚，自引而起，袖絶")

# =============== P4: fall of Yan ===============

# --- S012 (ZGC): 秦伐燕、滅燕 ---
add("Qin", "Yan", "military_conflict", "negative", "S012",
    "秦大怒燕，益發兵詣趙，詔王翦軍以伐燕。十月而拔燕薊城")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S012",
    "詔王翦軍以伐燕。十月而拔燕薊城")
add("Yan_Wang_Xi", "Yan_Dan", "sacrifice_resource", "negative", "S012",
    "王急，用代王嘉計，殺太子丹，欲獻之秦")
add("Dai_Wang_Jia", "Yan_Wang_Xi", "diplomatic_attempt", "negative", "S012",
    "用代王嘉計，殺太子丹，欲獻之秦")
add("Li_Xin", "Yan_Wang_Xi", "military_conflict", "negative", "S012",
    "秦將李信追擊燕王")

# --- S015/S016 (Shiji 燕世家) ---
add("Qin", "Yan", "military_conflict", "negative", "S015",
    "秦攻拔我薊，燕王亡，徙居遼東，斬丹以獻秦")
add("Yan_Wang_Xi", "Yan_Dan", "sacrifice_resource", "negative", "S015",
    "燕王亡，徙居遼東，斬丹以獻秦")
add("Qin", "Wei", "military_conflict", "negative", "S015",
    "三十年，秦滅魏")
add("Qin", "Yan", "military_conflict", "negative", "S016",
    "秦拔遼東，虜燕王喜，卒滅燕")
add("Wang_Ben", "Dai_Wang_Jia", "military_conflict", "negative", "S016",
    "秦將王賁亦虜代王嘉")

# --- S023 (Shiji 王翦列傳) ---
add("Jing_Ke", "Qin_Shi_Huang", "military_conflict", "negative", "S023",
    "燕使荊軻為賊於秦")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S023",
    "秦王使王翦攻燕")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S023",
    "秦王使王翦攻燕。燕王喜走遼東，翦遂定燕薊而還")
add("Wang_Ben", "Chu", "military_conflict", "negative", "S023",
    "秦使翦子王賁擊荊，荊兵敗")
add("Wang_Ben", "Wei", "military_conflict", "negative", "S023",
    "還擊魏，魏王降，遂定魏地")

# --- S024-S027 (Shiji 王翦列傳 滅楚) ---
add("Li_Xin", "Yan_Dan", "military_conflict", "negative", "S024",
    "嘗以兵數千逐燕太子丹至於衍水中，卒破得丹")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "neutral", "S024",
    "始皇問王翦，王翦曰：「非六十萬人不可。」")
add("Qin_Shi_Huang", "Li_Xin", "diplomatic_attempt", "positive", "S024",
    "遂使李信及蒙恬將二十萬南伐荊")
add("Li_Xin", "Chu", "military_conflict", "negative", "S024",
    "李信攻平與，蒙恬攻寢，大破荊軍")
add("Meng_Tian", "Chu", "military_conflict", "negative", "S024",
    "李信攻平與，蒙恬攻寢，大破荊軍")
add("Chu", "Qin", "military_conflict", "negative", "S024",
    "荊人因隨之，三日三夜不頓舍，大破李信軍，入兩壁，殺七都尉，秦軍走")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S025",
    "於是王翦將兵六十萬人，始皇自送至灞上")
add("Wang_Jian", "Qin_Shi_Huang", "diplomatic_attempt", "neutral", "S025",
    "王翦行，請美田宅園池甚眾")
add("Wang_Jian", "Chu", "military_conflict", "negative", "S026",
    "王翦果代李信擊荊")
add("Wang_Jian", "Xiang_Yan", "military_conflict", "negative", "S026",
    "至蘄南，殺其將軍項燕")
add("Wang_Jian", "Chu_King_Fuchu", "military_conflict", "negative", "S026",
    "歲餘，虜荊王負芻，竟平荊地為郡縣")
add("Wang_Jian", "Baiyue", "military_conflict", "negative", "S026",
    "因南征百越之君")
add("Wang_Ben", "Yan", "military_conflict", "negative", "S026",
    "而王翦子王賁，與李信破定燕、齊地")
add("Wang_Ben", "Qi", "military_conflict", "negative", "S026",
    "而王翦子王賁，與李信破定燕、齊地")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S027",
    "秦始皇二十六年，盡并天下，王氏、蒙氏功為多")

# --- S036-S046 (ZZTJ P4) ---
add("Wang_Ben", "Chu", "military_conflict", "negative", "S037",
    "王賁伐楚，取十餘城")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "neutral", "S037",
    "王以問王翦，王翦曰：「非六十萬人不可。」")
add("Qin_Shi_Huang", "Li_Xin", "diplomatic_attempt", "positive", "S037",
    "遂使李信、蒙〔武〕(恬)將二十萬人伐楚")
add("Wang_Ben", "Wei_Wang_Jia", "military_conflict", "negative", "S038",
    "王賁伐魏，引河溝以灌大梁")
add("Qin_Shi_Huang", "Anling_Jun", "diplomatic_attempt", "neutral", "S039",
    "王使人謂安陵君曰：「寡人欲以五百里地易安陵。」")
add("Anling_Jun", "Qin_Shi_Huang", "diplomatic_attempt", "negative", "S039",
    "臣受地於魏之先王，願終守之，弗敢易")
add("Li_Xin", "Chu", "military_conflict", "negative", "S040",
    "李信攻平輿，蒙〔武〕(恬)攻寢，大破楚軍")
add("Chu", "Qin", "military_conflict", "negative", "S040",
    "楚人因隨之，三日三夜不頓舍，大敗李信，入兩壁，殺七都尉；李信奔還")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S041",
    "於是王翦將六十萬人伐楚")
add("Wang_Jian", "Qin_Shi_Huang", "diplomatic_attempt", "neutral", "S041",
    "王翦請美田宅甚眾")
add("Wang_Jian", "Chu", "military_conflict", "negative", "S042",
    "王翦取陳以南至平輿")
add("Wang_Jian", "Xiang_Yan", "military_conflict", "negative", "S042",
    "至蘄南，殺其將軍項燕")
add("Wang_Jian", "Chu_King_Fuchu", "military_conflict", "negative", "S043",
    "王翦、蒙武虜楚王負芻")
add("Meng_Wu", "Chu_King_Fuchu", "military_conflict", "negative", "S043",
    "王翦、蒙武虜楚王負芻")
add("Wang_Ben", "Yan_Wang_Xi", "military_conflict", "negative", "S044",
    "使王賁攻遼東，虜燕王喜")
add("Qin", "Yan", "military_conflict", "negative", "S044",
    "大興兵，使王賁攻遼東，虜燕王喜")
add("Yan_Dan", "Qin", "military_conflict", "negative", "S045",
    "燕丹不勝一朝之忿以犯虎狼之秦")
add("Yan_Dan", "Zhao_Gong", "allusion_reference", "neutral", "S045",
    "使召公之廟不祀忽諸")
add("Yan_Dan", "Bai_Gong_Sheng", "allusion_reference", "neutral", "S045",
    "其楚白公勝之流乎")
# --- edges for previously unused nodes, all verbatim-verified in raw_texts ---
# 曹沫/齊桓公 allusion cited by 太子丹 (S005 ZGC, S034 ZZTJ, S075 Shiji)
add("Yan_Dan", "Cao_Mo", "allusion_reference", "neutral", "S005",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Qi_Huan_Gong", "allusion_reference", "neutral", "S005",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Cao_Mo", "allusion_reference", "neutral", "S034",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Qi_Huan_Gong", "allusion_reference", "neutral", "S034",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Cao_Mo", "allusion_reference", "neutral", "S075",
    "若曹沫之與齊桓公，則大善矣")
add("Yan_Dan", "Qi_Huan_Gong", "allusion_reference", "neutral", "S075",
    "若曹沫之與齊桓公，則大善矣")
# 管、晏 allusion cited by 鞠武 (S002 ZGC, S073 Shiji)
add("Ju_Wu", "Guan_Zhong", "allusion_reference", "neutral", "S002",
    "雖有管、晏，不能為謀")
add("Ju_Wu", "Yan_Ying", "allusion_reference", "neutral", "S002",
    "雖有管、晏，不能為謀")
add("Ju_Wu", "Guan_Zhong", "allusion_reference", "neutral", "S073",
    "雖有管、晏，不能爲之謀也")
add("Ju_Wu", "Yan_Ying", "allusion_reference", "neutral", "S073",
    "雖有管、晏，不能爲之謀也")
# 柳下惠 allusion in 燕王喜's letter to 樂間 (S019 ZGC)
add("Yan_Wang_Xi", "Liuxia_Hui", "allusion_reference", "neutral", "S019",
    "昔者，柳下惠吏於魯，三黜而不去")
# 殷紂/商容/箕左 allusions in the same letter (S018 ZGC)
add("Yan_Wang_Xi", "Yin_Zhou", "allusion_reference", "neutral", "S018",
    "寡人雖不肖乎，未如殷紂之亂也")
add("Yan_Wang_Xi", "Shang_Rong", "allusion_reference", "neutral", "S018",
    "君雖不得意乎，未如商容、箕左之累也")
add("Yan_Wang_Xi", "Ji_Zuo", "allusion_reference", "neutral", "S018",
    "君雖不得意乎，未如商容、箕左之累也")
# 秦虜趙王遷 - Qin captures the Zhao king (S013 Shiji, S028 ZZTJ)
add("Qin", "Zhao_Wang_Qian", "military_conflict", "negative", "S013",
    "秦虜趙王遷，滅趙")
add("Qin", "Zhao_Wang_Qian", "military_conflict", "negative", "S028",
    "克邯鄲，虜趙王遷")
# 慶舍 military actions (S084 Shiji 趙世家)
add("Qing_She", "Xin_Liang", "military_conflict", "negative", "S084",
    "趙將樂乘、慶舍攻秦信梁軍，破之")
# 秦兼天下/并天下 - Qin conquers all-under-heaven (S012 ZGC, S052/S082)
add("Qin", "Tianxia", "military_conflict", "negative", "S012",
    "五歲而卒滅燕國，而虜燕王喜。秦兼天下")
add("Qin", "Tianxia", "military_conflict", "negative", "S052",
    "王初并天下")
add("Qin", "Tianxia", "military_conflict", "negative", "S082",
    "其明年，秦并天下，立號爲皇帝")
# 齊不助五國攻秦 (S048 ZZTJ) - Qi_Wang_Jian's failure to aid the Five States
add("Qi_Wang_Jian", "Wuguo", "diplomatic_attempt", "negative", "S048",
    "不助五國攻秦，秦以故得滅五國")
add("Yang_Zi", "Jing_Ke", "allusion_reference", "negative", "S045",
    "故揚子論之，以要離為蛛蝥之靡，聶政為壯士之靡，荊軻為刺客之靡")
add("Yao_Li", "Jing_Ke", "allusion_reference", "neutral", "S045",
    "以要離為蛛蝥之靡")
add("Nie_Zheng", "Jing_Ke", "allusion_reference", "neutral", "S045",
    "聶政為壯士之靡")
add("Wang_Ben", "Dai_Wang_Jia", "military_conflict", "negative", "S045",
    "王賁攻代，虜代王嘉")
add("Wang_Jian", "Baiyue", "military_conflict", "negative", "S046",
    "王翦悉定荊江南地，降百越之君")

# --- S048-S054 (Qi's fall, unification) ---
add("Jun_Wang_Hou", "Qin", "diplomatic_attempt", "positive", "S048",
    "齊君王后賢，事秦謹，與諸侯信")
add("Qin", "Sanguo", "military_conflict", "negative", "S048",
    "秦日夜攻三晉、燕、楚")
add("Qin", "Yan", "military_conflict", "negative", "S048",
    "秦日夜攻三晉、燕、楚")
add("Qin", "Chu", "military_conflict", "negative", "S048",
    "秦日夜攻三晉、燕、楚")
add("Hou_Sheng", "Qin", "diplomatic_attempt", "negative", "S048",
    "后勝相齊，多受秦間金")
add("Hou_Sheng", "Qi_Wang_Jian", "diplomatic_attempt", "negative", "S048",
    "勸王朝秦，不修攻戰之備，不助五國攻秦")
add("Yongmen_Sima", "Qi_Wang_Jian", "diplomatic_attempt", "negative", "S049",
    "雍門司馬〔橫戟當馬〕前曰：「所為立王者，為社稷耶，為王耶？」")
add("Jimo_Dafu", "Qi_Wang_Jian", "diplomatic_attempt", "positive", "S050",
    "即墨大夫聞之，見齊王曰")
add("Jimo_Dafu", "Sanguo", "diplomatic_attempt", "positive", "S050",
    "王收而與之〔十〕(百)萬人之眾，使收三晉之故地")
add("Jimo_Dafu", "Chu", "diplomatic_attempt", "positive", "S050",
    "王收而與之〔十〕(百)萬之師，使收楚故地")
add("Wang_Ben", "Qi_Wang_Jian", "military_conflict", "negative", "S051",
    "王賁自燕南攻齊，卒入臨淄")
add("Qin_Shi_Huang", "Qi_Wang_Jian", "diplomatic_attempt", "positive", "S051",
    "秦使人誘齊王，約封以五百里之地")
add("Qi_Wang_Jian", "Qin_Shi_Huang", "diplomatic_attempt", "negative", "S051",
    "齊王遂降，秦遷之共")
add("Liuguo", "Qin", "military_conflict", "negative", "S052",
    "然大要合從者，六國之利也")
add("Sanguo", "Qi", "diplomatic_attempt", "neutral", "S052",
    "夫三晉者，齊、楚之籓蔽")
add("Qin_Shi_Huang", "Zhuang_Xiang_Wang", "diplomatic_attempt", "positive", "S052",
    "追尊莊襄王為太上皇")
add("Zou_Yan", "Qi_Wei_Wang", "allusion_reference", "neutral", "S053",
    "初，齊威、宣之時，鄒衍論著終始五德之運")
add("Zou_Yan", "Qi_Xuan_Wang", "allusion_reference", "neutral", "S053",
    "初，齊威、宣之時，鄒衍論著終始五德之運")
add("Wang_Wan", "Qin_Shi_Huang", "diplomatic_attempt", "neutral", "S054",
    "丞相〔王〕綰〔等〕言：「燕、齊、荊地遠，不為置王，無以鎮之。請立諸子。」")
add("Li_Si", "Qin_Shi_Huang", "diplomatic_attempt", "neutral", "S054",
    "廷尉斯曰：「周文、武所封子弟同姓甚眾，然後屬疏遠")
add("Li_Si", "Zhou_Wen_Wang", "allusion_reference", "neutral", "S054",
    "周文、武所封子弟同姓甚眾")
add("Li_Si", "Zhou_Wu_Wang", "allusion_reference", "neutral", "S054",
    "周文、武所封子弟同姓甚眾")

# --- S057-S064 (Shiji 本紀 P4) ---
add("Qin", "Zhuhou", "military_conflict", "negative", "S057",
    "每破諸侯，寫放其宮室")
add("Wang_Ben", "Chu", "military_conflict", "negative", "S060",
    "王賁攻（薊）［荊］")
add("Wang_Jian", "Yan_Dan", "military_conflict", "negative", "S060",
    "遂破燕太子軍，取燕薊城，得太子丹之首")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S060",
    "遂破燕太子軍，取燕薊城")
add("Wang_Ben", "Wei", "military_conflict", "negative", "S061",
    "王賁攻魏，引河溝灌大梁，大梁城壞，其王請降")
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S062",
    "秦王復召王翦，彊起之，使將擊荊")
add("Wang_Jian", "Chu", "military_conflict", "negative", "S062",
    "取陳以南至平輿，虜荊王")
add("Xiang_Yan", "Changping_Jun", "diplomatic_attempt", "positive", "S062",
    "荊將項燕立昌平君為荊王，反秦於淮南")
add("Changping_Jun", "Qin", "military_conflict", "negative", "S062",
    "立昌平君為荊王，反秦於淮南")
add("Wang_Jian", "Changping_Jun", "military_conflict", "negative", "S062",
    "王翦、蒙武攻荊，破荊軍，昌平君死")
add("Meng_Wu", "Changping_Jun", "military_conflict", "negative", "S062",
    "王翦、蒙武攻荊，破荊軍，昌平君死")
add("Wang_Jian", "Xiang_Yan", "military_conflict", "negative", "S062",
    "昌平君死，項燕遂自殺")
add("Wang_Ben", "Yan_Wang_Xi", "military_conflict", "negative", "S063",
    "使王賁將，攻燕遼東，得燕王喜")
add("Wang_Ben", "Dai_Wang_Jia", "military_conflict", "negative", "S063",
    "還攻代，虜代王嘉")
add("Wang_Jian", "Baiyue", "military_conflict", "negative", "S063",
    "王翦遂定荊江南地；降越君")
add("Hou_Sheng", "Qi_Wang_Jian", "diplomatic_attempt", "negative", "S064",
    "齊王建與其相后勝發兵守其西界，不通秦")
add("Wang_Ben", "Qi_Wang_Jian", "military_conflict", "negative", "S064",
    "秦使將軍王賁從燕南攻齊，得齊王建")

# --- S065/S066 (ZGC 秦并趙北向迎燕): Yan envoy diplomacy ---
# 趙王 in S065/S066: the segment text never names the Zhao ruler, and the
# cross-segment inference (趙王遷 already captured in S013/S028, so the acting
# "趙王" would be 代王嘉) is NOT stated in these segments themselves. Per the
# user's rule — if it cannot be verified from the text, remove it — the four
# edges that depended on identifying this 趙王 as 代王嘉 have been REMOVED.
# Only edges whose endpoints are named in the segment text are kept.
add("Yan_Wang_Xi", "Qin_Shi_Huang", "diplomatic_attempt", "positive", "S065",
    "燕王聞之，使人賀秦王")
add("Yan_Wang_Xi", "Qin_Shi_Huang", "diplomatic_attempt", "positive", "S066",
    "燕王竊聞秦并趙，燕王使使者賀千金")
add("Qin_Shi_Huang", "Yan", "diplomatic_attempt", "positive", "S066",
    "秦王以為然，起兵而救燕")

# --- S081/S082 (Shiji 刺客列傳 P4) ---
add("Qin_Shi_Huang", "Wang_Jian", "diplomatic_attempt", "positive", "S081",
    "於是秦王大怒，益發兵詣趙，詔王翦軍以伐燕")
add("Wang_Jian", "Yan", "military_conflict", "negative", "S081",
    "詔王翦軍以伐燕。十月而拔薊城")
add("Li_Xin", "Yan_Wang_Xi", "military_conflict", "negative", "S081",
    "秦將李信追撃燕王急")
add("Dai_Wang_Jia", "Yan_Wang_Xi", "diplomatic_attempt", "negative", "S081",
    "代王嘉乃遺燕王喜書曰：「秦所以尤追燕急者，以太子丹故也。")
add("Yan_Wang_Xi", "Yan_Dan", "sacrifice_resource", "negative", "S081",
    "燕王乃使使斬太子丹，欲獻之秦")
add("Qin", "Yan", "military_conflict", "negative", "S081",
    "後五年，秦卒滅燕，虜燕王喜")
add("Qin_Shi_Huang", "Gao_Jianli", "diplomatic_attempt", "neutral", "S082",
    "秦皇帝惜其善撃筑，重赦之，乃矐其目")
add("Gao_Jianli", "Qin_Shi_Huang", "military_conflict", "negative", "S082",
    "髙漸離乃以鉛置筑中，復進得近，舉筑樸秦皇帝，不中")
add("Qin_Shi_Huang", "Gao_Jianli", "military_conflict", "negative", "S082",
    "於是遂誅髙漸離")
add("Lu_Goujian", "Jing_Ke", "allusion_reference", "neutral", "S083",
    "魯句踐已聞荊軻之刺秦王，私曰：「嗟乎，惜哉其不講於刺劍之術也！")

# ---------------------------------------------------------------------------
# Build & validate
# ---------------------------------------------------------------------------

def main():
    with SEG.open(encoding="utf-8", newline="") as fh:
        segs = {r["segment_id"]: r for r in csv.DictReader(fh)}
    with NODES.open(encoding="utf-8", newline="") as fh:
        node_ids = {r["node_id"] for r in csv.DictReader(fh)}

    errors = []
    seen = set()
    rows_out = []
    for src, tgt, etype, val, sid, quote in E:
        # node ids valid
        if src not in node_ids:
            errors.append(f"{sid}: unknown source_node {src}")
            continue
        if tgt not in node_ids:
            errors.append(f"{sid}: unknown target_node {tgt}")
            continue
        # segment exists
        if sid not in segs:
            errors.append(f"{sid}: segment_id not found")
            continue
        seg = segs[sid]
        # quote must be verbatim substring of THIS segment
        if quote not in seg["text"]:
            errors.append(f"{sid}: quote not verbatim in segment: {quote[:40]}…")
            continue
        # no duplicate (src,tgt,etype,sid)
        key = (src, tgt, etype, sid)
        if key in seen:
            errors.append(f"{sid}: duplicate edge {key}")
            continue
        seen.add(key)
        rows_out.append({
            "source_node": src, "target_node": tgt, "edge_type": etype,
            "valence": val, "phase": seg["phase"],
            "text_source": seg["source"], "segment_id": sid,
            "evidence_quote": quote,
        })

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print("  ", e)
        sys.exit(1)

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "source_node", "target_node", "edge_type", "valence",
            "phase", "text_source", "segment_id", "evidence_quote"],
            quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writeheader()
        w.writerows(rows_out)

    # summary
    from collections import Counter
    print(f"WROTE {OUT}  edges={len(rows_out)}")
    print("edge_type:", dict(Counter(r["edge_type"] for r in rows_out)))
    print("valence  :", dict(Counter(r["valence"] for r in rows_out)))
    print("phase    :", dict(Counter(r["phase"] for r in rows_out)))
    print("source   :", dict(Counter(r["text_source"] for r in rows_out)))


if __name__ == "__main__":
    main()
