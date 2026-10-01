"""
run_all.py
----------
Runs the complete Objective 3 evaluation.

Usage:
    python run_all.py
    python run_all.py --quick
"""

import argparse
from pathlib import Path

import bench_performance
import bench_security
import make_report


def main():
    parser = argparse.ArgumentParser(
        description="Run Objective 3 adaptive authentication evaluation"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a smaller/faster evaluation"
    )

    args = parser.parse_args()

    # Create results directory
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" ADAPTIVE AUTHENTICATION - OBJECTIVE 3 EVALUATION")
    print("=" * 60)

    if args.quick:
        print("\nRunning QUICK evaluation...")
    else:
        print("\nRunning FULL evaluation...")

    # ---------------------------------------------------------
    # STEP 1: Performance benchmark
    # ---------------------------------------------------------
    print("\n[1/3] Running performance benchmark...")

    performance_results = bench_performance.run_performance(
        quick=args.quick
    )

    print("Performance benchmark completed.")

    # ---------------------------------------------------------
    # STEP 2: Security benchmark
    # ---------------------------------------------------------
    print("\n[2/3] Running security benchmark...")

    security_results = bench_security.run_security(
        quick=args.quick
    )

    print("Security benchmark completed.")

    # ---------------------------------------------------------
    # STEP 3: Generate report and graphs
    # ---------------------------------------------------------
    print("\n[3/3] Generating results and graphs...")

    make_report.main(
        performance_results=performance_results,
        security_results=security_results
    )

    print("\n" + "=" * 60)
    print(" EVALUATION COMPLETED")
    print("=" * 60)

    print(f"\nResults saved in:")
    print(results_dir)

    print("\nGenerated files include:")
    print("  - PNG graphs")
    print("  - CSV measurements")
    print("  - assumptions.json")
    print("  - run_metadata.json")
    print("  - results_summary.md")


if __name__ == "__main__":
    main()