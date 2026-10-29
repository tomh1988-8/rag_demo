"""Inspect measured extraction and admitted capabilities beside unassessed profile history."""

import argparse
import json
from pathlib import Path

from ask_phil.coverage import CoverageEvidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = CoverageEvidence(args.snapshot, args.plan, args.captures).report(args.graph)
    with args.output.open("x") as destination:
        destination.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"profiles": len(result["profiles"])}))


if __name__ == "__main__":
    main()
