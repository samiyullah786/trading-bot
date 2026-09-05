from __future__ import annotations

import argparse
import json

from .persistence import load
from .kernel import OutcomeKernel

def main() -> None:
    parser = argparse.ArgumentParser(description="AUREON mission kernel")
    parser.add_argument("mission", help="path to a mission JSON file")
    args = parser.parse_args()

    mission = load(args.mission)
    kernel = OutcomeKernel(mission)
    print(json.dumps(kernel.report(), indent=2))

if __name__ == "__main__":
    main()
