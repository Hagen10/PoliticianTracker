#!/usr/bin/env python3
"""
Measures time spent expressing gratitude/thanks in Danish parliament speech segments.

For every <TaleSegment> in _data/<year>/*.xml, this looks at the segment's OPENING
sentence only (a "tak"/"takke" mention mid- or end-of-speech is usually the speaker
talking about someone else's thanks, not thanking for the floor themselves) and finds
Danish "thank you" phrases there (e.g. "Tak til ordføreren.", "Tak for svaret.",
"Mange tak, formand.") via regex. It computes, assuming constant talking speed within
a segment:
  - TalkingTimeSeconds: wall-clock duration of the segment (EndDateTime - StartDateTime)
  - GratitudeProportion: gratitude word count / total word count in the segment
  - GratitudeTimeSeconds: TalkingTimeSeconds * GratitudeProportion

Results are written to new XML files under _gen_data/<year>/, mirroring _data/, with the
three fields above appended to each TaleSegment's <MetaSpeechSegment>. Files under _data/
are never modified.

Every segment with a match is also recorded in _gen_data/gratitude_matches.csv (one row
per segment) so the matches can be spot-checked manually, and split per politician under
_politicians/<Name>/gratitude_matches.csv.

Usage:
  python3 scripts/gratitude_time.py                       # process everything
  python3 scripts/gratitude_time.py --years 20091 20101   # only specific sessions
  python3 scripts/gratitude_time.py --limit 5              # quick smoke test
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "_data"
OUTPUT_DIR = REPO_ROOT / "_gen_data"
POLITICIANS_DIR = REPO_ROOT / "_politicians"
MATCHES_CSV = OUTPUT_DIR / "gratitude_matches.csv"
SUMMARY_OVERALL_CSV = OUTPUT_DIR / "gratitude_summary_overall.csv"
SUMMARY_BY_POLITICIAN_CSV = OUTPUT_DIR / "gratitude_summary_by_politician.csv"
SUMMARY_BY_PARTY_CSV = OUTPUT_DIR / "gratitude_summary_by_party.csv"
SUMMARY_BY_MONTH_CSV = OUTPUT_DIR / "gratitude_summary_by_month.csv"
SUMMARY_BY_POLITICIAN_MONTH_CSV = OUTPUT_DIR / "gratitude_summary_by_politician_month.csv"
SUMMARY_BY_PARTY_MONTH_CSV = OUTPUT_DIR / "gratitude_summary_by_party_month.csv"

WORD_RE = re.compile(r"\w+", re.UNICODE)
FILENAME_RE = re.compile(r"(\d+)_M(\d+)_helemoedet")

# Splits on sentence-ending punctuation; used to isolate a segment's opening sentence.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Danish gratitude phrases. Matches only the thanking clause itself (stopping at
# punctuation or after a bounded number of object words) so that substantive content
# following a "Tak, men ..." style sentence isn't miscounted as gratitude. "tak"/
# "mange tak"/etc. is a noun and takes "til/for X" (e.g. "tak til ordføreren"), while
# "takke"/"takker" is a verb that can also take a direct object with no preposition
# (e.g. "takke ministeren").
GRATITUDE_RE = re.compile(
    r"""
    \btak\s+skal\s+du\s+have\b                                   # "tak skal du have"
    |
    \b(?:(?:mange|tusind|stor|hjertelig)\s+)?tak\b                # tak (noun)
    (?:\s+(?:til|for)\s+\w+(?:\s+\w+){0,3})?                      # optional "til/for X Y Z"
    (?:\s*,\s*(?:kære\s+)?(?:fru\s+|hr\.\s+)?formand\b)?          # optional ", formand"
    |
    \btak(?:ke|ker)\b                                             # takke / takker (verb)
    (?:
        \s+(?:til|for)\s+\w+(?:\s+\w+){0,3}                       # "takke for X" / "takker til X"
      | \s+\w+(?:\s+\w+){0,3}                                      # direct object "takke ministeren"
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def count_words(text):
    return len(WORD_RE.findall(text))


def count_chars(text):
    return len(re.sub(r"\s+", "", text))


def extract_segment_text(segment):
    """Concatenate all spoken text (TekstGruppe/.../Char) of a TaleSegment."""
    parts = []
    for group in segment.findall("TekstGruppe"):
        for text in group.itertext():
            stripped = text.strip()
            if stripped:
                parts.append(stripped)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def opening_sentence(text):
    """The first sentence of a segment, i.e. what a new speaker says before anything else."""
    sentences = SENTENCE_SPLIT_RE.split(text, maxsplit=1)
    return sentences[0] if sentences else ""


def find_gratitude(text):
    """Gratitude matches restricted to the segment's opening sentence only.

    A "tak"/"takke" mention later in a segment is usually the speaker describing
    someone else's thanks (or a hidden intent), not thanking for the floor themselves.
    """
    return list(GRATITUDE_RE.finditer(opening_sentence(text)))


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


CSV_FIELDS = [
    "year",
    "meeting",
    "file",
    "speaker_first",
    "speaker_last",
    "party",
    "role",
    "start_datetime",
    "end_datetime",
    "talking_time_seconds",
    "opening_sentence",
    "matched_phrases",
    "gratitude_word_count",
    "total_word_count",
    "gratitude_proportion_words",
    "gratitude_char_count",
    "total_char_count",
    "gratitude_proportion_chars",
    "gratitude_time_seconds",
]


def speaker_info(tale):
    speaker = tale.find("Taler/MetaSpeakerMP")
    if speaker is None:
        return {"first": "", "last": "", "party": "", "role": ""}
    return {
        "first": speaker.findtext("OratorFirstName") or "",
        "last": speaker.findtext("OratorLastName") or "",
        "party": speaker.findtext("GroupNameShort") or "",
        "role": speaker.findtext("OratorRole") or "",
    }


def is_placeholder_speaker(speaker):
    """Detects non-speaker meeting markers (e.g. "Pause", "MødeSlut") rather than an MP:
    their first/last name, party and role are all the same placeholder word."""
    return bool(speaker["first"]) and speaker["first"] == speaker["last"] == speaker["party"] == speaker["role"]


def effective_party(speaker):
    """Ministers often have no GroupNameShort in the source data; fall back to their
    role (e.g. "minister") so summary tables don't show a blank/unlabeled party."""
    return speaker["party"] or speaker["role"] or "Ukendt"


def summarize_entry(entry):
    talking_time = entry["talking_time"]
    gratitude_time = entry["gratitude_time"]
    return {
        "segments": entry["segments"],
        "talking_time_seconds": f"{talking_time:.2f}",
        "talking_time_hours": f"{talking_time / 3600:.4f}",
        "gratitude_time_seconds": f"{gratitude_time:.2f}",
        "gratitude_time_hours": f"{gratitude_time / 3600:.4f}",
        "gratitude_proportion": f"{(gratitude_time / talking_time) if talking_time else 0.0:.4%}",
    }


def write_summary_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def politician_folder_name(first, last):
    """Filesystem-safe folder name for a politician, e.g. "Lars-Christian_Brask"."""
    name = f"{first}_{last}".strip("_")
    name = re.sub(r"\s+", "_", name)
    return re.sub(r"[^\w\-]", "-", name, flags=re.UNICODE)


def process_segment(segment, speaker, year, meeting, filename):
    meta = segment.find("MetaSpeechSegment")
    if meta is None:
        return None, None

    start = parse_datetime(meta.findtext("StartDateTime"))
    end = parse_datetime(meta.findtext("EndDateTime"))
    talking_time = (end - start).total_seconds() if start and end else 0.0
    talking_time = max(talking_time, 0.0)

    text = extract_segment_text(segment)
    opening = opening_sentence(text)
    matches = find_gratitude(text)

    total_words = count_words(text)
    gratitude_words = sum(count_words(m.group()) for m in matches)
    proportion_words = gratitude_words / total_words if total_words else 0.0

    total_chars = count_chars(text)
    gratitude_chars = sum(count_chars(m.group()) for m in matches)
    proportion_chars = gratitude_chars / total_chars if total_chars else 0.0

    gratitude_time = talking_time * proportion_words

    ET.SubElement(meta, "TalkingTimeSeconds").text = f"{talking_time:.2f}"
    ET.SubElement(meta, "GratitudeProportion").text = f"{proportion_words:.4f}"
    ET.SubElement(meta, "GratitudeTimeSeconds").text = f"{gratitude_time:.4f}"

    stat = {
        "talking_time": talking_time,
        "gratitude_time": gratitude_time,
        "speaker_first": speaker["first"],
        "speaker_last": speaker["last"],
        "party": effective_party(speaker),
        "month": start.strftime("%Y-%m") if start else "unknown",
    }

    row = None
    if matches:
        row = {
            "year": year,
            "meeting": meeting,
            "file": filename,
            "speaker_first": speaker["first"],
            "speaker_last": speaker["last"],
            "party": effective_party(speaker),
            "role": speaker["role"],
            "start_datetime": meta.findtext("StartDateTime") or "",
            "end_datetime": meta.findtext("EndDateTime") or "",
            "talking_time_seconds": f"{talking_time:.2f}",
            "opening_sentence": opening,
            "matched_phrases": "; ".join(m.group().strip() for m in matches),
            "gratitude_word_count": gratitude_words,
            "total_word_count": total_words,
            "gratitude_proportion_words": f"{proportion_words:.4f}",
            "gratitude_char_count": gratitude_chars,
            "total_char_count": total_chars,
            "gratitude_proportion_chars": f"{proportion_chars:.4f}",
            "gratitude_time_seconds": f"{gratitude_time:.4f}",
        }

    return stat, row


def process_file(src_path, dst_path):
    tree = ET.parse(src_path)
    root = tree.getroot()

    match = FILENAME_RE.search(src_path.stem)
    year, meeting = match.groups() if match else ("", "")

    stats = []
    rows = []
    for tale in root.iter("Tale"):
        speaker = speaker_info(tale)
        placeholder = is_placeholder_speaker(speaker)
        for segment in tale.findall("TaleSegment"):
            stat, row = process_segment(segment, speaker, year, meeting, src_path.name)
            # Meeting markers like "Pause"/"MødeSlut" aren't real MPs; still annotate their
            # XML timing fields above, but keep them out of the politician/party summaries.
            if placeholder:
                continue
            if stat is not None:
                stats.append(stat)
            if row is not None:
                rows.append(row)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dst_path, encoding="utf-8", xml_declaration=True)
    return stats, rows


