"""Summarize operator review agreement across one or more shadow-run reports."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _is_borderline(row: dict[str, Any], window: float = 0.35) -> bool:
    score = row.get("decision", {}).get("score")
    threshold = row.get("decision", {}).get("threshold")
    if score is None or threshold is None:
        return False
    try:
        return abs(float(score) - float(threshold)) <= window
    except (TypeError, ValueError):
        return False


def summarize(path: Path) -> dict[str, Any]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    total = len(rows)
    reviewed = 0
    matches = 0
    disagreements = 0
    by_reason = Counter()
    by_eligibility = Counter()
    by_case = Counter()
    borderline_disagreements = []

    for row in rows:
        reviewer = row.get("reviewer", {}) or {}
        matches_value = reviewer.get("matches_system_decision")
        if matches_value is None:
            continue
        reviewed += 1
        reason = row.get("decision", {}).get("reason") or "unknown"
        eligibility = row.get("eligibility", {}).get("status") or "unknown"
        if matches_value:
            matches += 1
        else:
            disagreements += 1
            by_reason[reason] += 1
            by_eligibility[eligibility] += 1
            by_case[row.get("case") or "unknown"] += 1
            if _is_borderline(row):
                borderline_disagreements.append(
                    {
                        "case": row.get("case"),
                        "reason": reason,
                        "summary": row.get("decision", {}).get("summary"),
                        "reviewer_disposition": reviewer.get("disposition"),
                        "reviewer_reason": reviewer.get("judgment_reason"),
                    }
                )

    return {
        "file": str(path),
        "total_rows": total,
        "reviewed_rows": reviewed,
        "match_rate": (matches / reviewed) if reviewed else 0.0,
        "disagreement_rate": (disagreements / reviewed) if reviewed else 0.0,
        "disagreements_by_reason": dict(by_reason),
        "disagreements_by_eligibility": dict(by_eligibility),
        "disagreements_by_case": dict(by_case),
        "borderline_disagreements": borderline_disagreements,
    }


def summarize_many(paths: list[Path]) -> dict[str, Any]:
    per_file = [summarize(path) for path in paths]
    aggregate = defaultdict(float)
    by_reason = Counter()
    by_eligibility = Counter()
    by_case = Counter()
    borderline_disagreements = []
    reviewed_total = 0
    matches_total = 0.0
    disagreements_total = 0.0

    for item in per_file:
        reviewed_total += int(item["reviewed_rows"])
        if item["reviewed_rows"]:
            matches_total += item["match_rate"] * item["reviewed_rows"]
            disagreements_total += item["disagreement_rate"] * item["reviewed_rows"]
        by_reason.update(item["disagreements_by_reason"])
        by_eligibility.update(item["disagreements_by_eligibility"])
        by_case.update(item["disagreements_by_case"])
        borderline_disagreements.extend(item["borderline_disagreements"])

    return {
        "reports": per_file,
        "aggregate": {
            "reviewed_rows": reviewed_total,
            "match_rate": (matches_total / reviewed_total) if reviewed_total else 0.0,
            "disagreement_rate": (disagreements_total / reviewed_total) if reviewed_total else 0.0,
            "disagreements_by_reason": dict(by_reason),
            "disagreements_by_eligibility": dict(by_eligibility),
            "disagreements_by_case": dict(by_case),
            "borderline_disagreements": borderline_disagreements,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python3 scripts/summarize_workflow_memory_reviews.py <review-report.json> [more.json ...]")
        return 1
    paths = [Path(arg).resolve() for arg in argv[1:]]
    summary = summarize_many(paths)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
