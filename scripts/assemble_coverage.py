"""Combine retained candidates and explicit reviews; never infer a support verdict from a score."""

import argparse
from pathlib import Path

from ask_phil.coverage import CoverageEvidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--reference-reviews", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    CoverageEvidence(args.snapshot, args.plan, args.captures).assemble(
        args.decisions,
        args.output,
        reference_reviews_path=args.reference_reviews,
    )


if __name__ == "__main__":
    main()
