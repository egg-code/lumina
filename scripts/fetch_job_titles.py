#!/usr/bin/env python3
"""Download the FULL gpriday/job-titles corpus from Hugging Face.

This is the production counterpart to data/job_titles_sample.json, which
is a ~1,000-title sample gathered the same way for use without network
access. Run this script from an environment with normal internet access
(it is NOT runnable in this build's sandbox — see action_steps.md #7) to
pull all ~65,248 rows and overwrite the bundled sample with the real
thing:

    python scripts/fetch_job_titles.py
    python scripts/fetch_job_titles.py --output data/job_titles_full.json

Deliberately stdlib-only (urllib, json, argparse — no `requests`, no
`huggingface_hub`, no `datasets`) so it has zero new dependencies to
install and can't silently rot if this project's Python version changes.

Data source: https://huggingface.co/datasets/gpriday/job-titles
(CC-BY-4.0). Per the privacy discussion in action_steps.md #7, this is a
PUBLIC TAXONOMY of generic occupational titles (derived from ESCO,
O*NET, and OSCA) — not scraped data about any identifiable person. This
script never touches a job board, social profile, or any other source of
real career-seeker data.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://datasets-server.huggingface.co/rows"
DATASET = "gpriday/job-titles"
CONFIG = "default"
SPLIT = "train"
PAGE_SIZE = 100

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "job_titles_full.json"


def fetch_page(offset: int, length: int = PAGE_SIZE, *, max_retries: int = 5) -> dict:
    """Fetch one page of rows, retrying with exponential backoff on transient errors."""
    url = (
        f"{API_BASE}?dataset={DATASET}&config={CONFIG}&split={SPLIT}"
        f"&offset={offset}&length={length}"
    )
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            wait = 2**attempt
            print(f"  fetch failed at offset={offset} ({exc}); retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    assert last_error is not None
    raise last_error


def fetch_all_titles(*, page_size: int = PAGE_SIZE, delay: float = 0.2) -> list[str]:
    """Page through the entire dataset, returning a deduplicated, sorted title list."""
    titles: set[str] = set()

    first_page = fetch_page(0, page_size)
    total = first_page["num_rows_total"]
    print(f"Dataset reports {total} total rows.", file=sys.stderr)

    for row in first_page["rows"]:
        titles.add(row["row"]["job_title"])

    offset = page_size
    while offset < total:
        page = fetch_page(offset, page_size)
        for row in page["rows"]:
            titles.add(row["row"]["job_title"])
        print(f"  fetched {min(offset + page_size, total)}/{total}", file=sys.stderr)
        offset += page_size
        time.sleep(delay)  # be polite to the public API

    return sorted(titles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the full title list (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Seconds to sleep between page requests (default: 0.2)",
    )
    args = parser.parse_args()

    titles = fetch_all_titles(delay=args.delay)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(titles, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(titles)} unique job titles to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
