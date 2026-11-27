#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_segments_csv.py
=====================
Converts the Classical Chinese source files in raw_texts/ into a clean UTF-8 CSV
(segments.csv) with header: segment_id,source,phase,text

Cleaning rules applied (per project spec):
  * Segments = blank-line-separated blocks of each source file.
    Nothing is split, merged, reordered or invented beyond that.
  * Removed: blank lines; modern editorial footnote markers of the form [nn]
    (half-width brackets + digits; 13 occurrences, all in the 資治通鑑 file);
    the ZZTJ year headings (始皇帝十九年（癸酉，西元前二二八年）, 8 occurrences);
    the ZZTJ item numbers at line start (1　, 2　…, 22 occurrences).
  * Kept verbatim: all Classical Chinese characters, original punctuation and
    editorial collation brackets (e.g. 〔冬，十月〕, （西）, ［樂乘］).
  * Lines inside a block are concatenated (Classical Chinese needs no separator);
    leading/trailing whitespace of each line is stripped.

Phase assignment criterion (documented for the audit):
  P1_pre_diplomacy      – before the plot: Yan–Zhao wars, Qin's rise, hostage
                          background, Jing Ke's early life, Qin destroying Han/Zhao.
  P2_alliance_vs_plot   – plot formation & alliance diplomacy: 鞠武's alliance plan,
                          田光/荊軻 recruitment, mission preparation, farewell at 易水;
                          also the ZGC envoy episode where Yan diplomatically aligns
                          with Qin (秦并趙，北向迎燕).
  P3_assassination      – the embassy in Qin and the assassination attempt itself.
  P4_fall_of_yan        – Qin's retaliation and conquest of Yan, death of 太子丹,
                          fall of Yan/Dai/Qi, unification and aftermath.
  Segments whose content substantially straddles two or more phases were
  originally marked [VERIFY_PHASE]; the user has since resolved them manually
  (S001 → P2, S014 → P3, S058 → P3), and the PHASES table below reflects those
  decisions so re-running the script reproduces the committed CSV exactly.

Renumbering (v3):
  The user manually split the two straddling blocks into two segments each at
  the sentence boundary below, then renumbered all rows sequentially. The
  SPLITS table reproduces those splits so the script output matches the
  committed CSV (92 rows, S001–S092).