def iter_source_files(years=None):
    if years:
        for year in years:
            yield from sorted((DATA_DIR / year).glob("*.xml"))
    else:
        yield from sorted(DATA_DIR.glob("*/*.xml"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="*", help="Only process these parliamentary session years (e.g. 20091 20101)")
    parser.add_argument("--limit", type=int, help="Only process the first N files (for quick testing)")
    args = parser.parse_args()

    files = list(iter_source_files(args.years))
    if args.limit:
        files = files[: args.limit]

    total_talking = 0.0
    total_gratitude = 0.0
    total_segments = 0
    skipped = []
    all_rows = []
    by_politician = defaultdict(lambda: {"talking_time": 0.0, "gratitude_time": 0.0, "segments": 0})
    by_party = defaultdict(lambda: {"talking_time": 0.0, "gratitude_time": 0.0, "segments": 0})
    by_month = defaultdict(lambda: {"talking_time": 0.0, "gratitude_time": 0.0, "segments": 0})
    by_politician_month = defaultdict(lambda: {"talking_time": 0.0, "gratitude_time": 0.0, "segments": 0})
    by_party_month = defaultdict(lambda: {"talking_time": 0.0, "gratitude_time": 0.0, "segments": 0})

    for src_path in files:
        rel = src_path.relative_to(DATA_DIR)
        dst_path = OUTPUT_DIR / rel
        try:
            stats, rows = process_file(src_path, dst_path)
        except ET.ParseError as exc:
            # A few source files contain malformed/concatenated XML; skip them rather
            # than aborting the whole run.
            print(f"{rel}: SKIPPED (malformed XML: {exc})", file=sys.stderr)
            skipped.append(rel)
            continue
        total_segments += len(stats)
        total_talking += sum(s["talking_time"] for s in stats)
        total_gratitude += sum(s["gratitude_time"] for s in stats)
        all_rows.extend(rows)
        for s in stats:
            key = (s["speaker_first"], s["speaker_last"], s["party"])
            entry = by_politician[key]
            entry["talking_time"] += s["talking_time"]
            entry["gratitude_time"] += s["gratitude_time"]
            entry["segments"] += 1

            party_entry = by_party[s["party"]]
            party_entry["talking_time"] += s["talking_time"]
            party_entry["gratitude_time"] += s["gratitude_time"]
            party_entry["segments"] += 1

            month_entry = by_month[s["month"]]
            month_entry["talking_time"] += s["talking_time"]
            month_entry["gratitude_time"] += s["gratitude_time"]
            month_entry["segments"] += 1

            politician_month_entry = by_politician_month[key + (s["month"],)]
            politician_month_entry["talking_time"] += s["talking_time"]
            politician_month_entry["gratitude_time"] += s["gratitude_time"]
            politician_month_entry["segments"] += 1

            party_month_entry = by_party_month[(s["party"], s["month"])]
            party_month_entry["talking_time"] += s["talking_time"]
            party_month_entry["gratitude_time"] += s["gratitude_time"]
            party_month_entry["segments"] += 1
        print(f"{rel}: {len(stats)} segments, {len(rows)} gratitude matches", file=sys.stderr)

    if skipped:
        print(f"\nSkipped {len(skipped)} malformed file(s): {', '.join(str(p) for p in skipped)}", file=sys.stderr)

    MATCHES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(MATCHES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    rows_by_politician = defaultdict(list)
    for row in all_rows:
        if row["speaker_first"] or row["speaker_last"]:
            rows_by_politician[(row["speaker_first"], row["speaker_last"])].append(row)
    for (first, last), rows in rows_by_politician.items():
        politician_dir = POLITICIANS_DIR / politician_folder_name(first, last)
        politician_dir.mkdir(parents=True, exist_ok=True)
        write_summary_csv(politician_dir / "gratitude_matches.csv", CSV_FIELDS, rows)

    overall_proportion = total_gratitude / total_talking if total_talking else 0.0
    with open(SUMMARY_OVERALL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "total_files",
                "total_segments",
                "total_talking_time_seconds",
                "total_talking_time_hours",
                "total_gratitude_time_seconds",
                "total_gratitude_time_hours",
                "gratitude_proportion",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "total_files": len(files) - len(skipped),
                "total_segments": total_segments,
                "total_talking_time_seconds": f"{total_talking:.2f}",
                "total_talking_time_hours": f"{total_talking / 3600:.4f}",
                "total_gratitude_time_seconds": f"{total_gratitude:.2f}",
                "total_gratitude_time_hours": f"{total_gratitude / 3600:.4f}",
                "gratitude_proportion": f"{overall_proportion:.4%}",
            }
        )

    # Sorted by talking time descending: most active speakers first.
    politician_rows = sorted(
        (
            {"speaker_first": first, "speaker_last": last, "party": party, **summarize_entry(entry)}
            for (first, last, party), entry in by_politician.items()
        ),
        key=lambda r: float(r["talking_time_seconds"]),
        reverse=True,
    )
    write_summary_csv(
        SUMMARY_BY_POLITICIAN_CSV,
        ["speaker_first", "speaker_last", "party", "segments", "talking_time_seconds", "talking_time_hours",
         "gratitude_time_seconds", "gratitude_time_hours", "gratitude_proportion"],
        politician_rows,
    )

    # Sorted by talking time descending: most active parties first.
    party_rows = sorted(
        ({"party": party, **summarize_entry(entry)} for party, entry in by_party.items()),
        key=lambda r: float(r["talking_time_seconds"]),
        reverse=True,
    )
    write_summary_csv(
        SUMMARY_BY_PARTY_CSV,
        ["party", "segments", "talking_time_seconds", "talking_time_hours",
         "gratitude_time_seconds", "gratitude_time_hours", "gratitude_proportion"],
        party_rows,
    )

    # Sorted by month ascending, then talking time descending within each month.
    month_rows = sorted(
        ({"month": month, **summarize_entry(entry)} for month, entry in by_month.items()),
        key=lambda r: (r["month"], -float(r["talking_time_seconds"])),
    )
    write_summary_csv(
        SUMMARY_BY_MONTH_CSV,
        ["month", "segments", "talking_time_seconds", "talking_time_hours",
         "gratitude_time_seconds", "gratitude_time_hours", "gratitude_proportion"],
        month_rows,
    )

    politician_month_rows = sorted(
        (
            {"month": month, "speaker_first": first, "speaker_last": last, "party": party, **summarize_entry(entry)}
            for (first, last, party, month), entry in by_politician_month.items()
        ),
        key=lambda r: (r["month"], -float(r["talking_time_seconds"])),
    )
    write_summary_csv(
        SUMMARY_BY_POLITICIAN_MONTH_CSV,
        ["month", "speaker_first", "speaker_last", "party", "segments", "talking_time_seconds", "talking_time_hours",
         "gratitude_time_seconds", "gratitude_time_hours", "gratitude_proportion"],
        politician_month_rows,
    )

    party_month_rows = sorted(
        (
            {"month": month, "party": party, **summarize_entry(entry)}
            for (party, month), entry in by_party_month.items()
        ),
        key=lambda r: (r["month"], -float(r["talking_time_seconds"])),
    )
    write_summary_csv(
        SUMMARY_BY_PARTY_MONTH_CSV,
        ["month", "party", "segments", "talking_time_seconds", "talking_time_hours",
         "gratitude_time_seconds", "gratitude_time_hours", "gratitude_proportion"],
        party_month_rows,
    )

    print(f"\nProcessed {len(files)} files, {total_segments} speech segments")
    print(f"Total talking time:    {total_talking / 3600:.2f} hours")
    print(f"Total gratitude time:  {total_gratitude / 3600:.2f} hours")
    if total_talking:
        print(f"Overall gratitude proportion: {overall_proportion:.4%}")
    print(f"Wrote {len(all_rows)} matched rows to {MATCHES_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote overall summary to {SUMMARY_OVERALL_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(politician_rows)} politician rows to {SUMMARY_BY_POLITICIAN_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(party_rows)} party rows to {SUMMARY_BY_PARTY_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(month_rows)} month rows to {SUMMARY_BY_MONTH_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(politician_month_rows)} politician-month rows to {SUMMARY_BY_POLITICIAN_MONTH_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(party_month_rows)} party-month rows to {SUMMARY_BY_PARTY_MONTH_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote per-politician match files for {len(rows_by_politician)} politicians to {POLITICIANS_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
