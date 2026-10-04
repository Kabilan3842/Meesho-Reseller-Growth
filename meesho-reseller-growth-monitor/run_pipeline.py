import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in (BASE_DIR, os.path.join(BASE_DIR, "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent.mock_runner import run_pipeline  # noqa: E402
from generate_dataset import generate_data  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the full Meesho reseller monitoring pipeline."
    )
    parser.add_argument("--skip-generate", action="store_true",
                        help="reuse the existing dataset in data/")
    parser.add_argument("--quiet", action="store_true",
                        help="print only errors")
    args = parser.parse_args(argv)

    verbose = not args.quiet

    if not args.skip_generate:
        if verbose:
            print("Generating dataset (seed 42)...")
        generate_data(verbose=False)

    report = run_pipeline(verbose=verbose)

    if verbose:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
        print("Please review the report above before sharing it.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
