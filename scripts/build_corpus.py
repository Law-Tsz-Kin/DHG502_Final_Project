#!/usr/bin/env python3
"""Build ``data/corpus_segments.csv`` from the Classical Chinese sources in ``raw_texts/``.

Each non-empty line of every source file becomes one corpus segment, tagged with
a ``source`` (textual tradition / chapter) and a ``phase`` (project period tag).
The script only removes blank lines, surrounding whitespace, and numeric
footnote markers such as ``[1]``, ``〔12〕`` or ``【3〕``-style brackets that
contain digits only. Editorial brackets that contain Classical Chinese text
(e.g. ``〔冬，十月〕``) are left untouched, and no Chinese character or
punctuation mark is ever modified, simplified, or translated.

Usage (works from the project root or from inside ``scripts/``)::

    python3 scripts/build_corpus.py
    cd scripts && python3 build_corpus.py

Only the Python standard library is used (``csv``, ``pathlib``, ``re``).
"""

import csv
import re
from pathlib import Path

# --------------------------------------------------------------------------
# Paths (resolved relative to the project root: the parent of scripts/)
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_TEXTS_DIR = PROJECT_ROOT / "raw_texts"
OUTPUT_CSV = PROJECT_ROOT / "data" / "corpus_segments.csv"

# --------------------------------------------------------------------------
# Exact file-to-tag mapping (list order defines the segment ordering)
# --------------------------------------------------------------------------
FILE_TAGS = [
    # (filename, source, phase)
    ("燕王喜使栗腹以百金為趙孝成王壽_燕策三_戰國策.txt", "ZGC", "P1_pre227_diplomacy"),
    ("秦并趙北向迎燕_燕策三_戰國策.txt", "ZGC", "P1_pre227_diplomacy"),
    ("燕王喜元年至二十三年_燕召公世家_史記.txt", "Shiji_34", "P1_pre227_diplomacy"),
    ("趙孝成王十年至趙悼襄王卒_趙世家_史記.txt", "Shiji_43", "P1_pre227_diplomacy"),
    ("燕太子丹質於秦亡歸_燕策三_戰國策.txt", "ZGC", "P2_alliance_vs_plot"),
    ("荊軻_刺客列傳_史記.txt", "Shiji_86", "P2_alliance_vs_plot"),
    ("燕王喜二十五年至三十三年_燕召公世家_史記.txt", "Shiji_34", "P4_fall_of_yan_228_221"),
    ("秦始皇十八年至二十六年_秦始皇本紀_史記.txt", "Shiji_06", "P4_fall_of_yan_228_221"),
    ("王翦_白起王翦列傳_史記.txt", "Shiji_73", "P4_fall_of_yan_228_221"),
    ("秦始皇十九年至二十六年_卷六卷七_資治通鑑.txt", "ZZTJ", "P4_fall_of_yan_228_221"),
]

# Numeric footnote markers only: [1], 〔12〕, 【3】 (ASCII or full-width digits).
# Brackets holding Chinese text (e.g. 〔冬，十月〕 or 〔武〕) are NOT matched,
# so collation notes inside the source texts are preserved verbatim.
FOOTNOTE_RE = re.compile(r"\[\d+\]|〔\d+〕|【\d+】")

# Runs of ASCII spaces/tabs are collapsed to a single space when cleaning a
# line. This never touches Chinese characters, full-width punctuation, or the
# full-width space (U+3000) used inside the source texts.
ASCII_WS_RE = re.compile(r"[ \t]+")


def read_text(path: Path) -> str:
    """Read *path* as UTF-8, falling back to UTF-8 with BOM handling."""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8-sig")
    # A leading BOM decodes fine under plain utf-8 (as U+FEFF); drop it.
    return text.lstrip("\ufeff")


def clean_line(line: str) -> str:
    """Strip footnote markers and stray whitespace from one line of text."""
    line = FOOTNOTE_RE.sub("", line)
    line = ASCII_WS_RE.sub(" ", line)
    return line.strip()


def extract_segments(path: Path) -> list[str]:
    """Return the cleaned, non-empty lines of *path* as corpus segments."""
    segments = []
    for line in read_text(path).splitlines():
        cleaned = clean_line(line)
        if cleaned:
            segments.append(cleaned)
    return segments


def main() -> None:
    records: list[tuple[str, str, str]] = []  # (source, phase, text)
    missing: list[str] = []

    for filename, source, phase in FILE_TAGS:
        path = RAW_TEXTS_DIR / filename
        if not path.is_file():
            missing.append(filename)
            continue
        for text in extract_segments(path):
            records.append((source, phase, text))

    # Zero-pad segment IDs to at least 2 digits, widening to 3+ digits
    # automatically if the corpus grows past 99 segments.
    total = len(records)
    id_width = max(2, len(str(total)))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["segment_id", "source", "phase", "text"])
        for index, (source, phase, text) in enumerate(records, start=1):
            writer.writerow([f"S{index:0{id_width}d}", source, phase, text])

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    source_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    for source, phase, _ in records:
        source_counts[source] = source_counts.get(source, 0) + 1
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

    print("=" * 60)
    print("Corpus build summary")
    print("=" * 60)
    print(f"Output file     : {OUTPUT_CSV}")
    print(f"Total segments  : {total}")
    print("-" * 60)
    print("Segments per source:")
    for _, source, _ in FILE_TAGS:
        if source not in source_counts:
            continue
        print(f"  {source:<10} {source_counts[source]}")
        del source_counts[source]
    print("-" * 60)
    print("Segments per phase:")
    for _, _, phase in FILE_TAGS:
        if phase not in phase_counts:
            continue
        print(f"  {phase:<24} {phase_counts[phase]}")
        del phase_counts[phase]
    print("=" * 60)

    if missing:
        print("WARNING: the following expected input files are missing:")
        for filename in missing:
            print(f"  - {RAW_TEXTS_DIR / filename}")
        print(f"({len(missing)} of {len(FILE_TAGS)} expected files missing; "
              "the CSV was written without them.)")
    elif total == 0:
        print("WARNING: no segments were extracted; the CSV contains only the header.")


if __name__ == "__main__":
    main()