"""

import csv
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_texts"
OUT = ROOT / "data" / "segments.csv"

# File order = workspace listing order; segment_ids run sequentially across files.
FILES = [
    "燕太子丹質於秦亡歸_燕策三_戰國策.txt",
    "燕王喜二十五年至三十三年_燕召公世家_史記.txt",
    "燕王喜使栗腹以百金為趙孝成王壽_燕策三_戰國策.txt",
    "燕王喜元年至二十三年_燕召公世家_史記.txt",
    "王翦_白起王翦列傳_史記.txt",
    "秦始皇十九年至二十六年_卷六卷七_資治通鑑.txt",
    "秦始皇十八年至二十六年_秦始皇本紀_史記.txt",
    "秦并趙北向迎燕_燕策三_戰國策.txt",
    "荊軻_刺客列傳_史記.txt",
    "趙孝成王十年至趙悼襄王卒_趙世家_史記.txt",
]

P1 = "P1_pre_diplomacy"
P2 = "P2_alliance_vs_plot"
P3 = "P3_assassination"
P4 = "P4_fall_of_yan"
VERIFY = "[VERIFY_PHASE]"

# One phase per blank-line-delimited block, in file order.
PHASES = {
    # 燕太子丹質於秦亡歸 (ZGC 燕策三): 12 blocks
    # [0] 丹歸國、患秦、問鞫武（尚未有謀）→ P2（人工修訂：歸國即謀劃背景，歸入 P2）
    # [1]-[8] 樊於期奔燕、合縱之議、田光薦軻、荊軻許諾、備行、易水送別 → P2
    # [9]-[10] 使秦、圖窮匕見 → P3   [11] 秦伐燕、滅燕 → P4
    "燕太子丹質於秦亡歸_燕策三_戰國策.txt":
        [P2] + [P2] * 8 + [P3] * 2 + [P4],

    # 燕召公世家 25-33年 (Shiji): 3 blocks
    # [0] 秦滅韓、滅趙，代王嘉自立（威脅背景）→ P1
    # [1] 同段橫跨養士謀刺／刺秦王／拔薊遼東斬丹 → P3（人工修訂：以刺秦王為主軸）
    # [2] 三十三年秦拔遼東虜燕王喜，卒滅燕 → P4
    "燕王喜二十五年至三十三年_燕召公世家_史記.txt":
        [P1, P3, P4],

    # 燕王喜使栗腹… (ZGC 燕策三): 4 blocks — 燕趙戰後交涉與謝罪書，皆在謀劃之前 → P1
    "燕王喜使栗腹以百金為趙孝成王壽_燕策三_戰國策.txt":
        [P1] * 4,

    # 燕召公世家 1-23年 (Shiji): 2 blocks — 栗腹伐趵至太子丹歸國前 → P1
    "燕王喜元年至二十三年_燕召公世家_史記.txt":
        [P1] * 2,

    # 王翦列傳 (Shiji): 5 blocks — 王翦滅趙、定燕薊及滅楚、并天下 → P4
    # （[0] 僅以一句提及荊軻為賊，主體為滅趙定燕之軍事過程）
    "王翦_白起王翦列傳_史記.txt":
        [P4] * 5,

    # 資治通鑑 卷六卷七: 30 blocks
    # [0]-[4] 始皇帝十九年：克邯鄲、王翦屯中山臨燕、楚魏國喪 → P1
    # [5]-[6] 丹怨王、鞠武合縱之議、樊於期奔燕、荊軻受命備行 → P2
    # [7]     始皇帝二十年：荊軻刺秦王（主體）→ P3
    # [8]-[29] 拔薊、遼東、斬丹以後至并天下、稱皇帝 → P4
    "秦始皇十九年至二十六年_卷六卷七_資治通鑑.txt":
        [P1] * 5 + [P2] * 2 + [P3] + [P4] * 22,

    # 秦始皇本紀 (Shiji): 6 blocks
    # [0] 十八、十九年攻趙、屯中山欲攻燕 → P1
    # [1] 同段橫跨使荊軻刺秦王（P3）與破燕取薊、得太子丹首（P4）→ P3（人工修訂：以刺秦王為主軸）
    # [2]-[5] 滅魏、擊荊、虜燕王喜、得齊王建 → P4
    "秦始皇十八年至二十六年_秦始皇本紀_史記.txt":
        [P1, P3] + [P4] * 4,

    # 秦并趙，北向迎燕 (ZGC 燕策三): 2 blocks — 燕使賀秦王、說秦救燕之外交 → P2
    "秦并趙北向迎燕_燕策三_戰國策.txt":
        [P2] * 2,

    # 刺客列傳 (Shiji): 17 blocks
    # [0]-[4] 荊軻早年、游燕、交田光 → P1
    # [5]-[12] 太子丹歸國謀劃、田光自刎、荊軻許諾、備行、易水送別 → P2
    # [13]  使秦、咸陽宮行刺 → P3
    # [14]-[16] 秦伐燕滅燕、高漸離、魯句踐 → P4
    "荊軻_刺客列傳_史記.txt":
        [P1] * 5 + [P2] * 8 + [P3] + [P4] * 3,

    # 趙世家 (Shiji) 孝成王十年—悼襄王卒: 9 blocks — 燕趙相攻、趙國內政 → P1
    "趙孝成王十年至趙悼襄王卒_趙世家_史記.txt":
        [P1] * 9,
}

# Manual splits (user decision): straddling blocks are cut at the sentence
# boundary below into two segments, each with its own phase. The split point
# is the start of the given sentence; text before it keeps the first phase,
# text from it onward takes the second phase. No characters are added or lost.
SPLITS = {
    # 燕召公世家 25-33年 block[1]: split before 「二十九年」
    #   part 1 (P3): 燕見秦且滅六國 … 使將軍王翦撃燕。
    #   part 2 (P4): 二十九年，秦攻拔我薊 … 三十年，秦滅魏。
    "燕王喜二十五年至三十三年_燕召公世家_史記.txt": [
        (1, "二十九年，秦攻拔我薊", P3, P4),
    ],
    # 秦始皇本紀 block[1]: split before 「二十一年」
    #   part 1 (P3): 二十年，燕太子丹患秦兵至國 … 秦軍破燕易水之西。
    #   part 2 (P4): 二十一年，王賁攻（薊）［荊］ … 大雨雪，深二尺五寸。
    "秦始皇十八年至二十六年_秦始皇本紀_史記.txt": [
        (1, "二十一年，王賁攻", P3, P4),
    ],
}


def source_of(name: str) -> str:
    if "戰國策" in name:
        return "ZGC"
    if "資治通鑑" in name:
        return "ZZTJ"
    if "史記" in name:
        return "Shiji"
    raise ValueError(f"Unknown source for file: {name}")


FOOTNOTE = re.compile(r"\[\d+\]")  # modern editorial footnote markers, e.g. [31]
# ZZTJ year headings, e.g. 始皇帝十九年（癸酉，西元前二二八年）
YEAR_HEADING = re.compile(
    r"^始皇帝[一二三四五六七八九十]+年（[癸甲乙丙丁戊己庚辛壬][子丑寅卯辰巳午未申酉戌亥]，西元前[一二三四五六七八九十百]+年）"
)
# ZZTJ item numbers at line start, e.g. "1　" (full-width space after the digit)
ITEM_NUM = re.compile(r"^\d{1,2}　")


def blocks_of(text: str):
    """Split file content into blocks on blank lines (blank = whitespace-only line)."""
    blocks, cur = [], []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    return blocks


def clean_block(lines) -> str:
    """Join lines, drop footnote markers, ZZTJ year headings and item numbers,
    strip outer whitespace. Nothing else is touched."""
    joined = "".join(ln.strip() for ln in lines)
    joined = FOOTNOTE.sub("", joined)
    joined = YEAR_HEADING.sub("", joined)
    joined = ITEM_NUM.sub("", joined)
    return joined.strip()


def apply_splits(fname: str, blocks, phases):
    """Apply the user's manual splits: a block listed in SPLITS is cut at the
    given sentence boundary into (text_before, phase_before) and
    (text_from_boundary, phase_after)."""
    rules = SPLITS.get(fname, [])
    for block_idx, marker, phase_a, phase_b in rules:
        text = clean_block(blocks[block_idx])
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit(f"{fname}: split marker not found in block {block_idx}: {marker}")
        blocks = (
            blocks[:block_idx]
            + [text[:pos], text[pos:]]
            + blocks[block_idx + 1:]
        )
        phases = phases[:block_idx] + [phase_a, phase_b] + phases[block_idx + 1:]
    return blocks, phases


def main() -> None:
    rows = []
    footnotes_removed = 0
    headings_removed = 0
    itemnums_removed = 0
    for fname in FILES:
        text = (RAW / fname).read_text(encoding="utf-8")
        blocks = blocks_of(text)
        phases = PHASES[fname]
        if len(blocks) != len(phases):
            raise SystemExit(
                f"{fname}: {len(blocks)} blocks but {len(phases)} phase tags — aborting."
            )
        src = source_of(fname)
        blocks, phases = apply_splits(fname, blocks, phases)
        for block, phase in zip(blocks, phases):
            # after apply_splits, split entries are pre-cleaned strings
            text = clean_block(block) if isinstance(block, list) else block
            footnotes_removed += len(FOOTNOTE.findall(text))
            headings_removed += len(YEAR_HEADING.findall(text))
            itemnums_removed += len(ITEM_NUM.findall(text))
            rows.append((fname, src, phase, text))

    # sequential unique ids
    rows_out = []
    for i, (fname, src, phase, text) in enumerate(rows, start=1):
        rows_out.append((f"S{i:03d}", src, phase, text, fname))

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["segment_id", "source", "phase", "text"])
        for sid, src, phase, text, _ in rows_out:
            w.writerow([sid, src, phase, text])

    # ---- validation pass: re-read and check ----
    with OUT.open(encoding="utf-8", newline="") as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        data = list(rdr)
    n_expected = len(rows_out)
    assert header == ["segment_id", "source", "phase", "text"], header
    assert len(data) == n_expected, (len(data), n_expected)
    ids = [r[0] for r in data]
    assert ids == [f"S{i:03d}" for i in range(1, n_expected + 1)], "ids not sequential/unique"
    assert len(set(ids)) == len(ids), "duplicate ids"
    allowed_src = {"ZGC", "Shiji", "ZZTJ"}
    allowed_phase = {P1, P2, P3, P4, VERIFY}
    assert all(r[1] in allowed_src for r in data)
    assert all(r[2] in allowed_phase for r in data)
    assert all(r[3].strip() != "" for r in data)
    # verbatim check: every text must equal its cleaned source block
    # (blocks that were split are checked as the concatenation of their parts)
    idx = 0
    for f in FILES:
        blocks, phases = apply_splits(f, blocks_of((RAW / f).read_text(encoding="utf-8")), PHASES[f])
        for b in blocks:
            expected = clean_block(b) if isinstance(b, list) else b
            assert data[idx][3] == expected, f"verbatim mismatch at {data[idx][0]}"
            idx += 1
    assert idx == n_expected

    # ---- audit summary ----
    from collections import Counter
    src_counts = Counter(r[1] for r in data)
    ph_counts = Counter(r[2] for r in data)
    print(
        f"WROTE {OUT}  rows={len(data)}  footnotes_removed={footnotes_removed}  "
        f"year_headings_removed={headings_removed}  item_numbers_removed={itemnums_removed}"
    )
    print("source counts:", dict(src_counts))
    print("phase counts :", dict(ph_counts))
    print("flagged      :", [r[0] for r in data if r[2] == VERIFY])


if __name__ == "__main__":
    main()
